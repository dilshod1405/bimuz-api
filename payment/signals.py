from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
import logging

from user.models import Student
from education.models import Group
from payment.models import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Student)
def create_invoice_on_booking(sender, instance: Student, created: bool, **kwargs):
    """
    Create invoice automatically when student books a group.
    Triggered when student.group is set.
    """
    # Only process if group is set
    if not instance.group:
        return
    
    # Check if invoice already exists for this student-group combination
    existing_invoice = Invoice.objects.filter(
        student=instance,
        group=instance.group,
        status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING, InvoiceStatus.PAID]
    ).first()
    
    if existing_invoice:
        logger.info(f"Invoice already exists for student {instance.id} and group {instance.group.id}")
        return
    
    # Get the group price
    group_price = instance.group.price
    
    if group_price <= 0:
        logger.warning(f"Group {instance.group.id} has no price set. Invoice not created.")
        return
    
    try:
        with transaction.atomic():
            invoice = Invoice.objects.create(
                student=instance,
                group=instance.group,
                amount=group_price,
                status=InvoiceStatus.CREATED
            )
            logger.info(f"Created invoice {invoice.id} for student {instance.id} and group {instance.group.id} with amount {group_price}")
    except Exception as e:
        logger.error(f"Failed to create invoice for student {instance.id} and group {instance.group.id}: {str(e)}")


@receiver(pre_save, sender=Group)
def update_invoice_amount_on_price_change(sender, instance: Group, **kwargs):
    """
    Update invoice amounts when group price changes.
    Only updates invoices that are not paid (created or pending status).
    """
    if not instance.pk:
        # New group, no invoices to update
        return
    
    try:
        # Get the old price from database
        old_group = Group.objects.get(pk=instance.pk)
        old_price = old_group.price
        new_price = instance.price
        
        # Only update if price actually changed
        if old_price != new_price and new_price > 0:
            # Update all unpaid invoices for this group
            unpaid_invoices = Invoice.objects.filter(
                group=instance,
                status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING]
            )
            
            updated_count = 0
            for invoice in unpaid_invoices:
                if invoice.update_amount(new_price):
                    updated_count += 1
                    logger.info(f"Updated invoice {invoice.id} amount from {old_price} to {new_price} for group {instance.id}")
            
            if updated_count > 0:
                logger.info(f"Updated {updated_count} invoice(s) for group {instance.id} due to price change")
    except Group.DoesNotExist:
        # Group doesn't exist yet, skip
        pass
    except Exception as e:
        logger.error(f"Failed to update invoice amounts for group {instance.id}: {str(e)}")
