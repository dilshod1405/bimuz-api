from django.urls import path
from payment import views

app_name = 'payment'

urlpatterns = [
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('create-payment/', views.CreatePaymentView.as_view(), name='create-payment'),
    path('callback/', views.payment_callback, name='payment-callback'),
    path('webhook/', views.payment_webhook, name='payment-webhook'),
    path('check-status/', views.CheckInvoiceStatusView.as_view(), name='check-status'),
]
