from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime
import logging

from payment.models import Invoice, InvoiceStatus
from payment.serializers import (
    InvoiceSerializer, 
    CreatePaymentSerializer, 
    PaymentCallbackSerializer,
    MarkInvoicesAsPaidSerializer,
)
from payment.multicard_service import multicard_service
from user.models import Student
from rest_framework.permissions import IsAuthenticated
from education.api.permissions import CanViewGroups

logger = logging.getLogger(__name__)


class InvoiceListView(generics.ListAPIView):
    """
    List all invoices.
    Students can see only their own invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.select_related('student', 'group').all()  # type: ignore

        # If user is a student, filter by their invoices
        if hasattr(user, 'student'):
            queryset = queryset.filter(student=user.student)
        # If user is staff/admin, show all invoices

        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        operation_description="List all invoices. Students see only their own invoices.",
        operation_summary="List Invoices",
        responses={
            200: openapi.Response('List of invoices', InvoiceSerializer(many=True)),
        },
        tags=['Payment']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class InvoiceDetailView(generics.RetrieveAPIView):
    """
    Retrieve invoice details.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Invoice.objects.select_related('student', 'group').all()  # type: ignore

    @swagger_auto_schema(
        operation_description="Retrieve invoice details by ID.",
        operation_summary="Get Invoice Details",
        responses={
            200: openapi.Response('Invoice details', InvoiceSerializer),
            404: openapi.Response('Invoice not found'),
        },
        tags=['Payment']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CreatePaymentView(generics.GenericAPIView):
    """
    Create payment link for invoice via Multicard payment gateway.
    """
    serializer_class = CreatePaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create payment link for invoice via Multicard payment gateway",
        operation_summary="Create Payment Link",
        request_body=CreatePaymentSerializer,
        responses={
            200: openapi.Response(
                'Payment link created',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'checkout_url': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                'short_link': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI),
                                'uuid': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response('Validation error'),
            404: openapi.Response('Invoice not found'),
        },
        tags=['Payment']
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice_id = serializer.validated_data['invoice_id']
        lang = serializer.validated_data.get('lang', 'uz')
        return_url = serializer.validated_data.get('return_url', settings.MULTICARD_RETURN_URL)
        return_error_url = serializer.validated_data.get('return_error_url', settings.MULTICARD_RETURN_ERROR_URL)
        send_sms = serializer.validated_data.get('send_sms', False)

        try:
            invoice = Invoice.objects.select_related('student', 'group').get(id=invoice_id)

            # Check permissions
            user = request.user
            if hasattr(user, 'student') and invoice.student != user.student:
                return Response(
                    {'success': False, 'message': 'You do not have permission to pay this invoice.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check if invoice can be paid
            if invoice.is_paid:
                return Response(
                    {'success': False, 'message': 'Invoice is already paid.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if invoice.status == InvoiceStatus.CANCELLED:
                return Response(
                    {'success': False, 'message': 'Invoice is cancelled.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Convert amount to tiyins (1 sum = 100 tiyins)
            amount_tiyins = int(invoice.amount * 100)

            # Prepare invoice ID for Multicard
            multicard_invoice_id = str(invoice.id)

            # Prepare SMS if requested
            sms_phone = None
            if send_sms and invoice.student.phone:
                # Normalize phone number to 998XXXXXXXXX format
                phone = invoice.student.phone.replace('+', '').replace(' ', '').replace('-', '')
                if phone.startswith('998'):
                    sms_phone = phone

            # Create invoice in Multicard
            result = multicard_service.create_invoice(
                invoice_id=multicard_invoice_id,
                amount=amount_tiyins,
                lang=lang,
                return_url=return_url,
                return_error_url=return_error_url,
                sms=sms_phone,
                ofd=None  # TODO: Add OFD data if needed
            )

            if not result.get('success'):
                return Response(
                    {'success': False, 'message': result.get('message', 'Failed to create payment link')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update invoice with Multicard data
            data = result.get('data', {})
            invoice.multicard_uuid = data.get('uuid', '')
            invoice.multicard_invoice_id = multicard_invoice_id
            invoice.checkout_url = data.get('checkout_url', '')
            invoice.status = InvoiceStatus.PENDING
            invoice.save(update_fields=['multicard_uuid', 'multicard_invoice_id', 'checkout_url', 'status', 'updated_at'])

            return Response({
                'success': True,
                'message': 'Payment link created successfully',
                'data': {
                    'checkout_url': invoice.checkout_url,
                    'short_link': data.get('short_link', ''),
                    'uuid': invoice.multicard_uuid,
                }
            })

        except ObjectDoesNotExist:
            return Response(
                {'success': False, 'message': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating payment link: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'message': 'Internal server error. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt  # Multicard callback doesn't send CSRF token
@api_view(['POST', 'GET'])  # Allow GET for testing
@permission_classes([permissions.AllowAny])  # Multicard will call this endpoint
def payment_callback(request):
    """
    Handle payment callback from Multicard.
    This endpoint is called by Multicard after payment is completed.
    """
    if request.method == 'GET':
        # For testing purposes, allow GET requests
        uuid = request.GET.get('uuid')
        invoice_id = request.GET.get('invoice_id')
        status_value = request.GET.get('status', 'success')
    else:
        serializer = PaymentCallbackSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid callback data: {serializer.errors}")
            return Response(
                {'success': False, 'message': 'Invalid callback data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        uuid = data.get('uuid')
        invoice_id = data.get('invoice_id')
        status_value = data.get('status')

    if not uuid or not invoice_id:
        logger.error("Missing uuid or invoice_id in callback")
        return Response(
            {'success': False, 'message': 'Missing required parameters'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Find invoice by multicard_invoice_id (which is our invoice.id as string)
        invoice = Invoice.objects.select_related('student', 'group').get(multicard_invoice_id=invoice_id)  # type: ignore

        # Verify UUID matches
        callback_uuid = uuid
        if invoice.multicard_uuid and invoice.multicard_uuid != callback_uuid:
            logger.warning(
                f"UUID mismatch for invoice {invoice.id}: "
                f"stored={invoice.multicard_uuid}, callback={callback_uuid}"
            )
            # Still process the payment if UUID doesn't match (might be from different payment attempt)

        # Map Multicard status to our status
        if status_value in ['success', 'paid']:
            target_status = InvoiceStatus.PAID
        elif status_value == 'cancelled':
            target_status = InvoiceStatus.CANCELLED
        elif status_value == 'pending':
            target_status = InvoiceStatus.PENDING
        else:
            target_status = InvoiceStatus.PENDING

        # Only update to PAID if status is success/paid
        if target_status != InvoiceStatus.PAID:
            logger.info(f"Invoice {invoice.id} callback with status {status_value}, not marking as paid")
            return Response({'success': True, 'message': 'Callback received, invoice status updated'})

        # If invoice is already paid but with different UUID, still return success
        if invoice.is_paid:
            logger.info(f"Invoice {invoice.id} already paid (different UUID), returning success")
            return Response({'success': True, 'message': 'Payment already processed'}, status=status.HTTP_200_OK)

        # Update invoice with payment details
        # Parse payment_time if provided, otherwise use current time
        payment_time = timezone.now()
        if request.method == 'POST':
            payment_time_str = request.data.get('payment_time')
        else:
            payment_time_str = request.GET.get('payment_time')
            
        if payment_time_str and payment_time_str.strip():
            try:
                # Try to parse Multicard payment_time format: "YYYY-MM-DD HH:MM:SS"
                payment_time = timezone.make_aware(
                    datetime.strptime(payment_time_str, '%Y-%m-%d %H:%M:%S')
                )
            except (ValueError, TypeError):
                try:
                    # Try ISO format
                    payment_time = timezone.make_aware(
                        datetime.fromisoformat(payment_time_str.replace('Z', '+00:00'))
                    )
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse payment_time '{payment_time_str}', using current time")
                    payment_time = timezone.now()
        
        with transaction.atomic():  # type: ignore
            invoice.status = InvoiceStatus.PAID
            if request.method == 'POST':
                invoice.receipt_url = request.data.get('receipt_url', '')
                invoice.payment_method = request.data.get('payment_method', '')
                invoice.card_pan = request.data.get('card_pan', '')
            else:
                invoice.receipt_url = request.GET.get('receipt_url', '')
                invoice.payment_method = request.GET.get('payment_method', '')
                invoice.card_pan = request.GET.get('card_pan', '')
            invoice.payment_time = payment_time
            invoice.multicard_uuid = callback_uuid or invoice.multicard_uuid or ''
            invoice.save(update_fields=[
                'status', 'receipt_url', 'payment_time', 'payment_method',
                'card_pan', 'multicard_uuid', 'multicard_invoice_id', 'updated_at'
            ])

        logger.info(f"Invoice {invoice.id} marked as paid via callback. UUID: {invoice.multicard_uuid}")

        # IMPORTANT: Must return HTTP 200 with success: true
        return Response({'success': True, 'message': 'Payment processed successfully'}, status=status.HTTP_200_OK)

    except ObjectDoesNotExist:
        logger.error(f"Invoice not found for multicard_invoice_id: {invoice_id}")
        # IMPORTANT: Return 200 even if invoice not found (to prevent Multicard retries)
        return Response({'success': False, 'message': 'Invoice not found'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error processing payment callback: {str(e)}", exc_info=True)
        # IMPORTANT: Even on error, return 200 to prevent Multicard retries
        return Response({'success': False, 'message': 'Error processing callback'}, status=status.HTTP_200_OK)


@csrf_exempt  # Multicard webhook doesn't send CSRF token
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Multicard will call this endpoint
def payment_webhook(request):
    """
    Handle payment webhook from Multicard.
    This endpoint receives status updates from Multicard.
    """
    logger.info(f"Received webhook: {request.data}")

    uuid = request.data.get('uuid')
    invoice_id = request.data.get('invoice_id')
    status_value = request.data.get('status')

    if not uuid or not invoice_id:
        logger.error("Missing uuid or invoice_id in webhook")
        return Response(
            {'success': False, 'message': 'Missing required parameters'},
            status=status.HTTP_200_OK  # Return 200 to prevent retries
        )

    # Find invoice
    try:
        invoice = Invoice.objects.get(multicard_invoice_id=invoice_id)  # type: ignore

        # Map Multicard status to our status
        status_mapping = {
            'draft': InvoiceStatus.CREATED,
            'progress': InvoiceStatus.PENDING,
            'success': InvoiceStatus.PAID,
            'error': InvoiceStatus.CANCELLED,
            'revert': InvoiceStatus.REFUNDED,
        }

        new_status = status_mapping.get(status_value, InvoiceStatus.PENDING)

        # Update invoice
        with transaction.atomic():  # type: ignore
            invoice.status = new_status
            invoice.multicard_uuid = uuid

            if status_value == 'success' and not invoice.payment_time:
                invoice.payment_time = timezone.now()
                invoice.receipt_url = request.data.get('receipt_url', '')
                invoice.payment_method = request.data.get('ps', '')
                invoice.card_pan = request.data.get('card_pan', '')

            invoice.save()

        logger.info(f"Invoice {invoice.id} status updated to {new_status} via webhook")

        return Response({'success': True, 'message': 'Webhook processed successfully'})

    except ObjectDoesNotExist:
        logger.error(f"Invoice not found for Multicard invoice_id: {invoice_id}")
        # IMPORTANT: Webhooks should return HTTP 2xx
        return Response(
            {'success': False, 'message': 'Invoice not found'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Error processing payment webhook: {str(e)}", exc_info=True)
        # IMPORTANT: Webhooks should return HTTP 2xx (otherwise will retry 5 times)
        return Response(
            {'success': False, 'message': 'Internal server error'},
            status=status.HTTP_200_OK
        )


class CheckInvoiceStatusView(generics.GenericAPIView):
    """
    Check invoice status from Multicard.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check invoice payment status from Multicard",
        operation_summary="Check Invoice Status",
        manual_parameters=[
            openapi.Parameter(
                'invoice_id',
                openapi.IN_QUERY,
                description='Invoice ID',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response('Invoice status'),
            404: openapi.Response('Invoice not found'),
        },
        tags=['Payment']
    )
    def get(self, request, *args, **kwargs):
        invoice_id = request.query_params.get('invoice_id')
        
        if not invoice_id:
            return Response(
                {'success': False, 'message': 'invoice_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = Invoice.objects.select_related('student', 'group').get(id=invoice_id)  # type: ignore

            # Check permissions
            user = request.user
            if hasattr(user, 'student') and invoice.student != user.student:
                return Response(
                    {'success': False, 'message': 'You do not have permission to check this invoice.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Check status from Multicard
            if not invoice.multicard_invoice_id:
                return Response({
                    'success': False,
                    'message': 'Invoice has no Multicard invoice ID',
                    'data': {
                        'invoice_id': invoice.id,
                        'status': invoice.status
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            result = multicard_service.check_invoice_status(invoice.multicard_invoice_id)


            if result.get('success'):
                multicard_data = result.get('data', {})
                payment_data = multicard_data.get('payment', {})

                # Update invoice if status changed
                multicard_status = payment_data.get('status', '')
                status_mapping = {
                    'draft': InvoiceStatus.CREATED,
                    'progress': InvoiceStatus.PENDING,
                    'success': InvoiceStatus.PAID,
                    'error': InvoiceStatus.CANCELLED,
                    'revert': InvoiceStatus.REFUNDED,
                }

                new_status = status_mapping.get(multicard_status, invoice.status)

                if new_status != invoice.status:
                    invoice.status = new_status
                    if multicard_status == 'success' and not invoice.payment_time:
                        invoice.payment_time = timezone.now()
                        invoice.receipt_url = multicard_data.get('receipt_url', '')
                    invoice.save()

                return Response({
                    'success': True,
                    'data': {
                        'invoice_id': invoice.id,
                        'status': invoice.status,
                        'multicard_status': multicard_status,
                        'checkout_url': invoice.checkout_url,
                        'receipt_url': invoice.receipt_url,
                        'payment_time': invoice.payment_time
                    }
                })
            else:
                return Response(
                    {
                        'success': False,
                        'message': result.get('message', 'Failed to get invoice status'),
                        'data': {
                            'invoice_id': invoice.id,
                            'status': invoice.status
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ObjectDoesNotExist:
            return Response(
                {'success': False, 'message': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking invoice status: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'message': 'Internal server error. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmployeeInvoiceListView(generics.ListAPIView):
    """
    List all invoices for employees.
    Mentors can see only invoices from their groups.
    Developer/Director/Administrator can see all invoices.
    """
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        
        user = self.request.user
        queryset = Invoice.objects.select_related('student', 'group', 'group__mentor').all()  # type: ignore

        # Only employees can access this view
        if not hasattr(user, 'employee_profile'):
            return Invoice.objects.none()

        # If user is Mentor, filter by their groups
        user_role = user.employee_profile.role
        if user_role == 'mentor':
            mentor_employee = user.employee_profile
            queryset = queryset.filter(group__mentor=mentor_employee)
        # If user is Developer/Director/Administrator, show all invoices

        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(student__full_name__icontains=search) |
                Q(student__phone__icontains=search) |
                Q(group__speciality_id__icontains=search) |
                Q(id__icontains=search)
            )

        # Status filter
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset

    @swagger_auto_schema(
        operation_description="To'lovlarni ro'yxatlash. Mentor faqat o'z guruhlarining to'lovlarini ko'radi, Dasturchi/Direktor/Administrator barcha to'lovlarni ko'radi.",
        operation_summary="To'lovlarni Ro'yxatlash",
        responses={
            200: openapi.Response('To\'lovlar muvaffaqiyatli yuklandi.', InvoiceSerializer(many=True)),
        },
        tags=['Payment']
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'message': 'To\'lovlar muvaffaqiyatli yuklandi.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class MarkInvoicesAsPaidView(generics.GenericAPIView):
    """
    Mark one or multiple invoices as paid manually.
    Only Accountant, Director, and Developer can use this endpoint.
    Used when payments are made offline or through other payment methods.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MarkInvoicesAsPaidSerializer

    def check_permissions(self, request):
        """Only Accountant, Director, and Developer can mark invoices as paid"""
        super().check_permissions(request)
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only employees can mark invoices as paid")
        role = request.user.employee_profile.role
        if role not in ['buxgalter', 'direktor', 'dasturchi']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to mark invoices as paid")

    @swagger_auto_schema(
        operation_description="Manually mark invoices as paid. Only Accountant, Director, and Developer can use this.",
        operation_summary="Mark Invoices as Paid",
        request_body=MarkInvoicesAsPaidSerializer,
        responses={
            200: openapi.Response('Invoices marked as paid successfully'),
            400: openapi.Response('Validation error'),
            403: openapi.Response('Permission denied'),
        },
        tags=['Payment']
    )
    def post(self, request):
        self.check_permissions(request)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        invoice_ids = serializer.validated_data['invoice_ids']
        payment_time = serializer.validated_data.get('payment_time') or timezone.now()
        payment_method = serializer.validated_data.get('payment_method', 'manual')
        
        try:
            with transaction.atomic():
                invoices = Invoice.objects.filter(id__in=invoice_ids)
                updated_count = 0
                
                for invoice in invoices:
                    if invoice.status != InvoiceStatus.PAID:
                        invoice.status = InvoiceStatus.PAID
                        invoice.payment_time = payment_time
                        invoice.payment_method = payment_method
                        invoice.save(update_fields=['status', 'payment_time', 'payment_method', 'updated_at'])
                        updated_count += 1
                
                return Response({
                    'success': True,
                    'message': f'{updated_count} invoice(s) marked as paid successfully',
                    'updated_count': updated_count,
                    'total_count': len(invoice_ids),
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error marking invoices as paid: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'message': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
