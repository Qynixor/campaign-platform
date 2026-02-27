
# Add a management command to clean up stale sessions
# management/commands/cleanup_audio_sessions.py
"""
python manage.py cleanup_audio_sessions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from your_app.models import ActiveAudioSession

class Command(BaseCommand):
    help = 'Clean up stale audio sessions'

    def handle(self, *args, **options):
        # Delete sessions older than 5 minutes with no heartbeat
        stale_time = timezone.now() - timedelta(minutes=5)
        stale_sessions = ActiveAudioSession.objects.filter(last_heartbeat__lt=stale_time)
        count = stale_sessions.count()
        stale_sessions.delete()
        
        self.stdout.write(f"Deleted {count} stale audio sessions")