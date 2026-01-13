from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime
import logging

from payment.models import Invoice, InvoiceStatus
from payment.serializers import InvoiceSerializer, CreatePaymentSerializer, PaymentCallbackSerializer
from payment.multicard_service import multicard_service
from user.models import Student

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
        queryset = Invoice.objects.select_related('student', 'group').all()

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
    queryset = Invoice.objects.select_related('student', 'group').all()

    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.select_related('student', 'group').all()

        # If user is a student, filter by their invoices
        if hasattr(user, 'student'):
            queryset = queryset.filter(student=user.student)

        return queryset

    @swagger_auto_schema(
        operation_description="Get invoice details by ID",
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
    Create payment link for invoice via Multicard.
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
        return_url = serializer.validated_data.get('return_url')
        return_error_url = serializer.validated_data.get('return_error_url')
        lang = serializer.validated_data.get('lang', 'uz')
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
                    {
                        'success': False,
                        'message': result.get('message', 'Failed to create payment link')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            data = result.get('data', {})

            # Update invoice with Multicard data
            with transaction.atomic():
                invoice.multicard_uuid = data.get('uuid')
                invoice.multicard_invoice_id = multicard_invoice_id
                invoice.checkout_url = data.get('checkout_url')
                invoice.status = InvoiceStatus.PENDING
                invoice.save(update_fields=['multicard_uuid', 'multicard_invoice_id', 'checkout_url', 'status', 'updated_at'])
                
                logger.info(
                    f"Invoice {invoice.id} updated with Multicard data: "
                    f"uuid={invoice.multicard_uuid}, invoice_id={invoice.multicard_invoice_id}, "
                    f"checkout_url={invoice.checkout_url}"
                )

            return Response({
                'success': True,
                'data': {
                    'checkout_url': data.get('checkout_url'),
                    'short_link': data.get('short_link'),
                    'deeplink': data.get('deeplink'),
                    'uuid': data.get('uuid'),
                    'invoice_id': invoice.id
                },
                'message': 'Payment link created successfully'
            }, status=status.HTTP_200_OK)

        except Invoice.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating payment link: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'message': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt  # Multicard callback doesn't send CSRF token
@api_view(['POST', 'GET'])  # Allow GET for testing
@permission_classes([permissions.AllowAny])  # Multicard will call this endpoint
def payment_callback(request):
    """
    Handle payment callback from Multicard.
    This endpoint receives payment notifications from Multicard.
    """
    # Handle GET requests for testing
    if request.method == 'GET':
        return Response({
            'success': True,
            'message': 'Callback endpoint is reachable',
            'endpoint': '/api/v1/payment/callback/',
            'method': 'POST',
            'note': 'This endpoint should receive POST requests from Multicard'
        }, status=status.HTTP_200_OK)
    
    logger.info(f"Payment callback received. Method: {request.method}, Content-Type: {request.content_type}")
    logger.info(f"Callback request headers: {dict(request.headers)}")
    
    # DRF automatically parses JSON, so we can use request.data directly
    # Don't access request.body after request.data - it will cause RawPostDataException
    try:
        # Use DRF parsed data (already parsed from JSON)
        data = request.data if hasattr(request, 'data') else {}
        
        # Try to get raw body for logging (only if not already consumed)
        try:
            if hasattr(request, '_body') and request._body:
                logger.info(f"Callback request body (raw): {request._body}")
        except Exception:
            pass  # Body already consumed, skip logging
        
        logger.info(f"Callback request data (parsed): {data}")
    except Exception as e:
        logger.error(f"Error getting request data: {e}", exc_info=True)
        # Fallback to empty dict
        data = {}
    
    logger.info(f"Final callback data: {data}")
    
    serializer = PaymentCallbackSerializer(data=data)
    if not serializer.is_valid():
        logger.error(f"Invalid callback data: {serializer.errors}")
        logger.error(f"Received data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        # IMPORTANT: Multicard requires HTTP 200 even for errors, but with success: false
        # The message will be shown to the user
        return Response(
            {'success': False, 'message': 'Неверные данные запроса'},
            status=status.HTTP_200_OK
        )

    validated_data = serializer.validated_data
    logger.info(f"Validated callback data: invoice_id={validated_data.get('invoice_id')}, uuid={validated_data.get('uuid')}")

    # Verify signature
    secret = getattr(settings, 'MULTICARD_SECRET', None)
    store_id = getattr(settings, 'MULTICARD_STORE_ID', None)

    if not secret or not store_id:
        logger.error("Multicard credentials not configured")
        # IMPORTANT: Return HTTP 200 with success: false (message will be shown to user)
        return Response(
            {'success': False, 'message': 'Ошибка конфигурации платежного сервиса'},
            status=status.HTTP_200_OK
        )

    # Verify signature
    invoice_id_str = str(validated_data['invoice_id'])
    amount_int = int(validated_data['amount'])
    sign_str = str(validated_data['sign'])
    
    # Debug signature verification
    import hashlib
    sign_string = f"{store_id}{invoice_id_str}{amount_int}{secret}"
    expected_sign = hashlib.md5(sign_string.encode()).hexdigest()
    
    logger.info(f"Signature verification: store_id={store_id}, invoice_id={invoice_id_str}, amount={amount_int}")
    logger.info(f"Sign string: {sign_string}")
    logger.info(f"Expected sign (MD5): {expected_sign}")
    logger.info(f"Received sign: {sign_str}")
    
    is_valid = multicard_service.verify_callback_signature(
        store_id=store_id,
        invoice_id=invoice_id_str,
        amount=amount_int,
        secret=secret,
        sign=sign_str
    )

    if not is_valid:
        logger.warning(f"Invalid callback signature for invoice {invoice_id_str}")
        logger.warning(f"Expected: {expected_sign.lower()}, Received: {sign_str.lower()}")
        # IMPORTANT: Return HTTP 200 with success: false (message will be shown to user)
        return Response(
            {'success': False, 'message': 'Неверная подпись запроса'},
            status=status.HTTP_200_OK
        )
    
    logger.info(f"Signature verified successfully for invoice {invoice_id_str}")

    # Find invoice by Multicard invoice_id (try both string and integer)
    # invoice_id_str already set above
    invoice = None
    
    try:
        # First try to find by multicard_invoice_id
        invoice = Invoice.objects.get(multicard_invoice_id=invoice_id_str)
        logger.info(f"Found invoice {invoice.id} by multicard_invoice_id={invoice_id_str}")
    except Invoice.DoesNotExist:
        try:
            # Try to find by invoice ID directly (in case multicard_invoice_id wasn't set)
            invoice_id_int = int(validated_data['invoice_id'])
            invoice = Invoice.objects.get(id=invoice_id_int)
            logger.info(f"Found invoice {invoice.id} by id={invoice_id_int}")
            # Update multicard_invoice_id for future callbacks
            invoice.multicard_invoice_id = invoice_id_str
        except (Invoice.DoesNotExist, ValueError):
            logger.error(f"Invoice not found for Multicard invoice_id: {invoice_id_str}")
            logger.error(f"Available invoices with multicard_invoice_id: {list(Invoice.objects.exclude(multicard_invoice_id__isnull=True).values_list('id', 'multicard_invoice_id'))}")
            # IMPORTANT: Return HTTP 200 with success: false (message will be shown to user)
            # According to docs: "Не найден инвойс" will be displayed to user
            return Response(
                {'success': False, 'message': 'Не найден инвойс'},
                status=status.HTTP_200_OK
            )

    # Check idempotency by UUID (if same uuid already processed)
    callback_uuid = validated_data.get('uuid', '')
    if callback_uuid and invoice.multicard_uuid == callback_uuid and invoice.is_paid:
        logger.info(f"Invoice {invoice.id} already paid with same UUID {callback_uuid}, returning success (idempotency)")
        return Response({'success': True, 'message': 'Payment already processed'}, status=status.HTTP_200_OK)
    
    # If invoice is already paid but with different UUID, still return success
    if invoice.is_paid:
        logger.info(f"Invoice {invoice.id} already paid (different UUID), returning success")
        return Response({'success': True, 'message': 'Payment already processed'}, status=status.HTTP_200_OK)

    # Update invoice with payment details
    try:
        # Parse payment_time if provided, otherwise use current time
        payment_time_str = validated_data.get('payment_time') or ''
        payment_time = timezone.now()
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
        
        with transaction.atomic():
            invoice.status = InvoiceStatus.PAID
            invoice.receipt_url = validated_data.get('receipt_url', '') or ''
            invoice.payment_time = payment_time
            invoice.payment_method = validated_data.get('ps', '') or ''
            invoice.card_pan = validated_data.get('card_pan', '') or ''
            invoice.multicard_uuid = validated_data.get('uuid', invoice.multicard_uuid) or ''
            invoice.save(update_fields=[
                'status', 'receipt_url', 'payment_time', 'payment_method',
                'card_pan', 'multicard_uuid', 'multicard_invoice_id', 'updated_at'
            ])

        logger.info(f"Invoice {invoice.id} marked as paid via callback. UUID: {invoice.multicard_uuid}")

        # IMPORTANT: Must return HTTP 200 with success: true
        return Response({'success': True, 'message': 'Payment processed successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error updating invoice {invoice.id}: {str(e)}", exc_info=True)
        # IMPORTANT: Return HTTP 200 with success: false (message will be shown to user)
        # According to docs, if we return 500 or timeout, Multicard will freeze the transaction
        return Response(
            {'success': False, 'message': 'Ошибка обработки платежа'},
            status=status.HTTP_200_OK
        )


@csrf_exempt  # Multicard webhook doesn't send CSRF token
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Multicard will call this endpoint
def payment_webhook(request):
    """
    Handle payment webhook from Multicard.
    This endpoint receives status updates for payments.
    """
    # Extract data from request
    uuid = request.data.get('uuid')
    invoice_id = request.data.get('invoice_id')
    amount = request.data.get('amount')
    status_value = request.data.get('status')
    sign = request.data.get('sign')

    if not all([uuid, invoice_id, amount, status_value, sign]):
        logger.error(f"Incomplete webhook data: {request.data}")
        # IMPORTANT: Webhooks should return HTTP 2xx (docs say HTTP 2xx)
        return Response(
            {'success': False, 'message': 'Incomplete webhook data'},
            status=status.HTTP_200_OK
        )

    # Verify signature
    secret = getattr(settings, 'MULTICARD_SECRET', None)
    if not secret:
        logger.error("Multicard secret not configured")
        # IMPORTANT: Webhooks should return HTTP 2xx
        return Response(
            {'success': False, 'message': 'Payment service configuration error'},
            status=status.HTTP_200_OK
        )

    is_valid = multicard_service.verify_webhook_signature(
        uuid=uuid,
        invoice_id=invoice_id,
        amount=amount,
        secret=secret,
        sign=sign
    )

    if not is_valid:
        logger.warning(f"Invalid webhook signature for invoice {invoice_id}")
        # IMPORTANT: Webhooks should return HTTP 2xx
        return Response(
            {'success': False, 'message': 'Invalid signature'},
            status=status.HTTP_200_OK
        )

    # Find invoice
    try:
        invoice = Invoice.objects.get(multicard_invoice_id=invoice_id)

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
        with transaction.atomic():
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

    except Invoice.DoesNotExist:
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
            invoice = Invoice.objects.select_related('student').get(id=invoice_id)

            # Check permissions
            user = request.user
            if hasattr(user, 'student') and invoice.student != user.student:
                return Response(
                    {'success': False, 'message': 'You do not have permission to view this invoice.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if not invoice.multicard_uuid:
                return Response({
                    'success': True,
                    'data': {
                        'invoice_id': invoice.id,
                        'status': invoice.status,
                        'message': 'Payment link not created yet'
                    }
                })

            # Get status from Multicard
            result = multicard_service.get_invoice_status(invoice.multicard_uuid)

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

        except Invoice.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Invoice not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error checking invoice status: {str(e)}", exc_info=True)
            return Response(
                {'success': False, 'message': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )