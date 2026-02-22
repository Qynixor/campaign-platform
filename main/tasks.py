from background_task import background
from .cron import send_pledge_reminders

@background(schedule=0)
def run_pledge_reminders_task():
    send_pledge_reminders()
# main/tasks.py - SIMPLE VERSION, NO CELERY!
import cloudinary
import cloudinary.uploader
import imageio_ffmpeg
import subprocess
import os
import tempfile
import requests

def process_video_screenshots(activity_id):
    """
    Extract screenshots from video - SIMPLE, NO CELERY!
    """
    # Import here to avoid circular imports
    from .models import Activity, VideoScreenshot
    
    try:
        activity = Activity.objects.get(id=activity_id)
        
        if not activity.file or not activity.is_video:
            return f"Activity {activity_id} is not a video"
        
        print(f"🎥 Processing video for activity {activity_id}...")
        
        # Get video URL from Cloudinary
        video_url = activity.file.url
        num_screenshots = activity.screenshot_count or 5
        
        # Get FFmpeg path
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video
            temp_video = os.path.join(temp_dir, f"video_{activity_id}.mp4")
            
            response = requests.get(video_url, stream=True)
            with open(temp_video, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Simple approach - extract screenshots at 2, 4, 6, 8, 10 seconds
            screenshots_created = []
            
            for i in range(num_screenshots):
                timestamp = (i + 1) * 2  # 2, 4, 6, 8, 10 seconds
                output_file = os.path.join(temp_dir, f"screenshot_{i+1}.jpg")
                
                cmd = [
                    ffmpeg_path,
                    '-i', temp_video,
                    '-ss', str(timestamp),
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y',
                    output_file
                ]
                
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        output_file,
                        folder=f"activity_screenshots/activity_{activity_id}",
                        public_id=f"screenshot_{i+1}",
                        overwrite=True,
                        resource_type="image"
                    )
                    
                    # Create screenshot record
                    VideoScreenshot.objects.update_or_create(
                        activity=activity,
                        order=i+1,
                        defaults={
                            'timestamp': timestamp,
                            'image': result['public_id']
                        }
                    )
                    
                    print(f"  ✅ Created screenshot {i+1}")
                    screenshots_created.append(True)
                    
                except Exception as e:
                    print(f"  ❌ Error on screenshot {i+1}: {e}")
            
            # Mark activity as processed
            if screenshots_created:
                activity.video_processed = True
                activity.save()
                return f"Created {len(screenshots_created)} screenshots"
            else:
                return "No screenshots created"
        
    except Exception as e:
        print(f"🔥 Error processing video: {e}")
        return str(e)