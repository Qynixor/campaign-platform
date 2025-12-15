# signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile  # Import your Profile model

@receiver(post_save, sender=Profile)
def verify_profile(sender, instance, created, **kwargs):
    if created:  # Only execute for newly created profiles
        if instance.followers.count() > 1:  # Check if the profile has more than 1 million followers
            instance.verified = True
            instance.save(update_fields=['verified'])




