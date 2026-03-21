# signals.py - EMPTY FILE

# This file is intentionally left empty
# Previous signals were removed because they referenced non-existent fields

# your_main_app/signals.py

from django.contrib import messages
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added

@receiver(social_account_added)
def handle_google_signup(sender, request, sociallogin, **kwargs):
    """When users sign up with Google, remind them to add PayPal email"""
    user = sociallogin.user
    
    # Check if profile exists and no PayPal email
    if hasattr(user, 'profile') and not user.profile.paypal_email:
        messages.info(request, "Please add your PayPal email in your profile to receive payouts.")