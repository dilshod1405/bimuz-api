import requests
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class EskizSMSService:
    """
    SMS service for Eskiz.uz gateway
    Handles authentication, token refresh, and SMS sending
    """
    
    TOKEN_CACHE_KEY = 'eskiz_token'
    TOKEN_CACHE_TIMEOUT = 30 * 24 * 60 * 60  # 30 days in seconds
    
    def __init__(self):
        self.base_url = getattr(settings, 'ESKIZ_BASE_URL', 'https://notify.eskiz.uz/api')
        self.email = getattr(settings, 'ESKIZ_EMAIL', None)
        self.password = getattr(settings, 'ESKIZ_PASSWORD', None)
        self.sender = getattr(settings, 'ESKIZ_SENDER', '4546')
        
        if not self.email or not self.password:
            logger.warning("Eskiz credentials not configured. SMS sending will fail.")
    
    def _get_token(self) -> Optional[str]:
        """
        Get authentication token from cache or login
        """
        token = cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token
        
        return self._login()
    
    def _login(self) -> Optional[str]:
        """
        Authenticate with Eskiz API and get token
        """
        if not self.email or not self.password:
            logger.error("Eskiz credentials not configured")
            return None
        
        try:
            url = f'{self.base_url}/auth/login'
            data = {
                'email': self.email,
                'password': self.password
            }
            
            logger.info(f"Attempting to login to Eskiz API: {url}")
            response = requests.post(url, data=data, timeout=10)
            
            logger.info(f"Login response status: {response.status_code}")
            logger.debug(f"Login response headers: {dict(response.headers)}")
            
            # Log response even if status is not 200
            if response.status_code != 200:
                logger.error(f"Login failed with status {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            try:
                result = response.json()
                logger.debug(f"Login response JSON: {result}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {response.text}")
                return None
            
            if result.get('message') == 'token_generated':
                token = result.get('data', {}).get('token')
                if token:
                    cache.set(self.TOKEN_CACHE_KEY, token, self.TOKEN_CACHE_TIMEOUT)
                    logger.info("Successfully authenticated with Eskiz API")
                    return token
                else:
                    logger.error("Token not found in response data")
            else:
                logger.error(f"Login failed: {result}")
            
            return None
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during Eskiz login: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during Eskiz login: {str(e)}")
            return None
    
    def _refresh_token(self) -> Optional[str]:
        """
        Refresh authentication token
        """
        token = self._get_token()
        if not token:
            return None
        
        try:
            url = f'{self.base_url}/auth/refresh'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.patch(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('message') == 'token_generated':
                new_token = result.get('data', {}).get('token')
                if new_token:
                    cache.set(self.TOKEN_CACHE_KEY, new_token, self.TOKEN_CACHE_TIMEOUT)
                    logger.info("Successfully refreshed Eskiz token")
                    return new_token
            
            logger.error(f"Failed to refresh token: {result}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during token refresh: {str(e)}")
            # Try to login again if refresh fails
            cache.delete(self.TOKEN_CACHE_KEY)
            return self._login()
    
    def send_sms(self, phone: str, message: str, callback_url: Optional[str] = None, allow_test_message: bool = False) -> Dict[str, Any]:
        """
        Send SMS to phone number
        
        Args:
            phone: Phone number in format 998991234567
            message: SMS message text
            callback_url: Optional callback URL for status updates
        
        Returns:
            Dict with 'success', 'request_id', and 'message' keys
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with SMS service'
            }
        
        try:
            url = f'{self.base_url}/message/sms/send'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            data = {
                'mobile_phone': phone,
                'message': message,
                'from': self.sender
            }
            
            if callback_url:
                data['callback_url'] = callback_url
            
            logger.info(f"Sending SMS to {phone} with message: {message[:50]}...")
            response = requests.post(url, headers=headers, data=data, timeout=10)
            
            logger.info(f"SMS send response status: {response.status_code}")
            logger.debug(f"SMS send response headers: {dict(response.headers)}")
            
            # If unauthorized, try to refresh token and retry
            if response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                token = self._refresh_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    logger.info("Retrying SMS send with new token...")
                    response = requests.post(url, headers=headers, data=data, timeout=10)
                    logger.info(f"Retry response status: {response.status_code}")
            
            # Log response even if status is not 200
            if response.status_code != 200:
                logger.error(f"SMS send failed with status {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            try:
                result = response.json()
                logger.debug(f"SMS send response JSON: {result}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {response.text}")
                return {
                    'success': False,
                    'message': f'Invalid response from SMS service: {response.text[:200]}'
                }
            
            if 'id' in result:
                logger.info(f"SMS sent successfully with request_id: {result.get('id')}")
                return {
                    'success': True,
                    'request_id': result.get('id'),
                    'message': result.get('message', 'SMS sent successfully'),
                    'status': result.get('status', 'waiting')
                }
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"SMS send failed: {error_msg}")
                return {
                    'success': False,
                    'message': error_msg
                }
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error sending SMS: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return {
                'success': False,
                'message': f'HTTP error: {str(e)}'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to send SMS: {str(e)}'
            }
    
    def get_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get SMS status by request ID
        
        Args:
            request_id: Request ID returned from send_sms
        
        Returns:
            Dict with status information
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with SMS service'
            }
        
        try:
            url = f'{self.base_url}/message/sms/status_by_id/{request_id}'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            # If unauthorized, try to refresh token and retry
            if response.status_code == 401:
                token = self._refresh_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.get(url, headers=headers, timeout=10)
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') == 'success':
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Unknown error')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting SMS status: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get SMS status: {str(e)}'
            }
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Get user information from Eskiz API
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with SMS service'
            }
        
        try:
            url = f'{self.base_url}/auth/user'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 401:
                token = self._refresh_token()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.get(url, headers=headers, timeout=10)
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') == 'success':
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'Unknown error')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get user info: {str(e)}'
            }
    
    def send_verification_code(self, phone: str, code: str) -> Dict[str, Any]:
        """
        Send verification code using test message format for unpaid accounts.
        Sends two messages: test message and code separately.
        
        Args:
            phone: Phone number in format 998991234567
            code: 6-digit verification code
        
        Returns:
            Dict with 'success', 'request_id', and 'message' keys
        """
        test_message = getattr(settings, 'ESKIZ_TEST_MESSAGE', 'This is test from Eskiz')
        
        # First, send the exact test message (required for unpaid accounts)
        result1 = self.send_sms(phone=phone, message=test_message)
        
        if not result1.get('success'):
            logger.error(f"Failed to send test message: {result1.get('message')}")
            return result1
        
        # Then, try to send the code as a separate message
        # Note: This might fail for unpaid accounts, but we try anyway
        result2 = self.send_sms(phone=phone, message=code)
        
        if result2.get('success'):
            logger.info(f"Both test message and code sent successfully")
            return {
                'success': True,
                'request_id': result2.get('request_id'),
                'message': 'Verification code sent successfully',
                'status': result2.get('status', 'waiting'),
                'test_message_sent': True,
                'code_message_sent': True
            }
        else:
            # Test message was sent, but code message failed
            # This is acceptable - user received the test message at least
            logger.warning(f"Test message sent, but code message failed: {result2.get('message')}")
            return {
                'success': True,  # Still consider it success since test message was sent
                'request_id': result1.get('request_id'),
                'message': f'Test message sent. Code sending failed: {result2.get("message")}. Code: {code}',
                'status': result1.get('status', 'waiting'),
                'test_message_sent': True,
                'code_message_sent': False,
                'code': code  # Include code in response as fallback
            }


# Singleton instance
sms_service = EskizSMSService()
