# management/commands/send_audio_reminders.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from main.models import Campaign

# Then in your command:
from django.conf import settings

site_url = settings.SITE_URL
site_name = settings.SITE_NAME


# management/commands/send_audio_reminders.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from main.models import Campaign

class Command(BaseCommand):
    help = 'Send audio reminders for campaigns without sound'
    
    def handle(self, *args, **options):
        # USE PRODUCTION DOMAIN!
        DOMAIN = "https://rallynex.com"
        
        campaigns = Campaign.objects.filter(audio=None, is_active=True)
        
        for campaign in campaigns:
            user = campaign.user.user
            
            if user.email:
                send_mail(
                    subject=f"Unlock Soundmark Tribe on '{campaign.title}'",
                    message=f"""Hi {user.username},

Unlock special features by adding audio to your campaign:

🎵 **Add Audio:**
{DOMAIN}/recreate-campaign/{campaign.id}/

Best,
RallyNex Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                print(f"Sent to {user.email}")