from django.urls import path
from payment import views
from payment.reports_views import (
    MonthlyReportsView, 
    EmployeeSalaryView,
    MarkSalaryAsPaidView,
    MarkMentorPaymentAsPaidView,
)

app_name = 'payment'

urlpatterns = [
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('create-payment/', views.CreatePaymentView.as_view(), name='create-payment'),
    path('callback/', views.payment_callback, name='payment-callback'),
    path('webhook/', views.payment_webhook, name='payment-webhook'),
    path('check-status/', views.CheckInvoiceStatusView.as_view(), name='check-status'),
    
    # Employee invoice management endpoints
    path('employee-invoices/', views.EmployeeInvoiceListView.as_view(), name='employee-invoice-list'),
    path('mark-as-paid/', views.MarkInvoicesAsPaidView.as_view(), name='mark-invoices-as-paid'),
    
    # Reports endpoints
    path('reports/monthly/', MonthlyReportsView.as_view(), name='monthly-reports'),
    path('reports/salary/', EmployeeSalaryView.as_view(), name='employee-salary'),
    path('reports/salary/mark-paid/', MarkSalaryAsPaidView.as_view(), name='mark-salary-as-paid'),
    path('reports/mentor-payment/mark-paid/', MarkMentorPaymentAsPaidView.as_view(), name='mark-mentor-payment-as-paid'),
]
