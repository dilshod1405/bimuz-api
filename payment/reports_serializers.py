"""
Serializers for reports API.
"""
from rest_framework import serializers
from decimal import Decimal

from payment.models import EmployeeSalary
from user.models import Employee


class EmployeeSalarySerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    month = serializers.CharField(max_length=7, help_text="Month in YYYY-MM format")
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_month(self, value):
        """Validate month format"""
        try:
            year, month = map(int, value.split('-'))
            if month < 1 or month > 12:
                raise serializers.ValidationError("Invalid month. Must be between 1-12")
            return value
        except (ValueError, AttributeError):
            raise serializers.ValidationError("Invalid month format. Use YYYY-MM format (e.g., 2025-01)")

    def validate_employee_id(self, value):
        """Validate employee exists and is not a mentor"""
        try:
            employee = Employee.objects.get(id=value)
            if employee.role == 'mentor':
                raise serializers.ValidationError("Cannot set salary for mentors. They are paid based on student payments.")
            return value
        except Employee.DoesNotExist:
            raise serializers.ValidationError("Employee not found")


class MentorEarningsSerializer(serializers.Serializer):
    mentor_id = serializers.IntegerField()
    mentor_name = serializers.CharField()
    mentor_email = serializers.EmailField()
    total_revenue = serializers.FloatField()
    mentor_payment = serializers.FloatField()
    director_share = serializers.FloatField()
    groups_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    groups_detail = serializers.ListField()


class FinancialSummarySerializer(serializers.Serializer):
    total_revenue = serializers.FloatField()
    total_mentor_payments = serializers.FloatField()
    total_director_share = serializers.FloatField()
    total_employee_salaries = serializers.FloatField()
    director_remaining = serializers.FloatField()


class MonthlyReportSerializer(serializers.Serializer):
    month = serializers.CharField()
    total_revenue = serializers.FloatField()
    total_mentor_payments = serializers.FloatField()
    total_director_share = serializers.FloatField()
    total_employee_salaries = serializers.FloatField()
    director_remaining = serializers.FloatField()
    mentor_earnings = MentorEarningsSerializer(many=True)
    employees = serializers.ListField()
