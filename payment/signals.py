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
    Create first installment invoice automatically when student books a group.
    First installment is 50% of the group price.
    Second installment will be created when first is paid or when needed.
    Triggered when student.group is set.
    """
    # Only process if group is set
    if not instance.group:
        return
    
    # Check if invoices already exist for this student-group combination
    existing_invoices = Invoice.objects.filter(
        student=instance,
        group=instance.group,
        status__in=[InvoiceStatus.CREATED, InvoiceStatus.PENDING, InvoiceStatus.PAID]
    )
    
    if existing_invoices.exists():
        logger.info(f"Invoices already exist for student {instance.id} and group {instance.group.id}")
        return
    
    # Get the group price
    group_price = instance.group.price
    
    if group_price <= 0:
        logger.warning(f"Group {instance.group.id} has no price set. Invoice not created.")
        return
    
    try:
        with transaction.atomic():
            # Calculate first installment amount (50% of total)
            total = float(group_price)
            first_installment_amount = total / 2
            
            # Create first installment invoice
            invoice = Invoice.objects.create(
                student=instance,
                group=instance.group,
                amount=first_installment_amount,
                status=InvoiceStatus.CREATED,
                notes=f"Birinchi to'lov (50%) guruh {instance.group.id} uchun. Jami guruh narxi: {group_price} so'm."
            )
            
            logger.info(
                f"Created first installment invoice {invoice.id} for student {instance.id} and group {instance.group.id}: "
                f"{first_installment_amount} UZS (50% of {group_price} UZS)."
            )
    except Exception as e:
        logger.error(f"Failed to create invoice for student {instance.id} and group {instance.group.id}: {str(e)}")


@receiver(pre_save, sender=Group)
def update_invoice_amount_on_price_change(sender, instance: Group, **kwargs):
    """
    Update invoice amounts when group price changes.
    Only updates invoices that are not paid (created or pending status).
    Updates first installment invoices proportionally (50% of new price).
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
                # Calculate new first installment amount (50% of new price)
                new_first_installment = float(new_price) / 2
                
                # Update invoice amount
                if invoice.update_amount(new_first_installment):
                    updated_count += 1
                    logger.info(
                        f"Updated invoice {invoice.id} amount from {old_price/2} to {new_first_installment} "
                        f"for group {instance.id} (price changed from {old_price} to {new_price})"
                    )
            
            if updated_count > 0:
                logger.info(f"Updated {updated_count} invoice(s) for group {instance.id} due to price change")
    except Group.DoesNotExist:
        # Group doesn't exist yet, skip
        pass
    except Exception as e:
        logger.error(f"Failed to update invoice amounts for group {instance.id}: {str(e)}")
