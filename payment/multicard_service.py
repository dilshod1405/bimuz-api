import requests
import logging
import hashlib
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class MulticardPaymentService:
    """
    Payment service for Multicard payment gateway.
    Handles authentication, invoice creation, and status checking.
    """

    TOKEN_CACHE_KEY = 'multicard_token'
    TOKEN_CACHE_TIMEOUT = 24 * 60 * 60  # 24 hours in seconds

    def __init__(self):
        self.base_url = getattr(settings, 'MULTICARD_BASE_URL', 'https://dev-mesh.multicard.uz')
        self.application_id = getattr(settings, 'MULTICARD_APPLICATION_ID', None)
        self.secret = getattr(settings, 'MULTICARD_SECRET', None)
        self.store_id = getattr(settings, 'MULTICARD_STORE_ID', None)
        self.callback_url = getattr(settings, 'MULTICARD_CALLBACK_URL', None)

        if not self.application_id or not self.secret:
            logger.warning("Multicard credentials not configured. Payment operations will fail.")

    def _get_token(self) -> Optional[str]:
        """
        Get authentication token from cache or login.
        """
        token = cache.get(self.TOKEN_CACHE_KEY)
        if token:
            return token

        return self._login()

    def _login(self) -> Optional[str]:
        """
        Authenticate with Multicard API and get token.
        """
        if not self.application_id or not self.secret:
            logger.error("Multicard credentials not configured")
            return None

        try:
            url = f'{self.base_url}/auth'
            data = {
                'application_id': self.application_id,
                'secret': self.secret
            }

            logger.info(f"Attempting Multicard login to {url}")
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Multicard login response status: {response.status_code}")
            logger.debug(f"Multicard login response JSON: {result}")

            if result.get('token'):
                token = result.get('token')
                expiry = result.get('expiry', '24 hours')
                # Cache token (use expiry if provided, otherwise default)
                cache.set(self.TOKEN_CACHE_KEY, token, self.TOKEN_CACHE_TIMEOUT)
                logger.info("Successfully authenticated with Multicard API")
                return token

            logger.error(f"Failed to get token: {result}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error during Multicard login: {str(e)}", exc_info=True)
            return None

    def create_invoice(
        self,
        invoice_id: str,
        amount: int,
        lang: str = 'uz',
        return_url: Optional[str] = None,
        return_error_url: Optional[str] = None,
        callback_url: Optional[str] = None,
        sms: Optional[str] = None,
        ofd: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Create invoice in Multicard payment system.

        Args:
            invoice_id: Unique invoice ID in our system
            amount: Amount in tiyins (1 sum = 100 tiyins)
            lang: Language (ru, uz, en)
            return_url: URL to redirect after payment
            return_error_url: URL to redirect after error
            callback_url: URL for payment callback
            sms: Phone number to send invoice link (format: 998XXXXXXXXX)
            ofd: OFD data for fiscal receipt

        Returns:
            Dict with 'success', 'data' keys
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with payment service'
            }

        if not self.store_id:
            return {
                'success': False,
                'message': 'Store ID not configured'
            }

        try:
            url = f'{self.base_url}/payment/invoice'
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            # Use provided callback_url or default from settings
            final_callback_url = callback_url or self.callback_url
            if not final_callback_url:
                return {
                    'success': False,
                    'message': 'Callback URL not configured'
                }

            data = {
                'store_id': self.store_id,
                'amount': amount,
                'invoice_id': invoice_id,
                'lang': lang,
                'callback_url': final_callback_url,
            }

            if return_url:
                data['return_url'] = return_url
            if return_error_url:
                data['return_error_url'] = return_error_url
            if sms:
                data['sms'] = sms
            if ofd:
                data['ofd'] = ofd

            logger.info(f"Creating invoice in Multicard: invoice_id={invoice_id}, amount={amount}")
            response = requests.post(url, headers=headers, json=data, timeout=30)

            logger.info(f"Invoice creation response status: {response.status_code}")
            logger.debug(f"Invoice creation response text: {response.text}")

            # If unauthorized, try to login again and retry
            if response.status_code == 401:
                logger.warning("Token expired, re-authenticating...")
                cache.delete(self.TOKEN_CACHE_KEY)
                token = self._login()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    logger.info(f"Invoice creation retry response status: {response.status_code}")
                else:
                    return {
                        'success': False,
                        'message': 'Failed to refresh token for payment service'
                    }

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                error = result.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', 'Unknown error'),
                    'error_code': error.get('code')
                }

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error creating invoice: {e}", exc_info=True)
            try:
                error_data = e.response.json()
                error = error_data.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', f'HTTP error: {e}'),
                    'error_code': error.get('code')
                }
            except:
                return {
                    'success': False,
                    'message': f'HTTP error: {e}. Status: {e.response.status_code}'
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to create invoice: {str(e)}'
            }

    def get_invoice_status(self, uuid: str) -> Dict[str, Any]:
        """
        Get invoice status from Multicard by UUID.

        Args:
            uuid: Multicard transaction UUID

        Returns:
            Dict with 'success', 'data' keys
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with payment service'
            }

        try:
            url = f'{self.base_url}/payment/invoice/{uuid}'
            headers = {
                'Authorization': f'Bearer {token}'
            }

            logger.info(f"Getting invoice status for UUID: {uuid}")
            response = requests.get(url, headers=headers, timeout=10)

            # If unauthorized, try to login again and retry
            if response.status_code == 401:
                logger.warning("Token expired, re-authenticating...")
                cache.delete(self.TOKEN_CACHE_KEY)
                token = self._login()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.get(url, headers=headers, timeout=10)
                else:
                    return {
                        'success': False,
                        'message': 'Failed to refresh token for payment service'
                    }

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                error = result.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', 'Unknown error'),
                    'error_code': error.get('code')
                }

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error getting invoice status: {e}", exc_info=True)
            try:
                error_data = e.response.json()
                error = error_data.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', f'HTTP error: {e}'),
                    'error_code': error.get('code')
                }
            except:
                return {
                    'success': False,
                    'message': f'HTTP error: {e}. Status: {e.response.status_code}'
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting invoice status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to get invoice status: {str(e)}'
            }

    def cancel_invoice(self, uuid: str) -> Dict[str, Any]:
        """
        Cancel (annul) invoice in Multicard.

        Args:
            uuid: Multicard transaction UUID

        Returns:
            Dict with 'success', 'message' keys
        """
        token = self._get_token()
        if not token:
            return {
                'success': False,
                'message': 'Failed to authenticate with payment service'
            }

        try:
            url = f'{self.base_url}/payment/invoice/{uuid}'
            headers = {
                'Authorization': f'Bearer {token}'
            }

            logger.info(f"Cancelling invoice with UUID: {uuid}")
            response = requests.delete(url, headers=headers, timeout=10)

            # If unauthorized, try to login again and retry
            if response.status_code == 401:
                logger.warning("Token expired, re-authenticating...")
                cache.delete(self.TOKEN_CACHE_KEY)
                token = self._login()
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.delete(url, headers=headers, timeout=10)
                else:
                    return {
                        'success': False,
                        'message': 'Failed to refresh token for payment service'
                    }

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return {
                    'success': True,
                    'message': 'Invoice cancelled successfully'
                }
            else:
                error = result.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', 'Unknown error'),
                    'error_code': error.get('code')
                }

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error cancelling invoice: {e}", exc_info=True)
            try:
                error_data = e.response.json()
                error = error_data.get('error', {})
                return {
                    'success': False,
                    'message': error.get('details', f'HTTP error: {e}'),
                    'error_code': error.get('code')
                }
            except:
                return {
                    'success': False,
                    'message': f'HTTP error: {e}. Status: {e.response.status_code}'
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error cancelling invoice: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Failed to cancel invoice: {str(e)}'
            }

    @staticmethod
    def verify_callback_signature(
        store_id: int,
        invoice_id: str,
        amount: int,
        secret: str,
        sign: str
    ) -> bool:
        """
        Verify callback signature from Multicard.

        Args:
            store_id: Store ID
            invoice_id: Invoice ID
            amount: Amount in tiyins
            secret: Secret key
            sign: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        # MD5 hash: {store_id}{invoice_id}{amount}{secret}
        sign_string = f"{store_id}{invoice_id}{amount}{secret}"
        expected_sign = hashlib.md5(sign_string.encode()).hexdigest()
        return expected_sign.lower() == sign.lower()

    @staticmethod
    def verify_webhook_signature(
        uuid: str,
        invoice_id: str,
        amount: int,
        secret: str,
        sign: str
    ) -> bool:
        """
        Verify webhook signature from Multicard.

        Args:
            uuid: Transaction UUID
            invoice_id: Invoice ID
            amount: Amount in tiyins
            secret: Secret key
            sign: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        # SHA1 hash: {uuid}{invoice_id}{amount}{secret}
        sign_string = f"{uuid}{invoice_id}{amount}{secret}"
        expected_sign = hashlib.sha1(sign_string.encode()).hexdigest()
        return expected_sign.lower() == sign.lower()


# Singleton instance
multicard_service = MulticardPaymentService()
