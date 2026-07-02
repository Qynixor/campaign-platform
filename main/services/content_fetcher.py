import re
import requests
import os
import hashlib
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.utils import timezone
from cloudinary.uploader import upload
import yt_dlp
from bs4 import BeautifulSoup
import json

class ContentFetcher:
    """Professional content fetching service that actually stores real content"""
    
    def __init__(self, imported_content):
        self.imported_content = imported_content
        self.platform = imported_content.platform
        self.url = imported_content.platform_url
        
    def fetch_and_store(self):
        """Main entry point - fetch and store real content"""
        self.imported_content.processing_status = 'fetching'
        self.imported_content.last_fetch_attempt = timezone.now()
        self.imported_content.fetch_attempts += 1
        self.imported_content.save()
        
        try:
            if self.platform == 'youtube':
                self._fetch_youtube()
            elif self.platform == 'tiktok':
                self._fetch_tiktok()
            elif self.platform == 'instagram':
                self._fetch_instagram()
            elif self.platform == 'twitter':
                self._fetch_twitter()
            else:
                self._fetch_generic()
                
            self.imported_content.processing_status = 'stored'
            self.imported_content.processed_at = timezone.now()
            self.imported_content.save()
            
            # Update linked activity if exists
            if self.imported_content.created_activity:
                activity = self.imported_content.created_activity
                if not activity.content and self.imported_content.caption:
                    activity.content = self.imported_content.caption
                # Store rendered HTML in the activity's embed_html field
                if self.imported_content.rendered_html:
                    activity.embed_html = self.imported_content.rendered_html
                    activity.save()
                    print(f"✅ Updated activity {activity.id} with rendered HTML")
            
            return True
            
        except Exception as e:
            self.imported_content.processing_status = 'failed'
            self.imported_content.processing_error = str(e)
            self.imported_content.save()
            print(f"❌ Content fetch error: {e}")
            raise
    
    def _fetch_youtube(self):
        """Fetch and store YouTube content"""
        video_id = self._extract_youtube_id()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.url, download=False)
                
                # Store metadata
                self.imported_content.content_title = info.get('title', '')[:200]
                self.imported_content.content_description = info.get('description', '')[:500]
                self.imported_content.author_name = info.get('uploader', '')
                self.imported_content.view_count = info.get('view_count', 0)
                self.imported_content.like_count = info.get('like_count', 0)
                self.imported_content.comment_count = info.get('comment_count', 0)
                self.imported_content.content_type = 'video'
                self.imported_content.original_tags = info.get('tags', [])[:10]
                self.imported_content.raw_text = f"{info.get('title', '')}\n{info.get('description', '')}"
                
                if info.get('upload_date'):
                    try:
                        self.imported_content.original_created_at = timezone.datetime.strptime(
                            str(info.get('upload_date')), '%Y%m%d'
                        ).replace(tzinfo=timezone.utc)
                    except:
                        pass
                
                # Fetch and store thumbnail
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    best_thumb = max(thumbnails, key=lambda x: x.get('width', 0))
                    self._fetch_and_store_thumbnail(best_thumb['url'])
                else:
                    # Fallback thumbnail
                    self._fetch_and_store_thumbnail(f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg")
                
                # Generate professional card (this will be stored in rendered_html)
                self.imported_content.rendered_html = self._generate_youtube_card(info, video_id)
                
            except Exception as e:
                print(f"YouTube fetch error: {e}")
                raise
    
    def _generate_youtube_card(self, info, video_id):
        """Generate a professional-looking card for YouTube content"""
        title = info.get('title', 'YouTube Video')[:60]
        channel = info.get('uploader', 'Unknown Channel')
        views = self.imported_content.view_count
        likes = self.imported_content.like_count
        comments = self.imported_content.comment_count
        description = info.get('description', '')[:150]
        
        return f'''
        <div class="content-card youtube-card" style="
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            <div class="yt-thumbnail" style="position:relative;padding-bottom:56.25%;background:#000;cursor:pointer;" onclick="window.open('{self.url}', '_blank')">
                <img src="https://img.youtube.com/vi/{video_id}/hqdefault.jpg" alt="Video thumbnail" style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;">
                <div class="yt-play-button" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:68px;height:48px;background:rgba(255,255,255,0.9);border-radius:12px;display:flex;align-items:center;justify-content:center;transition:all 0.3s ease;cursor:pointer;">
                    <i class="fab fa-youtube" style="color:#ff0000;font-size:24px;"></i>
                </div>
            </div>
            <div style="padding:16px;">
                <div style="font-weight:600;font-size:15px;color:var(--text-primary);margin-bottom:4px;">{title}</div>
                <div style="font-size:13px;color:var(--text-secondary);margin-bottom:8px;">{channel}</div>
                <div style="display:flex;gap:16px;font-size:12px;color:var(--text-muted);flex-wrap:wrap;">
                    <span><i class="fas fa-eye"></i> {views:,}</span>
                    <span><i class="fas fa-heart"></i> {likes:,}</span>
                    <span><i class="fas fa-comment"></i> {comments:,}</span>
                </div>
                {f'<div style="font-size:13px;color:var(--text-secondary);line-height:1.5;margin-top:8px;max-height:60px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">{description}</div>' if description else ''}
                <a href="{self.url}" target="_blank" style="display:inline-block;margin-top:8px;font-size:12px;color:var(--accent);text-decoration:none;">
                    <i class="fab fa-youtube"></i> Watch on YouTube →
                </a>
            </div>
        </div>
        '''
    
    def _fetch_tiktok(self):
        """Fetch and store TikTok content"""
        try:
            oembed_url = f"https://www.tiktok.com/oembed?url={self.url}"
            response = requests.get(oembed_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                self.imported_content.content_title = data.get('title', 'TikTok Video')[:100]
                self.imported_content.author_name = data.get('author_name', '')
                self.imported_content.content_type = 'video'
                
                if data.get('thumbnail_url'):
                    self._fetch_and_store_thumbnail(data['thumbnail_url'])
                    self.imported_content.thumbnail_url = data['thumbnail_url']
                
                self.imported_content.raw_text = data.get('title', '')
                
                # Try to get more metadata from additional API call
                self._fetch_tiktok_metadata()
                
                self.imported_content.rendered_html = self._generate_tiktok_card()
            else:
                # Fallback: generate basic card
                self.imported_content.rendered_html = self._generate_tiktok_card()
                
        except Exception as e:
            print(f"TikTok fetch error: {e}")
            self.imported_content.rendered_html = self._generate_tiktok_card()
            raise
    
    def _fetch_tiktok_metadata(self):
        """Fetch additional TikTok metadata"""
        try:
            # Try to get video ID from URL
            video_id = self.url.split('/')[-1].split('?')[0]
            if video_id:
                # Attempt to fetch additional data from TikTok's API
                api_url = f"https://www.tiktok.com/api/v1/item/detail/?itemId={video_id}"
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('item'):
                        item = data['item']
                        self.imported_content.view_count = item.get('stats', {}).get('playCount', 0)
                        self.imported_content.like_count = item.get('stats', {}).get('diggCount', 0)
                        self.imported_content.comment_count = item.get('stats', {}).get('commentCount', 0)
                        self.imported_content.share_count = item.get('stats', {}).get('shareCount', 0)
        except Exception as e:
            print(f"TikTok metadata fetch error: {e}")
    
    def _generate_tiktok_card(self):
        """Generate TikTok card"""
        caption = self.imported_content.caption[:100] or self.imported_content.content_title
        author = self.imported_content.author_name or 'TikTok Creator'
        likes = self.imported_content.like_count
        comments = self.imported_content.comment_count
        views = self.imported_content.view_count
        thumbnail = self.imported_content.thumbnail_file.url if self.imported_content.thumbnail_file else ''
        
        thumbnail_html = ''
        if thumbnail:
            thumbnail_html = f'''
            <div style="position:relative;border-radius:8px;overflow:hidden;margin-bottom:12px;background:#000;cursor:pointer;" onclick="window.open('{self.url}', '_blank')">
                <img src="{thumbnail}" style="width:100%;max-height:400px;object-fit:contain;" />
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:60px;height:60px;background:rgba(255,255,255,0.2);backdrop-filter:blur(4px);border-radius:50%;display:flex;align-items:center;justify-content:center;">
                    <i class="fas fa-play" style="color:#fff;font-size:24px;"></i>
                </div>
            </div>
            '''
        
        return f'''
        <div class="content-card tiktok-card" style="
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            <div style="padding:16px;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                    <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#00f2ea,#ff004f);padding:2px;">
                        <div style="width:100%;height:100%;border-radius:50%;background:var(--card-bg);display:flex;align-items:center;justify-content:center;">
                            <i class="fab fa-tiktok" style="color:#00f2ea;font-size:20px;"></i>
                        </div>
                    </div>
                    <div>
                        <div style="font-weight:600;color:var(--text-primary);font-size:14px;">@{author}</div>
                        <div style="font-size:11px;color:var(--text-muted);">TikTok</div>
                    </div>
                </div>
                {thumbnail_html}
                <p style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{caption}</p>
                <div style="display:flex;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border-color);flex-wrap:wrap;">
                    {f'<span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-eye"></i> {views:,}</span>' if views else ''}
                    <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-heart"></i> {likes:,}</span>
                    <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-comment"></i> {comments:,}</span>
                </div>
                <a href="{self.url}" target="_blank" style="display:inline-block;margin-top:8px;font-size:12px;color:#00f2ea;text-decoration:none;">
                    <i class="fab fa-tiktok"></i> View on TikTok →
                </a>
            </div>
        </div>
        '''
    
    def _fetch_instagram(self):
        """Fetch and store Instagram content"""
        try:
            # Try Graph API if available
            if hasattr(settings, 'INSTAGRAM_ACCESS_TOKEN') and settings.INSTAGRAM_ACCESS_TOKEN:
                oembed_url = f"https://graph.facebook.com/v18.0/instagram_oembed?url={self.url}&access_token={settings.INSTAGRAM_ACCESS_TOKEN}"
                response = requests.get(oembed_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self.imported_content.content_title = data.get('title', 'Instagram Post')[:100]
                    self.imported_content.author_name = data.get('author_name', '')
                    self.imported_content.raw_text = data.get('title', '')
                    if data.get('thumbnail_url'):
                        self._fetch_and_store_thumbnail(data['thumbnail_url'])
                        self.imported_content.thumbnail_url = data['thumbnail_url']
            
            self.imported_content.rendered_html = self._generate_instagram_card()
            
        except Exception as e:
            print(f"Instagram fetch error: {e}")
            self.imported_content.rendered_html = self._generate_instagram_card()
    
    def _generate_instagram_card(self):
        """Generate Instagram card"""
        caption = self.imported_content.caption[:100] or self.imported_content.content_title
        author = self.imported_content.author_name or 'Instagram Creator'
        likes = self.imported_content.like_count
        comments = self.imported_content.comment_count
        thumbnail = self.imported_content.thumbnail_file.url if self.imported_content.thumbnail_file else ''
        
        thumbnail_html = ''
        if thumbnail:
            thumbnail_html = f'<div style="border-radius:8px;overflow:hidden;margin-bottom:12px;background:#000;cursor:pointer;" onclick="window.open(\'{self.url}\', \'_blank\')"><img src="{thumbnail}" style="width:100%;max-height:400px;object-fit:contain;" /></div>'
        
        return f'''
        <div class="content-card instagram-card" style="
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            <div style="padding:16px;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                    <div style="width:48px;height:48px;border-radius:50%;background:linear-gradient(45deg,#f09433,#e6683c,#dc2743);display:flex;align-items:center;justify-content:center;">
                        <i class="fab fa-instagram" style="color:#fff;font-size:20px;"></i>
                    </div>
                    <div>
                        <div style="font-weight:600;color:var(--text-primary);font-size:14px;">@{author}</div>
                        <div style="font-size:11px;color:var(--text-muted);">Instagram</div>
                    </div>
                </div>
                {thumbnail_html}
                <p style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{caption}</p>
                <div style="display:flex;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border-color);">
                    <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-heart"></i> {likes:,}</span>
                    <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-comment"></i> {comments:,}</span>
                </div>
                <a href="{self.url}" target="_blank" style="display:inline-block;margin-top:8px;font-size:12px;color:#dc2743;text-decoration:none;">
                    <i class="fab fa-instagram"></i> View on Instagram →
                </a>
            </div>
        </div>
        '''
    
    def _fetch_twitter(self):
        """Fetch and store Twitter/X content"""
        try:
            tweet_id = self._extract_tweet_id()
            if tweet_id:
                oembed_url = f"https://publish.twitter.com/oembed?url=https://twitter.com/i/web/status/{tweet_id}&omit_script=1&dnt=1&hide_thread=1&theme=dark"
                response = requests.get(oembed_url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self.imported_content.content_title = data.get('title', 'Tweet')[:100]
                    self.imported_content.author_name = data.get('author_name', '')
                    self.imported_content.raw_text = data.get('title', '')
                    
                    # Try to extract like count from HTML (rough estimate)
                    html = data.get('html', '')
                    like_match = re.search(r'like-count[^>]*>([0-9,]+)', html)
                    if like_match:
                        self.imported_content.like_count = int(like_match.group(1).replace(',', ''))
            
            self.imported_content.rendered_html = self._generate_twitter_card()
            
        except Exception as e:
            print(f"Twitter fetch error: {e}")
            self.imported_content.rendered_html = self._generate_twitter_card()
    
    def _generate_twitter_card(self):
        """Generate Twitter/X card"""
        caption = self.imported_content.caption[:140] or self.imported_content.content_title
        author = self.imported_content.author_name or 'Twitter User'
        likes = self.imported_content.like_count
        comments = self.imported_content.comment_count
        
        return f'''
        <div class="content-card twitter-card" style="
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            padding:16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <div style="width:48px;height:48px;border-radius:50%;background:var(--bg-secondary);display:flex;align-items:center;justify-content:center;">
                    <i class="fab fa-x-twitter" style="color:#1DA1F2;font-size:22px;"></i>
                </div>
                <div>
                    <div style="font-weight:600;color:var(--text-primary);font-size:14px;">@{author}</div>
                    <div style="font-size:11px;color:var(--text-muted);">X/Twitter</div>
                </div>
            </div>
            <p style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{caption}</p>
            <div style="display:flex;gap:16px;margin-top:12px;padding-top:12px;border-top:1px solid var(--border-color);">
                <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-heart"></i> {likes:,}</span>
                <span style="font-size:12px;color:var(--text-muted);"><i class="fas fa-comment"></i> {comments:,}</span>
            </div>
            <a href="{self.url}" target="_blank" style="display:inline-block;margin-top:8px;font-size:12px;color:#1DA1F2;text-decoration:none;">
                <i class="fab fa-x-twitter"></i> View on X →
            </a>
        </div>
        '''
    
    def _fetch_generic(self):
        """Generic fetch for any URL"""
        try:
            response = requests.get(self.url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Get title
                title = soup.find('title')
                if title:
                    self.imported_content.content_title = title.text.strip()[:100]
                
                # Get description
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc:
                    self.imported_content.content_description = meta_desc.get('content', '')[:500]
                
                # Get OG image
                og_image = soup.find('meta', {'property': 'og:image'})
                if og_image:
                    self._fetch_and_store_thumbnail(og_image.get('content', ''))
                
                # Get OG title
                og_title = soup.find('meta', {'property': 'og:title'})
                if og_title and not self.imported_content.content_title:
                    self.imported_content.content_title = og_title.get('content', '')[:100]
                
                self.imported_content.raw_text = f"{self.imported_content.content_title}\n{self.imported_content.content_description}"
            
            self.imported_content.rendered_html = self._generate_generic_card()
            
        except Exception as e:
            print(f"Generic fetch error: {e}")
            self.imported_content.rendered_html = self._generate_generic_card()
    
    def _generate_generic_card(self):
        """Generate generic content card"""
        title = self.imported_content.content_title or 'Content'
        description = self.imported_content.content_description or 'View this content'
        thumbnail = self.imported_content.thumbnail_file.url if self.imported_content.thumbnail_file else ''
        
        thumbnail_html = ''
        if thumbnail:
            thumbnail_html = f'<img src="{thumbnail}" style="width:100%;max-height:200px;object-fit:cover;border-radius:8px;margin-bottom:12px;" />'
        
        return f'''
        <div class="content-card generic-card" style="
            background: var(--card-bg);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            padding:20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        ">
            {thumbnail_html}
            <h4 style="color:var(--text-primary);margin-bottom:8px;font-size:16px;">{title}</h4>
            <p style="font-size:13px;color:var(--text-secondary);line-height:1.5;">{description[:200]}</p>
            <a href="{self.url}" target="_blank" style="display:inline-block;margin-top:12px;font-size:13px;color:var(--accent);text-decoration:none;">
                <i class="fas fa-external-link-alt"></i> View Content →
            </a>
        </div>
        '''
    
    def _fetch_and_store_thumbnail(self, url):
        """Fetch and store a thumbnail locally on Cloudinary"""
        if not url:
            return
            
        try:
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200 and len(response.content) > 1000:
                content_type = response.headers.get('content-type', 'image/jpeg')
                extension = content_type.split('/')[-1] if '/' in content_type else 'jpg'
                
                # Generate a unique ID
                unique_id = hashlib.md5(url.encode()).hexdigest()[:12]
                
                upload_result = upload(
                    response.content,
                    folder='imported_thumbnails',
                    resource_type='image',
                    public_id=f"thumb_{unique_id}",
                    overwrite=True
                )
                
                self.imported_content.thumbnail_file = upload_result['public_id']
                self.imported_content.save(update_fields=['thumbnail_file'])
                print(f"✅ Thumbnail stored: {upload_result['public_id']}")
                return True
                
        except Exception as e:
            print(f"❌ Thumbnail fetch error: {e}")
        return False
    
    def _extract_youtube_id(self):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
            r'youtu\.be\/([0-9A-Za-z_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                return match.group(1)
        raise ValueError("Could not extract YouTube video ID")
    
    def _extract_tweet_id(self):
        """Extract tweet ID from Twitter/X URL"""
        patterns = [
            r'/status/(\d+)',
            r'/statuses/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.url)
            if match:
                return match.group(1)
        raise ValueError("Could not extract tweet ID")