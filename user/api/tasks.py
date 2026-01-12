from celery import shared_task
import logging
from user.api.sms_service import sms_service
from user.api.redis_utils import store_verification_code, get_verification_code_key
from user.api.utils import generate_verification_code, get_verification_code_expiry
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_verification_code_sms(self, student_id: int, phone: str, code: str):
    """
    Celery task to send verification code via SMS
    
    Args:
        student_id: Student ID
        phone: Phone number (normalized)
        code: Verification code to send
    
    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"Sending verification code SMS to student {student_id}, phone: {phone}")
        
        result = sms_service.send_verification_code(phone=phone, code=code)
        
        if result.get('success'):
            logger.info(f"Verification code SMS sent successfully for student {student_id}")
            return {
                'success': True,
                'student_id': student_id,
                'message': 'SMS sent successfully',
                'request_id': result.get('request_id')
            }
        else:
            error_msg = result.get('message', 'Unknown error')
            logger.error(f"Failed to send SMS for student {student_id}: {error_msg}")
            
            # Retry if it's a temporary error
            if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
                raise Exception(f"Temporary error: {error_msg}")
            
            return {
                'success': False,
                'student_id': student_id,
                'message': error_msg
            }
            
    except Exception as exc:
        logger.error(f"Exception in send_verification_code_sms for student {student_id}: {str(exc)}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def generate_and_send_verification_code(student_id: int, phone: str):
    """
    Generate verification code, store in Redis, and send via SMS
    
    Args:
        student_id: Student ID
        phone: Phone number (normalized)
    
    Returns:
        Dict with success status, code, and SMS result
    """
    try:
        # Generate code
        code = generate_verification_code()
        
        # Store in Redis
        expiry_minutes = getattr(settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 2)
        stored = store_verification_code(student_id, code, expiry_minutes)
        
        if not stored:
            logger.error(f"Failed to store verification code in Redis for student {student_id}")
            return {
                'success': False,
                'message': 'Failed to store verification code'
            }
        
        # Send SMS asynchronously
        send_verification_code_sms.delay(student_id, phone, code)
        
        logger.info(f"Verification code generated and queued for SMS for student {student_id}")
        
        return {
            'success': True,
            'code': code,  # For testing/debugging
            'expires_in_minutes': expiry_minutes
        }
        
    except Exception as e:
        logger.error(f"Exception in generate_and_send_verification_code for student {student_id}: {str(e)}")
        return {
            'success': False,
            'message': f'Failed to generate and send code: {str(e)}'
        }
