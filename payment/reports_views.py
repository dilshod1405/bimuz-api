"""
Reports API views for financial calculations and salary management.
All calculations are done on the backend for security and accuracy.
"""
from decimal import Decimal
from datetime import datetime
from django.db.models import Sum, Q, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)

from payment.models import Invoice, InvoiceStatus, EmployeeSalary, MentorPayment
from user.models import Employee
from education.models import Group
from payment.reports_serializers import (
    MentorEarningsSerializer,
    EmployeeSalarySerializer,
    FinancialSummarySerializer,
    MonthlyReportSerializer,
)
from user.api.permissions import IsDeveloperOrAdministrator


class MonthlyReportsView(generics.GenericAPIView):
    """
    Get monthly financial reports including:
    - Total revenue
    - Mentor earnings (with payment splits)
    - Director share
    - Employee salaries
    - Director remaining amount
    
    Accessible by: Developer, Director, Administrator, Accountant
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        """Only Developer, Director, Administrator, and Accountant can view reports"""
        super().check_permissions(request)
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only employees can access reports")
        role = request.user.employee_profile.role
        if role not in ['dasturchi', 'direktor', 'administrator', 'buxgalter']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to view reports")

    @staticmethod
    def calculate_payment_split(amount: Decimal, students_count: int) -> tuple[Decimal, Decimal]:
        """
        Calculate payment split between director and mentor.
        Rules:
        - If students <= 6: Director 45%, Mentor 55%
        - If students > 6: Director 40%, Mentor 60%
        """
        if students_count <= 6:
            director_percent = Decimal('0.45')
            mentor_percent = Decimal('0.55')
        else:
            director_percent = Decimal('0.40')
            mentor_percent = Decimal('0.60')
        
        director_share = amount * director_percent
        mentor_payment = amount * mentor_percent
        
        return director_share, mentor_payment

    def get_monthly_mentor_earnings(self, year: int, month: int):
        """
        Calculate mentor earnings for a specific month with payment splits.
        Returns detailed breakdown per mentor including group-level details.
        """
        # Get start and end dates for the month (timezone aware)
        start_date = timezone.make_aware(datetime(year, month, 1))
        if month == 12:
            end_date = timezone.make_aware(datetime(year + 1, 1, 1))
        else:
            end_date = timezone.make_aware(datetime(year, month + 1, 1))

        # Get all paid invoices in this month
        invoices = Invoice.objects.filter(
            status=InvoiceStatus.PAID,
            payment_time__gte=start_date,
            payment_time__lt=end_date
        ).select_related('student', 'group', 'group__mentor')

        # Group invoices by mentor
        mentor_data = {}
        
        for invoice in invoices:
            group = invoice.group
            if not group or not group.mentor:
                continue
            
            mentor_id = group.mentor.id
            mentor = group.mentor
            
            if mentor_id not in mentor_data:
                mentor_data[mentor_id] = {
                    'mentor': mentor,
                    'total_revenue': Decimal('0'),
                    'mentor_payment': Decimal('0'),
                    'director_share': Decimal('0'),
                    'groups': {},
                    'all_students': set(),
                }
            
            mentor_info = mentor_data[mentor_id]
            mentor_info['total_revenue'] += invoice.amount
            
            # Get unique students count for this group in this month
            group_students_count = invoices.filter(
                group=group,
                student__isnull=False
            ).values('student').distinct().count()
            
            # Calculate payment split for this invoice
            director_share, mentor_payment = self.calculate_payment_split(
                invoice.amount,
                group_students_count
            )
            
            mentor_info['mentor_payment'] += mentor_payment
            mentor_info['director_share'] += director_share
            mentor_info['all_students'].add(invoice.student.id)
            
            # Group-level details
            if group.id not in mentor_info['groups']:
                mentor_info['groups'][group.id] = {
                    'group': group,
                    'total_revenue': Decimal('0'),
                    'mentor_payment': Decimal('0'),
                    'director_share': Decimal('0'),
                    'students': set(),
                }
            
            group_info = mentor_info['groups'][group.id]
            group_info['total_revenue'] += invoice.amount
            group_info['mentor_payment'] += mentor_payment
            group_info['director_share'] += director_share
            group_info['students'].add(invoice.student.id)
        
        # Format the data
        result = []
        for mentor_id, data in mentor_data.items():
            groups_detail = []
            for group_id, group_data in data['groups'].items():
                group = group_data['group']
                # Get speciality and dates display (same logic as Group.__str__)
                speciality_map = {
                    'revit_architecture': 'Revit Architecture',
                    'revit_structure': 'Revit Structure',
                    'tekla_structure': 'Tekla Structure',
                }
                dates_map = {
                    'mon_wed_fri': 'Dushanba - Chorshanba - Juma',
                    'tue_thu_sat': 'Seshanba - Payshanba - Shanba',
                }
                speciality_display = speciality_map.get(group.speciality_id, group.speciality_id)
                dates_display = dates_map.get(group.dates, group.dates)
                
                groups_detail.append({
                    'group_id': group.id,
                    'group_name': str(group),
                    'speciality_display': speciality_display,
                    'dates_display': dates_display,
                    'time': str(group.time),
                    'starting_date': group.starting_date.isoformat() if group.starting_date else None,
                    'total_revenue': float(group_data['total_revenue']),
                    'mentor_payment': float(group_data['mentor_payment']),
                    'director_share': float(group_data['director_share']),
                    'students_count': len(group_data['students']),
                })
            
            result.append({
                'mentor_id': mentor.id,
                'mentor_name': mentor.full_name,
                'mentor_email': mentor.user.email if hasattr(mentor, 'user') and mentor.user else '',
                'total_revenue': float(data['total_revenue']),
                'mentor_payment': float(data['mentor_payment']),
                'director_share': float(data['director_share']),
                'groups_count': len(data['groups']),
                'students_count': len(data['all_students']),
                'groups_detail': sorted(groups_detail, key=lambda x: x['total_revenue'], reverse=True),
            })
        
        return sorted(result, key=lambda x: x['total_revenue'], reverse=True)

    @swagger_auto_schema(
        operation_description="Get monthly financial reports",
        operation_summary="Get Monthly Reports",
        manual_parameters=[
            openapi.Parameter(
                'month',
                openapi.IN_QUERY,
                description='Month in YYYY-MM format (e.g., 2025-01)',
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response('Monthly report data', MonthlyReportSerializer),
            400: openapi.Response('Invalid month format'),
        },
        tags=['Reports']
    )
    def get(self, request):
        # Check permissions first
        try:
            self.check_permissions(request)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        month_str = request.query_params.get('month')
        if not month_str:
            return Response(
                {'error': 'month parameter is required (YYYY-MM format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year, month = map(int, month_str.split('-'))
            if month < 1 or month > 12:
                raise ValueError
        except (ValueError, AttributeError):
            return Response(
                {'error': 'Invalid month format. Use YYYY-MM format (e.g., 2025-01)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get mentor earnings
            mentor_earnings = self.get_monthly_mentor_earnings(year, month)
            
            # Calculate totals
            total_revenue = sum(m['total_revenue'] for m in mentor_earnings)
            total_mentor_payments = sum(m['mentor_payment'] for m in mentor_earnings)
            total_director_share = sum(m['director_share'] for m in mentor_earnings)
            
            # Get employee salaries for this month
            employee_salaries = EmployeeSalary.objects.filter(month=month_str).select_related('employee')
            total_employee_salaries = employee_salaries.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # Convert to Decimal for proper calculation
            director_remaining = max(Decimal('0'), Decimal(str(total_director_share)) - total_employee_salaries)
            
            # Get non-mentor employees
            non_mentor_employees = Employee.objects.exclude(role='mentor').select_related('user')
            
            # Pre-fetch salaries for all employees to avoid N+1 queries
            salary_map = {}
            salary_paid_map = {}
            for salary in employee_salaries:
                emp_id = salary.employee.id
                if emp_id not in salary_map:
                    salary_map[emp_id] = Decimal('0')
                salary_map[emp_id] += salary.amount
                salary_paid_map[emp_id] = {
                    'is_paid': salary.is_paid,
                    'payment_date': salary.payment_date.isoformat() if salary.payment_date else None,
                }
            
            # Get mentor payment statuses
            mentor_payments = MentorPayment.objects.filter(month=month_str).select_related('mentor')
            mentor_paid_map = {}
            for mp in mentor_payments:
                mentor_paid_map[mp.mentor.id] = {
                    'is_paid': mp.is_paid,
                    'payment_date': mp.payment_date.isoformat() if mp.payment_date else None,
                }
            
            # Add payment status to mentor earnings
            for mentor_earning in mentor_earnings:
                mentor_id = mentor_earning.get('mentor_id')
                if mentor_id and mentor_id in mentor_paid_map:
                    mentor_earning['is_paid'] = mentor_paid_map[mentor_id]['is_paid']
                    mentor_earning['payment_date'] = mentor_paid_map[mentor_id]['payment_date']
                else:
                    mentor_earning['is_paid'] = False
                    mentor_earning['payment_date'] = None
            
            response_data = {
                'month': month_str,
                'total_revenue': float(total_revenue),
                'total_mentor_payments': float(total_mentor_payments),
                'total_director_share': float(total_director_share),
                'total_employee_salaries': float(total_employee_salaries),
                'director_remaining': float(director_remaining),
                'mentor_earnings': mentor_earnings,
                'employees': [
                    {
                        'id': emp.id,
                        'full_name': emp.full_name,
                        'email': getattr(emp.user, 'email', '') if hasattr(emp, 'user') and emp.user else '',
                        'role': emp.role,
                        'role_display': emp.get_role_display(),
                        'salary': float(salary_map.get(emp.id, Decimal('0'))),
                        'is_paid': salary_paid_map.get(emp.id, {}).get('is_paid', False),
                        'payment_date': salary_paid_map.get(emp.id, {}).get('payment_date'),
                    }
                    for emp in non_mentor_employees
                ],
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in getMonthlyReports: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmployeeSalaryView(generics.CreateAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    """
    Create, update, or delete employee salary.
    Only Director and Buxgalter can manage salaries.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeSalarySerializer

    def get_queryset(self):
        month = self.request.query_params.get('month') or self.request.data.get('month')
        if month:
            return EmployeeSalary.objects.filter(month=month).select_related('employee')
        return EmployeeSalary.objects.all().select_related('employee')

    def check_permissions(self, request):
        """Only Director and Buxgalter can manage salaries"""
        super().check_permissions(request)
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only employees can manage salaries")
        if request.user.employee_profile.role not in ['direktor', 'buxgalter']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to manage salaries")

    @swagger_auto_schema(
        operation_description="Create or update employee salary for a month",
        operation_summary="Set Employee Salary",
        request_body=EmployeeSalarySerializer,
        responses={
            200: openapi.Response('Salary created/updated', EmployeeSalarySerializer),
            400: openapi.Response('Validation error'),
            403: openapi.Response('Permission denied'),
        },
        tags=['Reports']
    )
    def post(self, request):
        # Check permissions first
        self.check_permissions(request)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        employee_id = serializer.validated_data['employee_id']
        month = serializer.validated_data['month']
        amount = serializer.validated_data['amount']
        notes = serializer.validated_data.get('notes', '')
        
        # Get or create salary
        salary, created = EmployeeSalary.objects.get_or_create(
            employee_id=employee_id,
            month=month,
            defaults={'amount': amount, 'notes': notes}
        )
        
        if not created:
            salary.amount = amount
            salary.notes = notes
            salary.save()
        
        # Return response with salary data
        response_data = {
            'id': salary.id,
            'employee_id': salary.employee.id,
            'employee_name': salary.employee.full_name,
            'month': salary.month,
            'amount': float(salary.amount),
            'notes': salary.notes or '',
        }
        
        return Response(
            response_data,
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED
        )


