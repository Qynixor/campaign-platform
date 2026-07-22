import logging
import paypalrestsdk
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

def create_payment(product, user, request):
    try:
        price = str(product.price if hasattr(product, 'price') else product.price_min)
        name = getattr(product, 'name', 'Product')
        
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {
                "return_url": request.build_absolute_uri(reverse('paypal_execute')),
                "cancel_url": request.build_absolute_uri(reverse('paypal_cancel'))
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": name,
                        "sku": str(product.id),
                        "price": price,
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {"total": price, "currency": "USD"},
                "description": getattr(product, 'description', name)[:200]
            }]
        })
        
        if payment.create():
            return payment
        return None
    except Exception as e:
        logger.error(f"PayPal error: {e}")
        return None

def execute_payment(payment_id, payer_id):
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            return payment
        return None
    except Exception as e:
        logger.error(f"Execute error: {e}")
        return None

def test_paypal_connection():
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [{
                "amount": {"total": "1.00", "currency": "USD"},
                "description": "Test"
            }]
        })
        if payment.create():
            return True, "Connected"
        return False, "Failed"
    except Exception as e:
        return False, str(e)