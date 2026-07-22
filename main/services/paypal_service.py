# services/paypal_service.py - Update the execute_payment function

import paypalrestsdk
import logging
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from django.conf import settings
from django.urls import reverse
import time

logger = logging.getLogger(__name__)

# ============================================
# SSL FIX FOR PYTHON 3.13
# ============================================

class SSLAdapter(HTTPAdapter):
    """Custom adapter to handle SSL issues with Python 3.13"""
    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1_2
        kwargs['cert_reqs'] = ssl.CERT_NONE
        return super().init_poolmanager(*args, **kwargs)
    
    def proxy_manager_for(self, *args, **kwargs):
        kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1_2
        kwargs['cert_reqs'] = ssl.CERT_NONE
        return super().proxy_manager_for(*args, **kwargs)


def configure_paypal():
    """Configure PayPal SDK with credentials from settings"""
    try:
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
        receiver_email = getattr(settings, 'PAYPAL_RECEIVER_EMAIL', '')
        
        if not client_id or not client_secret:
            logger.error("❌ PayPal credentials missing!")
            return False
        
        # Configure PayPal SDK
        paypalrestsdk.configure({
            'mode': mode,
            'client_id': client_id,
            'client_secret': client_secret,
        })
        
        # FIX: Override requests session with custom SSL adapter and timeout
        if mode == 'sandbox':
            session = requests.Session()
            session.mount('https://', SSLAdapter())
            # Set longer timeout for sandbox
            session.timeout = 60
            paypalrestsdk.api.default.session = session
            logger.info("✅ SSL adapter configured for sandbox")
        
        logger.info(f"✅ PayPal configured in {mode} mode")
        logger.info(f"✅ Receiver: {receiver_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ PayPal configuration error: {e}")
        return False

# Configure immediately
PAYPAL_CONFIGURED = configure_paypal()


def create_payment(product, user, request):
    """Create a PayPal payment"""
    try:
        if not PAYPAL_CONFIGURED:
            logger.error("❌ PayPal not configured")
            return None
        
        receiver_email = getattr(settings, 'PAYPAL_RECEIVER_EMAIL', '')
        
        if not receiver_email:
            logger.error("❌ No receiver email configured!")
            return None
        
        return_url = request.build_absolute_uri(reverse('paypal_execute'))
        cancel_url = request.build_absolute_uri(reverse('paypal_cancel'))
        
        # Get product details
        product_name = getattr(product, 'name', 'Product')
        
        if hasattr(product, 'description') and product.description:
            product_description = product.description[:200]
        elif hasattr(product, 'plan_type'):
            product_description = f"{product_name} - {product.get_plan_type_display()} subscription"
        else:
            product_description = product_name
        
        # Get price
        if hasattr(product, 'price'):
            price = str(product.price)
        elif hasattr(product, 'price_min'):
            price = str(product.price_min)
        else:
            price = "0.00"
        
        # Create payment
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": product_name,
                        "sku": str(product.id),
                        "price": price,
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": price,
                    "currency": "USD"
                },
                "description": product_description,
                "payee": {
                    "email": receiver_email
                }
            }]
        })
        
        logger.info(f"Creating PayPal payment for: {product_name} - ${price}")
        logger.info(f"Receiver: {receiver_email}")
        
        if payment.create():
            logger.info(f"✅ Payment created successfully: {payment.id}")
            return payment
        else:
            logger.error(f"❌ Payment creation failed: {payment.error}")
            return None
            
    except Exception as e:
        logger.error(f"❌ PayPal error: {e}")
        import traceback
        traceback.print_exc()
        return None


def execute_payment(payment_id, payer_id):
    """Execute PayPal payment with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if not PAYPAL_CONFIGURED:
                logger.error("❌ PayPal not configured")
                return None
            
            logger.info(f"Executing payment (attempt {attempt + 1}/{max_retries}): {payment_id}")
            
            # Find the payment
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if not payment:
                logger.error(f"❌ Payment not found: {payment_id}")
                return None
            
            # Execute the payment
            if payment.execute({"payer_id": payer_id}):
                logger.info(f"✅ Payment executed successfully: {payment_id}")
                return payment
            else:
                logger.error(f"❌ Execution failed: {payment.error}")
                
                # If it's a timeout or connection error, retry
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                return None
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            return None
            
        except Exception as e:
            logger.error(f"❌ Execute error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            return None
    
    return None


def test_paypal_connection():
    """Test PayPal connection"""
    try:
        if not PAYPAL_CONFIGURED:
            return False, "PayPal not configured"
        
        config = paypalrestsdk.config.__dict__
        client_id = config.get('client_id', '')
        mode = config.get('mode', '')
        
        if not client_id:
            return False, "Client ID not set in SDK"
        
        paypalrestsdk.Payment.all({"count": 1})
        return True, f"Connection successful in {mode} mode"
    except Exception as e:
        return False, str(e)