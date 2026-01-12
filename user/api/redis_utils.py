import json
from datetime import timedelta
from typing import Optional
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def get_verification_code_key(student_id: int) -> str:
    """Get Redis key for student verification code"""
    return f'verification_code:student:{student_id}'


def store_verification_code(student_id: int, code: str, expiry_minutes: Optional[int] = None) -> bool:
    """
    Store verification code in Redis with expiration
    
    Args:
        student_id: Student ID
        code: 6-digit verification code
        expiry_minutes: Expiration time in minutes (defaults to VERIFICATION_CODE_EXPIRY_MINUTES)
    
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        if expiry_minutes is None:
            expiry_minutes = getattr(settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 2)
        
        # Type narrowing: after None check, expiry_minutes is guaranteed to be int
        assert expiry_minutes is not None, "expiry_minutes should not be None after check"
        expiry_minutes_int = expiry_minutes
        
        key = get_verification_code_key(student_id)
        expiry_seconds = expiry_minutes_int * 60
        
        # Store code with metadata
        data = {
            'code': code,
            'student_id': student_id,
            'created_at': timezone.now().isoformat(),
            'expires_at': (timezone.now() + timedelta(minutes=expiry_minutes_int)).isoformat()
        }
        
        cache.set(key, json.dumps(data), timeout=expiry_seconds)
        logger.info(f"Stored verification code for student {student_id}, expires in {expiry_minutes_int} minutes")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store verification code in Redis: {str(e)}")
        return False


def get_verification_code(student_id: int) -> Optional[dict]:
    """
    Get verification code from Redis
    
    Args:
        student_id: Student ID
    
    Returns:
        Dict with 'code', 'student_id', 'created_at', 'expires_at' or None if not found/expired
    """
    try:
        key = get_verification_code_key(student_id)
        cached_data = cache.get(key)
        
        if cached_data is None:
            return None
        
        data = json.loads(cached_data)
        
        # Check if expired (double check)
        expires_at_str = data['expires_at']
        # Handle timezone-aware datetime strings
        if expires_at_str.endswith('Z'):
            expires_at_str = expires_at_str.replace('Z', '+00:00')
        expires_at = timezone.datetime.fromisoformat(expires_at_str)
        if expires_at < timezone.now():
            # Already expired, delete it
            cache.delete(key)
            return None
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to get verification code from Redis: {str(e)}")
        return None


def verify_code(student_id: int, code: str) -> bool:
    """
    Verify code and delete it if correct
    
    Args:
        student_id: Student ID
        code: Code to verify
    
    Returns:
        True if code matches and not expired, False otherwise
    """
    try:
        stored_data = get_verification_code(student_id)
        
        if stored_data is None:
            logger.warning(f"No verification code found for student {student_id}")
            return False
        
        if stored_data['code'] != code:
            logger.warning(f"Invalid verification code for student {student_id}")
            return False
        
        # Code is valid, delete it (one-time use)
        key = get_verification_code_key(student_id)
        cache.delete(key)
        logger.info(f"Verification code verified and deleted for student {student_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify code: {str(e)}")
        return False


def delete_verification_code(student_id: int) -> bool:
    """
    Delete verification code from Redis
    
    Args:
        student_id: Student ID
    
    Returns:
        True if deleted, False otherwise
    """
    try:
        key = get_verification_code_key(student_id)
        cache.delete(key)
        logger.info(f"Deleted verification code for student {student_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete verification code: {str(e)}")
        return False
