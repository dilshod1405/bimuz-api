from rest_framework import status, generics, permissions
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from education.models import Group
from user.models import Student
from education.api.serializers import GroupSerializer
from education.api.booking_serializers import (
    GroupBookingSerializer,
    StudentBookingSerializer,
    AlternativeGroupSuggestionSerializer
)
from education.api.permissions import IsAdministratorOrMentor
from education.api.utils import success_response, error_response
from payment.models import Invoice, InvoiceStatus


class GroupBookingListView(generics.ListAPIView):
    """
    List all groups available for booking.
    Shows groups that can accept bookings based on 10-day rule.
    """
    serializer_class = GroupBookingSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Group._default_manager.all().select_related('mentor', 'mentor__user').prefetch_related('students')
        return queryset
    
    @swagger_auto_schema(
        operation_description="List all groups available for booking",
        operation_summary="List Available Groups for Booking",
        responses={
            200: openapi.Response('List of available groups', GroupBookingSerializer(many=True)),
        },
        tags=['Student Booking']
    )
    def get(self, request, *args, **kwargs):
        groups = self.get_queryset()
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StudentBookingCreateView(generics.CreateAPIView):
    """
    Create a booking for a student in a group.
    Validates:
    - Student exists and is not already booked
    - Group has available seats
    - Group can accept bookings (10-day rule)
    """
    serializer_class = StudentBookingSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_description="Book a student into a group. Validates seat availability and 10-day rule.",
        operation_summary="Book Student into Group",
        request_body=StudentBookingSerializer,
        responses={
            201: openapi.Response('Booking created successfully'),
            400: openapi.Response('Validation errors or booking not allowed'),
        },
        tags=['Student Booking']
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        student_id = serializer.validated_data['student_id']
        group_id = serializer.validated_data['group_id']
        
        try:
            with transaction.atomic():  # type: ignore
                student = Student._default_manager.select_for_update().get(id=student_id)
                group = Group._default_manager.select_for_update().get(id=group_id)
                
                if student.group:
                    return error_response(
                        message='Talaba boshqa guruhga allaqachon yozilgan.',
                        errors={'student_id': ['Talaba allaqachon guruhga yozilgan.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if group.available_seats <= 0:
                    alternatives = self._get_alternative_groups(group)
                    return error_response(
                        message='Bu guruhda bo\'sh o\'rin yo\'q.',
                        errors={'group_id': ['Guruh to\'liq.']},
                        status_code=status.HTTP_400_BAD_REQUEST,
                        data={'alternatives': alternatives} if alternatives else None
                    )
                
                if not group.can_accept_bookings():
                    days_since = group.days_since_start()
                    if days_since is not None and days_since >= 10:
                        alternatives = self._get_alternative_groups(group)
                        return error_response(
                            message=f'Bu guruhga yozilish mumkin emas. Guruh {days_since} kun oldin boshlangan (10 kunlik cheklov oshib ketgan).',
                            errors={'group_id': ['10 kunlik yozilish muddati oshib ketgan.']},
                            status_code=status.HTTP_400_BAD_REQUEST,
                            data={'alternatives': alternatives} if alternatives else None
                        )
                
                student.group = group
                student.save()
                
                # Calculate payment information based on group price
                group_price = float(group.price) if group.price else 0
                first_installment = group_price / 2 if group_price > 0 else 0
                second_installment = group_price - first_installment if group_price > 0 else 0
                
                # Calculate payment milestones based on total_lessons
                payment_info = {
                    'total_price': group_price,
                    'currency': 'UZS'
                }
                
                if group.total_lessons and group.total_lessons > 0:
                    midpoint_lesson = group.total_lessons // 2
                    final_lesson = group.total_lessons
                    
                    payment_info['first_installment'] = {
                        'amount': first_installment,
                        'percentage': 50,
                        'due_by_lesson': midpoint_lesson,
                        'lesson_range': {
                            'from_lesson': 1,
                            'to_lesson': midpoint_lesson,
                            'description': f"Lessons 1 to {midpoint_lesson}"
                        },
                        'description': f"First payment (50%) must be paid by lesson {midpoint_lesson}"
                    }
                    
                    payment_info['second_installment'] = {
                        'amount': second_installment,
                        'percentage': 50,
                        'due_by_lesson': final_lesson,
                        'lesson_range': {
                            'from_lesson': midpoint_lesson + 1,
                            'to_lesson': final_lesson,
                            'description': f"Lessons {midpoint_lesson + 1} to {final_lesson}"
                        },
                        'description': f"Second payment (50%) must be paid by lesson {final_lesson}"
                    }
                    
                    payment_info['total_lessons'] = group.total_lessons
                else:
                    # If total_lessons is not set, still show payment info without milestones
                    payment_info['first_installment'] = {
                        'amount': first_installment,
                        'percentage': 50,
                        'due_by_lesson': None,
                        'lesson_range': None,
                        'description': "First payment (50%)"
                    }
                    
                    payment_info['second_installment'] = {
                        'amount': second_installment,
                        'percentage': 50,
                        'due_by_lesson': None,
                        'lesson_range': None,
                        'description': "Second payment (50%)"
                    }
                    
                    payment_info['total_lessons'] = None
                    payment_info['note'] = "Payment milestones will be set when total_lessons is configured for this group"
                
                # Get the invoice that was just created (by signal)
                invoice = Invoice.objects.filter(
                    student=student,
                    group=group,
                    status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING]
                ).order_by('-created_at').first()
                
                # Add invoice ID if invoice was created
                if invoice:
                    payment_info['first_invoice'] = {
                        'id': invoice.id,
                        'status': invoice.status,
                        'status_display': invoice.get_status_display(),
                        'amount': float(invoice.amount)
                    }
                else:
                    payment_info['first_invoice'] = None
                    payment_info['note'] = (payment_info.get('note', '') + ' Invoice will be created automatically.').strip()
                
                group_serializer = GroupBookingSerializer(group, context={'request': request})
                
                return success_response(
                    data={
                        'booking': {
                            'student_id': student.id,
                            'student_name': student.full_name,
                            'group': group_serializer.data,
                            'payment_info': payment_info
                        }
                    },
                    message='Talaba muvaffaqiyatli guruhga yozildi.',
                    status_code=status.HTTP_201_CREATED
                )
        except Student.DoesNotExist:
            return error_response(
                message='Talaba topilmadi.',
                errors={'student_id': ['Talaba mavjud emas.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return error_response(
                message='Guruh topilmadi.',
                errors={'group_id': ['Guruh mavjud emas.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
    
    def _get_alternative_groups(self, original_group):
        """
        Get alternative groups with similar speciality that are planned and have available seats.
        """
        alternatives = Group._default_manager.filter(
            speciality_id=original_group.speciality_id,
            is_active=True
        ).exclude(id=original_group.id).select_related('mentor', 'mentor__user').prefetch_related('students')
        
        available_alternatives = []
        for group in alternatives:
            if group.can_accept_bookings() and group.available_seats > 0:
                available_alternatives.append(group)
        
        if available_alternatives:
            serializer = AlternativeGroupSuggestionSerializer(available_alternatives[:5], many=True)
            return serializer.data
        return []


class StudentBookingCancelView(generics.GenericAPIView):
    """
    Cancel a student's booking (remove student from group).
    
    Permission Rules:
    - Students can cancel their own booking ONLY if the group hasn't started yet
    - Administrators and Mentors can cancel any booking at any time
    """
    permission_classes = [permissions.AllowAny]
    
    def _is_group_started(self, group: Group) -> bool:
        """Check if group has started (starting_date is in the past or today)."""
        if not group.starting_date:
            return False
        today = timezone.now().date()
        return group.starting_date <= today
    
    def _is_admin_or_mentor(self, request) -> bool:
        """Check if user is administrator or mentor."""
        if not request.user or not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'employee_profile'):
            return False
        role = request.user.employee_profile.role
        return role in ['administrator', 'mentor', 'dasturchi']
    
    @swagger_auto_schema(
        operation_description="Cancel a student's booking by removing them from their group. "
                              "Students can only cancel if group hasn't started. "
                              "Administrators and Mentors can cancel at any time.",
        operation_summary="Cancel Student Booking",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'student_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Student ID')
            },
            required=['student_id']
        ),
        responses={
            200: openapi.Response('Booking cancelled successfully'),
            400: openapi.Response('Student has no booking or group has started (for students)'),
            403: openapi.Response('Permission denied - Group has started, only admin/mentor can cancel'),
            404: openapi.Response('Student not found'),
        },
        tags=['Student Booking']
    )
    def post(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        
        if not student_id:
            return error_response(
                message='student_id talab qilinadi.',
                errors={'student_id': ['Bu maydon to\'ldirilishi shart.']},
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():  # type: ignore
                student = Student._default_manager.select_for_update().get(id=student_id)
                
                if not student.group:
                    return error_response(
                        message='Talabaning faol yozilishi yo\'q.',
                        errors={'student_id': ['Talaba hech qanday guruhga yozilmagan.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                group = student.group
                
                # Check permissions: Students can only cancel if group hasn't started
                is_admin_or_mentor = self._is_admin_or_mentor(request)
                group_started = self._is_group_started(group)
                
                if not is_admin_or_mentor and group_started:
                    return error_response(
                        message='Guruh boshlanganidan keyin talaba o\'zi bekor qila olmaydi. '
                               'Iltimos, administrator yoki mentor bilan bog\'laning.',
                        errors={'group_id': ['Guruh boshlangan. Faqat administrator yoki mentor bekor qilishi mumkin.']},
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                
                # Cancel the booking
                student.group = None
                student.save()
                
                # Cancel unpaid invoices for this student-group combination
                unpaid_invoices = Invoice.objects.filter(
                    student=student,
                    group=group,
                    status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING]
                )
                cancelled_count = unpaid_invoices.update(status=InvoiceStatus.CANCELLED)
                
                return success_response(
                    data={
                        'cancelled_booking': {
                            'student_id': student.id,
                            'student_name': student.full_name,
                            'group_id': group.id,
                            'group_name': str(group),
                            'cancelled_invoices': cancelled_count
                        }
                    },
                    message='Yozilish muvaffaqiyatli bekor qilindi.',
                    status_code=status.HTTP_200_OK
                )
        except Student.DoesNotExist:  # type: ignore
            return error_response(
                message='Talaba topilmadi.',
                errors={'student_id': ['Talaba mavjud emas.']},
                status_code=status.HTTP_404_NOT_FOUND
            )


class StudentGroupChangeView(generics.GenericAPIView):
    """
    Change a student's group (Administrator only).
    
    Handles price differences:
    - If new group is more expensive: Creates new invoice for the difference
    - If new group is cheaper: Reports refund amount to administrator
    """
    permission_classes = [IsAdministratorOrMentor]
    
    @swagger_auto_schema(
        operation_description="Change a student's group. Handles price differences automatically. "
                              "If new group is more expensive, creates invoice for difference. "
                              "If cheaper, reports refund amount.",
        operation_summary="Change Student Group (Admin/Mentor)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'student_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Student ID'),
                'new_group_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='New Group ID')
            },
            required=['student_id', 'new_group_id']
        ),
        responses={
            200: openapi.Response('Group changed successfully'),
            400: openapi.Response('Validation errors'),
            403: openapi.Response('Permission denied - Administrator or Mentor role required'),
            404: openapi.Response('Student or Group not found'),
        },
        security=[{'Bearer': []}],
        tags=['Student Booking']
    )
    def post(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        new_group_id = request.data.get('new_group_id')
        
        if not student_id or not new_group_id:
            return error_response(
                message='student_id va new_group_id talab qilinadi.',
                errors={
                    'student_id': ['Bu maydon to\'ldirilishi shart.'] if not student_id else None,
                    'new_group_id': ['Bu maydon to\'ldirilishi shart.'] if not new_group_id else None
                },
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                student = Student._default_manager.select_for_update().get(id=student_id)
                new_group = Group._default_manager.select_for_update().get(id=new_group_id)
                
                old_group = student.group
                
                if not old_group:
                    return error_response(
                        message='Talaba hech qanday guruhga yozilmagan.',
                        errors={'student_id': ['Talabaning mavjud guruhi yo\'q.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if old_group.id == new_group.id:
                    return error_response(
                        message='Talaba allaqachon bu guruhga yozilgan.',
                        errors={'new_group_id': ['Yangi guruh mavjud guruh bilan bir xil.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if new_group.available_seats <= 0:
                    return error_response(
                        message='Yangi guruhda bo\'sh o\'rin yo\'q.',
                        errors={'new_group_id': ['Guruh to\'liq.']},
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculate price difference
                old_price = float(old_group.price) if old_group.price else 0
                new_price = float(new_group.price) if new_group.price else 0
                price_difference = new_price - old_price
                
                # Get paid amount from old group invoices
                paid_invoices = Invoice.objects.filter(
                    student=student,
                    group=old_group,
                    status=InvoiceStatus.PAID
                )
                total_paid = sum(float(inv.amount) for inv in paid_invoices)
                
                # Cancel unpaid invoices for old group
                unpaid_invoices = Invoice.objects.filter(
                    student=student,
                    group=old_group,
                    status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING]
                )
                cancelled_count = unpaid_invoices.update(status=InvoiceStatus.CANCELLED)
                
                # Change student's group
                student.group = new_group
                student.save()
                
                # Handle price differences
                refund_amount = 0
                new_invoice_amount = 0
                new_invoice_id = None
                
                if price_difference > 0:
                    # New group is more expensive - create invoice for difference
                    # Calculate first installment (50% of new price)
                    first_installment = new_price / 2
                    new_invoice_amount = first_installment
                    
                    # Create new invoice for first installment
                    new_invoice = Invoice.objects.create(
                        student=student,
                        group=new_group,
                        amount=new_invoice_amount,
                        status=InvoiceStatus.CREATED,
                        notes=f"First installment (50%) for group change. Old group: {old_group.id}, New group: {new_group.id}. "
                              f"Price difference: +{price_difference} UZS. Total paid for old group: {total_paid} UZS."
                    )
                    new_invoice_id = new_invoice.id
                    
                elif price_difference < 0:
                    # New group is cheaper - calculate refund amount
                    refund_amount = abs(price_difference)
                    # If student paid more than new group price, refund the excess
                    if total_paid > new_price:
                        refund_amount = total_paid - new_price
                    else:
                        # Student hasn't paid enough, but new group is cheaper
                        # Create invoice for first installment of new group
                        first_installment = new_price / 2
                        new_invoice_amount = first_installment
                        
                        new_invoice = Invoice.objects.create(
                            student=student,
                            group=new_group,
                            amount=new_invoice_amount,
                            status=InvoiceStatus.CREATED,
                            notes=f"First installment (50%) for group change. Old group: {old_group.id}, New group: {new_group.id}. "
                                  f"Price difference: {price_difference} UZS (cheaper). Total paid for old group: {total_paid} UZS. "
                                  f"Refund amount: {refund_amount} UZS."
                        )
                        new_invoice_id = new_invoice.id
                else:
                    # Same price - just create first installment invoice
                    first_installment = new_price / 2
                    new_invoice_amount = first_installment
                    
                    new_invoice = Invoice.objects.create(
                        student=student,
                        group=new_group,
                        amount=new_invoice_amount,
                        status=InvoiceStatus.CREATED,
                        notes=f"First installment (50%) for group change. Old group: {old_group.id}, New group: {new_group.id}. "
                              f"Same price. Total paid for old group: {total_paid} UZS."
                    )
                    new_invoice_id = new_invoice.id
                
                response_data = {
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'old_group_id': old_group.id,
                    'old_group_name': str(old_group),
                    'old_group_price': old_price,
                    'new_group_id': new_group.id,
                    'new_group_name': str(new_group),
                    'new_group_price': new_price,
                    'price_difference': price_difference,
                    'total_paid_old_group': total_paid,
                    'cancelled_invoices': cancelled_count,
                    'new_invoice_id': new_invoice_id,
                    'new_invoice_amount': new_invoice_amount
                }
                
                if refund_amount > 0:
                    response_data['refund_amount'] = refund_amount
                    response_data['refund_required'] = True
                    response_data['message'] = f'Guruh o\'zgartirildi. Qaytarib berish kerak: {refund_amount:,.2f} UZS.'
                else:
                    response_data['refund_required'] = False
                
                return success_response(
                    data=response_data,
                    message='Guruh muvaffaqiyatli o\'zgartirildi.',
                    status_code=status.HTTP_200_OK
                )
                
        except Student.DoesNotExist:
            return error_response(
                message='Talaba topilmadi.',
                errors={'student_id': ['Talaba mavjud emas.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Group.DoesNotExist:
            return error_response(
                message='Guruh topilmadi.',
                errors={'new_group_id': ['Guruh mavjud emas.']},
                status_code=status.HTTP_404_NOT_FOUND
            )
