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
        if hasattr(activity.file, 'url'):
            video_url = activity.file.url
        else:
            video_url = str(activity.file)
        
        num_screenshots = activity.screenshot_count or 5
        
        # Get FFmpeg path
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video
            temp_video = os.path.join(temp_dir, f"video_{activity_id}.mp4")
            
            try:
                response = requests.get(video_url, stream=True, timeout=30)
                response.raise_for_status()
                
                with open(temp_video, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                return f"Failed to download video: {e}"
            
            # Simple approach - extract screenshots at intervals
            screenshots_created = []
            
            # Calculate intervals based on video duration (if we could get it)
            # For simplicity, we'll use fixed intervals
            timestamps = [2, 4, 6, 8, 10]  # seconds
            
            for i in range(min(num_screenshots, len(timestamps))):
                timestamp = timestamps[i]
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
                    result = subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
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
                    else:
                        print(f"  ❌ Screenshot {i+1} file is empty")
                    
                except subprocess.TimeoutExpired:
                    print(f"  ❌ Timeout on screenshot {i+1}")
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ FFmpeg error on screenshot {i+1}: {e.stderr}")
                except Exception as e:
                    print(f"  ❌ Error on screenshot {i+1}: {e}")
            
            # Mark activity as processed
            if screenshots_created:
                activity.video_processed = True
                activity.save()
                return f"Created {len(screenshots_created)} screenshots"
            else:
                # Try alternative method: use more timestamps
                return try_alternative_timestamps(activity, temp_video, ffmpeg_path, temp_dir)
        
    except Exception as e:
        print(f"🔥 Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return str(e)

def try_alternative_timestamps(activity, temp_video, ffmpeg_path, temp_dir):
    """Try alternative timestamps if the first attempt failed"""
    try:
        screenshots_created = []
        alt_timestamps = [1, 3, 5, 7, 9]  # different seconds
        
        for i, timestamp in enumerate(alt_timestamps[:activity.screenshot_count or 5]):
            output_file = os.path.join(temp_dir, f"screenshot_alt_{i+1}.jpg")
            
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
                subprocess.run(cmd, check=True, capture_output=True, timeout=30)
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    result = cloudinary.uploader.upload(
                        output_file,
                        folder=f"activity_screenshots/activity_{activity.id}",
                        public_id=f"screenshot_{i+1}",
                        overwrite=True,
                        resource_type="image"
                    )
                    
                    VideoScreenshot.objects.update_or_create(
                        activity=activity,
                        order=i+1,
                        defaults={
                            'timestamp': timestamp,
                            'image': result['public_id']
                        }
                    )
                    
                    screenshots_created.append(True)
            except:
                pass
        
        if screenshots_created:
            activity.video_processed = True
            activity.save()
            return f"Created {len(screenshots_created)} screenshots (alternative method)"
        else:
            return "No screenshots created with either method"
    
    except Exception as e:
        return f"Alternative method failed: {e}"