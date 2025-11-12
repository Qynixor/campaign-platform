import requests
import json
import base64
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def get_paypal_access_token():
    """Get PayPal API access token"""
    auth_url = f"{settings.PAYPAL_API_BASE}/v1/oauth2/token"
    auth_data = {"grant_type": "client_credentials"}
    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {base64.b64encode(f'{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}'.encode()).decode()}"
    }
    
    try:
        response = requests.post(auth_url, data=auth_data, headers=auth_headers)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting PayPal access token: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"PayPal auth response: {e.response.text}")
        return None

def create_paypal_pledge_order(amount, campaign_id, return_url, cancel_url, description="Pledge payment"):
    """Create a PayPal order for pledge"""
    access_token = get_paypal_access_token()
    if not access_token:
        logger.error("Failed to get PayPal access token for order creation")
        return None
    
    order_url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders"
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": str(amount)
                },
                "custom_id": f"campaign_{campaign_id}",
                "description": description
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "brand_name": "Your Platform Name",
            "user_action": "PAY_NOW"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=representation"
    }
    
    try:
        response = requests.post(order_url, data=json.dumps(order_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating PayPal order: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"PayPal order response: {e.response.text}")
        return None

def capture_paypal_order(order_id):
    """Capture a PayPal payment - return only the response data, not a tuple"""
    access_token = get_paypal_access_token()
    if not access_token:
        logger.error("Failed to get PayPal access token for order capture")
        return None
    
    capture_url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Prefer": "return=representation"
    }
    
    try:
        response = requests.post(capture_url, headers=headers)
        response.raise_for_status()
        return response.json()  # Return just the JSON data, not a tuple
    except requests.exceptions.RequestException as e:
        logger.error(f"Error capturing PayPal order {order_id}: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"PayPal capture response: {e.response.text}")
            try:
                # Return error response as dict
                error_data = e.response.json()
                error_data['error'] = True
                return error_data
            except:
                return {"error": str(e), "status": "failed"}
        return {"error": str(e), "status": "failed"}

def send_paypal_payout(recipient_email, amount, note, sender_item_id):
    """Send payout to recipient using PayPal Payouts"""
    access_token = get_paypal_access_token()
    if not access_token:
        logger.error("Failed to get PayPal access token for payout")
        return None
    
    payout_url = f"{settings.PAYPAL_API_BASE}/v1/payments/payouts"
    payout_data = {
        "sender_batch_header": {
            "sender_batch_id": f"batch_{int(timezone.now().timestamp())}",
            "email_subject": "You have received a pledge payment!",
            "email_message": f"You have received a pledge payment of ${amount} from our platform."
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": str(amount),
                    "currency": "USD"
                },
                "note": note,
                "receiver": recipient_email,
                "sender_item_id": sender_item_id
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    
    try:
        response = requests.post(payout_url, data=json.dumps(payout_data), headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending PayPal payout to {recipient_email}: {e}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"PayPal payout response: {e.response.text}")
        return None

def process_pledge_split(pledge_amount):
    """Calculate the split between campaign owner and platform"""
    platform_share = round(float(pledge_amount) * 0.10, 2)  # 10% to platform
    campaign_owner_share = round(float(pledge_amount) * 0.90, 2)  # 50% to campaign owner
    
    return platform_share, campaign_owner_share