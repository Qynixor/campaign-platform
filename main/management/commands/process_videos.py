# management/commands/process_videos.py
# main/management/commands/process_videos.py
from django.core.management.base import BaseCommand
from main.models import Activity
from main.tasks import process_video_screenshots  # Import the function directly

class Command(BaseCommand):
    help = 'Process videos and extract screenshots'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--activity-id',
            type=int,
            help='Process a specific activity ID'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all unprocessed videos'
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess already processed videos'
        )
    
    def handle(self, *args, **options):
        if options['activity_id']:
            activities = Activity.objects.filter(id=options['activity_id'], is_video=True)
            if not activities.exists():
                self.stdout.write(self.style.ERROR(f"Activity {options['activity_id']} not found or not a video"))
                return
        
        elif options['all']:
            if options['reprocess']:
                activities = Activity.objects.filter(is_video=True)
            else:
                activities = Activity.objects.filter(is_video=True, video_processed=False)
        
        else:
            # Default: process first 10 unprocessed videos
            activities = Activity.objects.filter(is_video=True, video_processed=False)[:10]
        
        count = 0
        for activity in activities:
            self.stdout.write(f"Processing activity {activity.id}...")
            # REMOVED .delay() - call function directly
            process_video_screenshots(activity.id)
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"Processed {count} videos")
        )