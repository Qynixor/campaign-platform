# main/tasks.py - COMPLETE FIXED VERSION for Neon Database
import cloudinary
import cloudinary.uploader
import imageio_ffmpeg
import subprocess
import os
import tempfile
import requests
import json
import math
import re
import gc
import shutil
import time
from django.db import connection, connections, transaction
from django.db.utils import OperationalError, InterfaceError
from django.core.files.base import ContentFile

def refresh_db_connection(max_retries=3):
    """Close and reopen database connection to avoid stale connections"""
    for attempt in range(max_retries):
        try:
            # Close the old connection
            connection.close()
            # Force a new connection by touching the database
            from django.db import connections
            connections['default'].connect()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"⚠️ Failed to refresh DB connection: {e}")
            return False

def safe_db_operation(operation, *args, using='default', **kwargs):
    """Execute a database operation with connection retry logic"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # For Django ORM operations that need using parameter
            if 'using' in kwargs or any(isinstance(arg, dict) and 'using' in arg for arg in args):
                with transaction.atomic(using=using):
                    return operation(*args, **kwargs)
            else:
                # For simple functions that don't accept using parameter
                with transaction.atomic(using=using):
                    return operation(*args, **kwargs)
        except (OperationalError, InterfaceError) as e:
            if "closed" in str(e) or "timeout" in str(e) or "idle" in str(e):
                print(f"🔄 Database connection error, retrying ({attempt + 1}/{max_retries})...")
                if using == 'default':
                    refresh_db_connection()
                else:
                    try:
                        connections[using].close()
                        connections[using].ensure_connection()
                    except:
                        pass
                time.sleep(1)
                continue
            else:
                raise
        except Exception as e:
            raise
    
    raise Exception(f"Failed after {max_retries} retries")

def get_video_duration(ffmpeg_path, video_file):
    """Get video duration using ffprobe or ffmpeg"""
    import subprocess
    import re
    
    # Try ffprobe first
    try:
        # On Windows, ffprobe might be in the same directory
        ffprobe_path = os.path.join(os.path.dirname(ffmpeg_path), 'ffprobe.exe')
        
        if not os.path.exists(ffprobe_path):
            ffprobe_path = ffmpeg_path.replace('ffmpeg', 'ffprobe')
        
        if os.path.exists(ffprobe_path):
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_file
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, timeout=30, text=True)
            duration = float(result.stdout.strip())
            return duration
    except Exception as e:
        print(f"⚠️ ffprobe failed: {e}")
    
    # Fallback to ffmpeg
    try:
        cmd = [ffmpeg_path, '-i', video_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse duration from stderr
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)", result.stderr)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"⚠️ ffmpeg duration detection failed: {e}")
    
    return 0

def process_video_screenshots(activity_id):
    """
    Extract screenshots from video - FIXED VERSION for Neon Database
    Uses direct/unpooled connection for long-running task
    """
    # Import here to avoid circular imports
    from .models import Activity, VideoScreenshot
    
    # Use direct connection for this long-running task
    db_alias = 'direct' if 'direct' in connections else 'default'
    print(f"🔌 Using database connection: {db_alias}")
    
    try:
        # Get connection for this task
        task_connection = connections[db_alias]
        task_connection.ensure_connection()
        
        # Get activity with fresh connection - DON'T pass using parameter to the function
        def get_activity():
            return Activity.objects.using(db_alias).get(id=activity_id)
        
        # Call without passing using parameter again
        activity = safe_db_operation(get_activity, using=db_alias)
        
        if not activity.file or not activity.is_video:
            return f"Activity {activity_id} is not a video"
        
        print(f"🎥 Processing video for activity {activity_id}...")
        
        # Get video URL from Cloudinary
        if hasattr(activity.file, 'url'):
            video_url = activity.file.url
        else:
            video_url = str(activity.file)
        
        # Clean URL - remove query parameters if present
        if '?' in video_url:
            video_url = video_url.split('?')[0]
        
        num_screenshots = activity.screenshot_count or 5
        print(f"📸 Will extract {num_screenshots} screenshots")
        
        # Get FFmpeg path
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"🔧 Using FFmpeg at: {ffmpeg_path}")
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video
            temp_video = os.path.join(temp_dir, f"video_{activity_id}.mp4")
            
            print(f"⬇️ Downloading video from: {video_url}")
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(video_url, stream=True, timeout=60, headers=headers)
                response.raise_for_status()
                
                file_size = 0
                with open(temp_video, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            file_size += len(chunk)
                
                print(f"✅ Video downloaded: {file_size / (1024*1024):.1f} MB")
            except Exception as e:
                print(f"❌ Failed to download video: {e}")
                return f"Failed to download video: {e}"
            
            # Get video duration
            duration = get_video_duration(ffmpeg_path, temp_video)
            print(f"⏱️ Video duration: {duration:.2f} seconds")
            
            if duration <= 0:
                duration = 60
                print(f"⚠️ Using default duration: {duration} seconds")
            
            # Calculate timestamps within video duration
            if duration <= 2:
                # Very short video
                timestamps = [0.5] if duration > 0.5 else [0.1]
                print(f"⚠️ Video too short, using single timestamp: {timestamps[0]:.1f}s")
            else:
                # Spread timestamps evenly
                start_time = 0.5
                end_time = duration - 0.5
                
                if num_screenshots == 1:
                    timestamps = [duration / 2]
                else:
                    step = (end_time - start_time) / (num_screenshots - 1)
                    timestamps = [start_time + (i * step) for i in range(num_screenshots)]
                
                # Ensure timestamps are within bounds
                timestamps = [max(0.1, min(t, duration - 0.1)) for t in timestamps]
            
            print(f"📅 Screenshot timestamps: {[f'{t:.1f}s' for t in timestamps]}")
            
            screenshots_created = 0
            
            # Process each screenshot
            for i, timestamp in enumerate(timestamps):
                # Refresh connection if using default (pooled) connection
                if db_alias == 'default' and i > 0 and i % 2 == 0:
                    print(f"🔄 Refreshing database connection...")
                    refresh_db_connection()
                
                # Create a fresh copy for this screenshot (avoids Windows file locking)
                video_copy = os.path.join(temp_dir, f"video_copy_{i+1}.mp4")
                try:
                    shutil.copy2(temp_video, video_copy)
                except Exception as e:
                    print(f"  ❌ Failed to copy video for screenshot {i+1}: {e}")
                    continue
                
                output_file = os.path.join(temp_dir, f"screenshot_{i+1}.jpg")
                
                # Try JPEG extraction first
                cmd = [
                    ffmpeg_path,
                    '-ss', str(timestamp),
                    '-i', video_copy,
                    '-frames:v', '1',
                    '-q:v', '2',
                    '-vf', 'scale=800:-2',
                    '-y',
                    output_file
                ]
                
                try:
                    print(f"  ⏱️ Extracting screenshot {i+1} at {timestamp:.1f}s...")
                    result = subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                    
                    # Clean up video copy
                    try:
                        os.remove(video_copy)
                    except:
                        pass
                    
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                        file_size_kb = os.path.getsize(output_file) / 1024
                        print(f"  ✅ Screenshot {i+1} created: {file_size_kb:.1f} KB")
                        
                        # Upload to Cloudinary
                        try:
                            upload_result = cloudinary.uploader.upload(
                                output_file,
                                folder=f"activity_screenshots/activity_{activity_id}",
                                public_id=f"screenshot_{i+1}",
                                overwrite=True,
                                resource_type="image",
                                quality="auto:good"
                            )
                            
                            print(f"  ☁️ Uploaded to Cloudinary: {upload_result.get('public_id')}")
                            
                            # Create screenshot record with safe DB operation
                            def save_screenshot():
                                screenshot, created = VideoScreenshot.objects.using(db_alias).update_or_create(
                                    activity=activity,
                                    order=i+1,
                                    defaults={
                                        'timestamp': timestamp,
                                        'image': upload_result['public_id']
                                    }
                                )
                                return screenshot
                            
                            safe_db_operation(save_screenshot, using=db_alias)
                            screenshots_created += 1
                            
                        except Exception as e:
                            print(f"  ❌ Cloudinary upload failed: {e}")
                            
                            # Try PNG fallback for upload
                            try:
                                png_file = os.path.join(temp_dir, f"screenshot_{i+1}.png")
                                if os.path.exists(png_file) and os.path.getsize(png_file) > 1000:
                                    upload_result = cloudinary.uploader.upload(
                                        png_file,
                                        folder=f"activity_screenshots/activity_{activity_id}",
                                        public_id=f"screenshot_{i+1}",
                                        resource_type="image"
                                    )
                                    
                                    def save_png_screenshot():
                                        VideoScreenshot.objects.using(db_alias).update_or_create(
                                            activity=activity,
                                            order=i+1,
                                            defaults={
                                                'timestamp': timestamp,
                                                'image': upload_result['public_id']
                                            }
                                        )
                                    
                                    safe_db_operation(save_png_screenshot, using=db_alias)
                                    screenshots_created += 1
                                    print(f"  ✅ PNG upload succeeded for screenshot {i+1}")
                            except:
                                pass
                    else:
                        print(f"  ❌ Screenshot {i+1} file is empty or too small")
                        
                        # Try PNG fallback for extraction
                        png_file = os.path.join(temp_dir, f"screenshot_{i+1}.png")
                        png_cmd = [
                            ffmpeg_path,
                            '-ss', str(timestamp),
                            '-i', video_copy,
                            '-frames:v', '1',
                            '-y',
                            png_file
                        ]
                        
                        try:
                            subprocess.run(png_cmd, check=True, capture_output=True, timeout=60)
                            if os.path.exists(png_file) and os.path.getsize(png_file) > 1000:
                                print(f"  ✅ PNG extraction succeeded for screenshot {i+1}")
                                
                                upload_result = cloudinary.uploader.upload(
                                    png_file,
                                    folder=f"activity_screenshots/activity_{activity_id}",
                                    public_id=f"screenshot_{i+1}",
                                    resource_type="image"
                                )
                                
                                def save_png_fallback():
                                    VideoScreenshot.objects.using(db_alias).update_or_create(
                                        activity=activity,
                                        order=i+1,
                                        defaults={
                                            'timestamp': timestamp,
                                            'image': upload_result['public_id']
                                        }
                                    )
                                
                                safe_db_operation(save_png_fallback, using=db_alias)
                                screenshots_created += 1
                        except Exception as e:
                            print(f"  ❌ PNG fallback failed: {e}")
                    
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ FFmpeg error on screenshot {i+1}: {e}")
                    if e.stderr:
                        print(f"     stderr: {e.stderr.decode()}")
                except Exception as e:
                    print(f"  ❌ Error on screenshot {i+1}: {e}")
                
                # Force garbage collection
                gc.collect()
            
            # If we got at least one screenshot, duplicate for missing ones
            if screenshots_created > 0 and screenshots_created < num_screenshots:
                print(f"⚠️ Only created {screenshots_created}/{num_screenshots} screenshots. Duplicating...")
                
                # Get the first screenshot to duplicate
                def get_first_screenshot():
                    return VideoScreenshot.objects.using(db_alias).filter(activity=activity, order=1).first()
                
                first_screenshot = safe_db_operation(get_first_screenshot, using=db_alias)
                
                if first_screenshot:
                    for i in range(screenshots_created + 1, num_screenshots + 1):
                        try:
                            def duplicate_screenshot():
                                return VideoScreenshot.objects.using(db_alias).update_or_create(
                                    activity=activity,
                                    order=i,
                                    defaults={
                                        'timestamp': timestamps[i-1] if i-1 < len(timestamps) else i * 2,
                                        'image': first_screenshot.image
                                    }
                                )
                            
                            safe_db_operation(duplicate_screenshot, using=db_alias)
                            print(f"  ✅ Duplicated screenshot for position {i}")
                            screenshots_created += 1
                        except Exception as e:
                            print(f"  ❌ Failed to duplicate for position {i}: {e}")
            
            # Mark activity as processed
            if screenshots_created > 0:
                def mark_processed():
                    activity.video_processed = True
                    activity.save(using=db_alias)
                
                safe_db_operation(mark_processed, using=db_alias)
                print(f"🎉 Success! Created {screenshots_created} screenshots")
                return f"Created {screenshots_created} screenshots"
            else:
                print("❌ No screenshots created")
                
                # Ultimate fallback: use Cloudinary's auto-generated thumbnail
                try:
                    print("🔄 Trying Cloudinary auto-thumbnail...")
                    thumbnail_url = cloudinary.CloudinaryImage(activity.file.public_id).build_url(
                        resource_type="video",
                        transformation=[
                            {'width': 800, 'crop': 'scale'},
                            {'start_offset': '1s'},
                            {'format': 'jpg'}
                        ]
                    )
                    
                    response = requests.get(thumbnail_url, timeout=30)
                    if response.status_code == 200:
                        thumb_path = os.path.join(temp_dir, "auto_thumb.jpg")
                        with open(thumb_path, 'wb') as f:
                            f.write(response.content)
                        
                        upload_result = cloudinary.uploader.upload(
                            thumb_path,
                            folder=f"activity_screenshots/activity_{activity_id}",
                            public_id="screenshot_1",
                            resource_type="image"
                        )
                        
                        for i in range(num_screenshots):
                            def save_thumbnail():
                                VideoScreenshot.objects.using(db_alias).update_or_create(
                                    activity=activity,
                                    order=i+1,
                                    defaults={
                                        'timestamp': i * 2,
                                        'image': upload_result['public_id']
                                    }
                                )
                            
                            safe_db_operation(save_thumbnail, using=db_alias)
                        
                        def mark_thumbnail_processed():
                            activity.video_processed = True
                            activity.save(using=db_alias)
                        
                        safe_db_operation(mark_thumbnail_processed, using=db_alias)
                        print(f"🎉 Created {num_screenshots} screenshots from Cloudinary thumbnail")
                        return f"Created {num_screenshots} screenshots from Cloudinary"
                except Exception as e:
                    print(f"❌ Cloudinary thumbnail failed: {e}")
                
                return "Failed to create screenshots"
    
    except Exception as e:
        print(f"🔥 Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return str(e)
    finally:
        # Always close the connection when done
        try:
            connections[db_alias].close()
        except:
            pass

def process_video_screenshots_task(activity_id):
    """Wrapper for async task processing"""
    return process_video_screenshots(activity_id)