class MarkSalaryAsPaidView(generics.GenericAPIView):
    """
    Mark employee salary as paid.
    Only Director and Buxgalter can mark salaries as paid.
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        """Only Director and Buxgalter can mark salaries as paid"""
        super().check_permissions(request)
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only employees can mark salaries as paid")
        if request.user.employee_profile.role not in ['direktor', 'buxgalter']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to mark salaries as paid")

    @swagger_auto_schema(
        operation_description="Mark employee salary as paid",
        operation_summary="Mark Salary as Paid",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'employee_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'month': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'is_paid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=['employee_id', 'month', 'is_paid']
        ),
        responses={
            200: openapi.Response('Salary marked as paid'),
            400: openapi.Response('Validation error'),
            403: openapi.Response('Permission denied'),
        },
        tags=['Reports']
    )
    def post(self, request):
        self.check_permissions(request)
        
        employee_id = request.data.get('employee_id')
        month = request.data.get('month')
        is_paid = request.data.get('is_paid', True)
        
        if not employee_id or not month:
            return Response(
                {'error': 'employee_id and month are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            salary = EmployeeSalary.objects.get(employee_id=employee_id, month=month)
            salary.is_paid = is_paid
            if is_paid and not salary.payment_date:
                salary.payment_date = timezone.now()
            elif not is_paid:
                salary.payment_date = None
            salary.save()
            
            return Response({
                'success': True,
                'message': 'Salary marked as paid successfully',
                'data': {
                    'employee_id': salary.employee.id,
                    'month': salary.month,
                    'is_paid': salary.is_paid,
                    'payment_date': salary.payment_date.isoformat() if salary.payment_date else None,
                }
            }, status=status.HTTP_200_OK)
        except EmployeeSalary.DoesNotExist:
            return Response(
                {'error': 'Salary not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error marking salary as paid: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkMentorPaymentAsPaidView(generics.GenericAPIView):
    """
    Mark mentor payment as paid.
    Only Director and Buxgalter can mark mentor payments as paid.
    """
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request):
        """Only Director and Buxgalter can mark mentor payments as paid"""
        super().check_permissions(request)
        if not hasattr(request.user, 'employee_profile'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only employees can mark mentor payments as paid")
        if request.user.employee_profile.role not in ['direktor', 'buxgalter']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to mark mentor payments as paid")

    @swagger_auto_schema(
        operation_description="Mark mentor payment as paid",
        operation_summary="Mark Mentor Payment as Paid",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mentor_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'month': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'is_paid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=['mentor_id', 'month', 'amount', 'is_paid']
        ),
        responses={
            200: openapi.Response('Mentor payment marked as paid'),
            400: openapi.Response('Validation error'),
            403: openapi.Response('Permission denied'),
        },
        tags=['Reports']
    )
    def post(self, request):
        self.check_permissions(request)
        
        mentor_id = request.data.get('mentor_id')
        month = request.data.get('month')
        amount = request.data.get('amount')
        is_paid = request.data.get('is_paid', True)
        
        if not mentor_id or not month or amount is None:
            return Response(
                {'error': 'mentor_id, month, and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            mentor = Employee.objects.get(id=mentor_id, role='mentor')
            
            mentor_payment, created = MentorPayment.objects.get_or_create(
                mentor=mentor,
                month=month,
                defaults={'amount': Decimal(str(amount))}
            )
            
            if not created:
                mentor_payment.amount = Decimal(str(amount))
            
            mentor_payment.is_paid = is_paid
            if is_paid and not mentor_payment.payment_date:
                mentor_payment.payment_date = timezone.now()
            elif not is_paid:
                mentor_payment.payment_date = None
            mentor_payment.save()
            
            return Response({
                'success': True,
                'message': 'Mentor payment marked as paid successfully',
                'data': {
                    'mentor_id': mentor_payment.mentor.id,
                    'month': mentor_payment.month,
                    'amount': float(mentor_payment.amount),
                    'is_paid': mentor_payment.is_paid,
                    'payment_date': mentor_payment.payment_date.isoformat() if mentor_payment.payment_date else None,
                }
            }, status=status.HTTP_200_OK)
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Mentor not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error marking mentor payment as paid: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
