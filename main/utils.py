# utils.py
from .models import Profile
# utils.py
import paypalrestsdk
from decimal import Decimal

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(profile1, profile2):
    # Concatenate the text fields from both profiles
    text1 = f"{profile1.bio} {profile1.location} {profile1.highest_level_of_education}"
    text2 = f"{profile2.bio} {profile2.location} {profile2.highest_level_of_education}"

    # Create a TF-IDF vectorizer
    vectorizer = TfidfVectorizer()

    # Fit and transform the text data
    tfidf_matrix = vectorizer.fit_transform([text1, text2])

    # Calculate the cosine similarity between the two profiles
    similarity_score = cosine_similarity(tfidf_matrix)[0, 1]

    return similarity_score


# main/utils.py

def validate_no_long_words(text):
    """
    Validate that no word in the text is too long.
    Usually used to prevent extremely long concatenated words.
    """
    if not text:
        return
    
    words = text.split()
    for word in words:
        # Check if any word is longer than 50 characters (adjust as needed)
        if len(word) > 50:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Word '{word[:20]}...' is too long. Please use spaces or break it into smaller words.")
    
    return text








def calculate_campaign_cost(audience_size, duration):
    # Define your pricing model based on audience size and duration
    # For example, you could charge a certain amount per user per day
    cost_per_user_per_day = Decimal('0.1')  # Adjust this value based on your pricing model
    total_cost = cost_per_user_per_day * audience_size * duration
    return total_cost

def charge_advertiser_with_paypal(advertiser_email, amount):
    paypal_client_id = 'YOUR_PAYPAL_CLIENT_ID'
    paypal_client_secret = 'YOUR_PAYPAL_CLIENT_SECRET'

    paypalrestsdk.configure({
        "mode": "sandbox",  # Change to "live" for production
        "client_id": paypal_client_id,
        "client_secret": paypal_client_secret
    })

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "transactions": [{
            "amount": {
                "total": str(amount),
                "currency": "USD"
            },
            "description": "Payment for advertising campaign"
        }],
        "redirect_urls": {
            "return_url": "YOUR_RETURN_URL",
            "cancel_url": "YOUR_CANCEL_URL"
        }
    })

    if payment.create():
        # Payment created successfully, redirect advertiser to approval URL
        for link in payment.links:
            if link.method == "REDIRECT":
                redirect_url = link.href
                # Redirect advertiser to PayPal for payment approval
                return redirect_url
    else:
        # Payment creation failed, handle the error
        error_message = payment.error
        return None







def filter_target_audience(campaign):
    target_location = campaign.target_location
    target_age_min = campaign.target_age_min
    target_age_max = campaign.target_age_max
    target_education = campaign.target_education
    target_gender = campaign.target_gender
    
    filtered_profiles = Profile.objects.all()
    if target_location:
        filtered_profiles = filtered_profiles.filter(location=target_location)
    if target_age_min:
        filtered_profiles = filtered_profiles.filter(age__gte=target_age_min)
    if target_age_max:
        filtered_profiles = filtered_profiles.filter(age__lte=target_age_max)
    if target_education:
        filtered_profiles = filtered_profiles.filter(highest_level_of_education=target_education)
    if target_gender:
        filtered_profiles = filtered_profiles.filter(gender=target_gender)
    
    return filtered_profiles
