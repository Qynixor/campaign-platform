from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import (
    Profile, SocialConnection, ImportedContent,
    Journey, Activity, JourneyFollow, Tag, JourneyTag,
    ActivityLove, ActivityComment, JourneySave, Share,
    Notification, Report, FAQ, ContactMessage, Subscriber,
    SocialPostTemplate, ReferralTracking, QuickAddTracker
)
from django.contrib.auth import get_user_model

# ============================================================================
# MIXINS
# ============================================================================

class ReadOnlyMixin:
    """Make fields read-only after creation"""
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at',)
        return self.readonly_fields


class TimestampMixin:
    """Common timestamp display"""
    
    def get_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    get_created_at.short_description = 'Created'
    get_created_at.admin_order_field = 'created_at'


# ============================================================================
# PROFILE ADMIN
# ============================================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_avatar', 'profile_verified', 'get_journey_count', 'last_activity']
    list_filter = ['profile_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'bio', 'location']
    readonly_fields = ['created_at', 'last_activity', 'get_journey_count']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'image', 'bio', 'location')
        }),
        ('Social Connections', {
            'fields': ('tiktok_username', 'instagram_username', 'youtube_channel')
        }),
        ('Verification', {
            'fields': ('profile_verified',)
        }),
        ('Activity', {
            'fields': ('created_at', 'last_activity', 'get_journey_count')
        }),
    )
    
    def get_avatar(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />',
                obj.image.url
            )
        return '-'
    get_avatar.short_description = 'Avatar'
    
    def get_journey_count(self, obj):
        count = obj.journeys.count()
        url = reverse('admin:main_journey_changelist') + f'?creator__id={obj.id}'
        return format_html('<a href="{}">{} journeys</a>', url, count)
    get_journey_count.short_description = 'Journeys'


# ============================================================================
# SOCIAL CONNECTION ADMIN - KEPT (Critical)
# ============================================================================

@admin.register(SocialConnection)
class SocialConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'platform_username', 'auto_import', 'get_token_status', 'last_sync']
    list_filter = ['platform', 'auto_import', 'connected_at']
    search_fields = ['user__username', 'platform_username', 'platform_user_id']
    readonly_fields = ['connected_at', 'last_sync']
    
    fieldsets = (
        ('User & Platform', {
            'fields': ('user', 'platform', 'platform_user_id', 'platform_username')
        }),
        ('OAuth Tokens', {
            'fields': ('access_token', 'refresh_token', 'token_expires'),
            'classes': ('collapse',)
        }),
        ('Import Settings', {
            'fields': ('auto_import', 'import_hashtag')
        }),
        ('Metadata', {
            'fields': ('connected_at', 'last_sync')
        }),
    )
    
    def get_token_status(self, obj):
        if not obj.token_expires:
            return format_html('<span style="color: orange;">⚠️ No expiry</span>')
        if obj.is_token_expired():
            return format_html('<span style="color: red;">❌ Expired</span>')
        return format_html('<span style="color: green;">✅ Valid</span>')
    get_token_status.short_description = 'Token Status'


# ============================================================================
# IMPORTED CONTENT ADMIN - KEPT (Critical for Social-First)
# ============================================================================

@admin.register(ImportedContent)
class ImportedContentAdmin(admin.ModelAdmin):
    list_display = ['get_thumbnail', 'platform', 'get_caption_preview', 'status', 'detected_day', 'assigned_journey', 'imported_at']
    list_filter = ['platform', 'status', 'media_type', 'imported_at']
    search_fields = ['caption', 'platform_post_id', 'assigned_journey__title']
    readonly_fields = ['imported_at', 'processed_at', 'get_media_preview']
    actions = ['approve_selected', 'ignore_selected', 'assign_to_journey']
    
    fieldsets = (
        ('Source', {
            'fields': ('social_connection', 'platform', 'platform_post_id', 'platform_url')
        }),
        ('Content', {
            'fields': ('caption', 'media_type', 'get_media_preview', 'media_url', 'thumbnail_url')
        }),
        ('Platform Metadata', {
            'fields': ('posted_at', 'like_count', 'comment_count')
        }),
        ('Assignment - SOCIAL FIRST', {
            'fields': ('detected_day', 'assigned_journey', 'assigned_day', 'status')
        }),
        ('Result', {
            'fields': ('created_activity',)
        }),
        ('Timestamps', {
            'fields': ('imported_at', 'processed_at')
        }),
    )
    
    def get_thumbnail(self, obj):
        if obj.thumbnail_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;" />',
                obj.thumbnail_url
            )
        return '-'
    get_thumbnail.short_description = 'Thumbnail'
    
    def get_caption_preview(self, obj):
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    get_caption_preview.short_description = 'Caption'
    
    def get_media_preview(self, obj):
        if obj.media_type == 'image':
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 12px;" />',
                obj.media_url
            )
        elif obj.media_type == 'video':
            return format_html(
                '<video src="{}" controls style="max-width: 300px; max-height: 300px; border-radius: 12px;"></video>',
                obj.media_url
            )
        return '-'
    get_media_preview.short_description = 'Media Preview'
    
    def approve_selected(self, request, queryset):
        updated = queryset.update(status='approved', processed_at=timezone.now())
        self.message_user(request, f'{updated} items approved.')
    approve_selected.short_description = 'Approve selected items'
    
    def ignore_selected(self, request, queryset):
        updated = queryset.update(status='ignored', processed_at=timezone.now())
        self.message_user(request, f'{updated} items ignored.')
    ignore_selected.short_description = 'Ignore selected items'
    
    def assign_to_journey(self, request, queryset):
        """Bulk assign imported content to a journey"""
        # This would open a custom action form in a full implementation
        self.message_user(request, 'Use the detail view to assign to a journey.')
    assign_to_journey.short_description = 'Assign to journey (via detail view)'


# ============================================================================
# INLINE MODELS
# ============================================================================

class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ['day_number_field', 'content', 'is_video', 'source_platform', 'get_love_count', 'created_at']
    readonly_fields = ['day_number_field', 'get_love_count', 'created_at']
    show_change_link = True
    
    def get_love_count(self, obj):
        return obj.loves.count()
    get_love_count.short_description = '❤️'


class JourneyFollowInline(admin.TabularInline):
    model = JourneyFollow
    extra = 0
    fields = ['user', 'notify_on_activity', 'followed_at']
    readonly_fields = ['followed_at']


class JourneyTagInline(admin.TabularInline):
    model = JourneyTag
    extra = 1
    autocomplete_fields = ['tag']


# ============================================================================
# SOCIAL POST TEMPLATE INLINE - NEW (Social-First)
# ============================================================================

class SocialPostTemplateInline(admin.TabularInline):
    model = SocialPostTemplate
    extra = 0
    fields = ['platform', 'template_text', 'auto_post']
    show_change_link = True


# ============================================================================
# JOURNEY ADMIN - KEPT & ENHANCED
# ============================================================================

@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = ['get_cover', 'title', 'creator', 'category', 'journey_type', 'get_progress', 'get_social_stats', 'is_public', 'created_at']
    list_filter = ['category', 'journey_type', 'is_public', 'is_active', 'is_featured', 'auto_import_enabled', 'created_at']
    search_fields = ['title', 'description', 'creator__user__username', 'slug']
    readonly_fields = ['slug', 'view_count', 'unique_viewers', 'total_watch_time', 'created_at', 'updated_at', 'get_share_url']
    autocomplete_fields = ['creator']
    
    inlines = [ActivityInline, JourneyFollowInline, JourneyTagInline, SocialPostTemplateInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('creator', 'title', 'slug', 'description', 'category', 'journey_type', 'template_style')
        }),
        ('Visuals', {
            'fields': ('cover_image', 'cover_video')
        }),
        ('Structure', {
            'fields': ('duration', 'duration_unit', 'start_date', 'end_date', 'milestones', 'current_day_override')
        }),
        ('SOCIAL-FIRST SETTINGS', {
            'fields': ('auto_import_enabled', 'import_hashtag', 'social_share_url', 'auto_post_to_social', 'social_share_text'),
            'classes': ('wide',)
        }),
        ('Visibility', {
            'fields': ('is_public', 'is_active', 'is_featured', 'allow_comments')
        }),
        ('Social Analytics', {
            'fields': ('traffic_sources', 'social_engagement_stats'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'unique_viewers', 'total_watch_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at')
        }),
        ('Links', {
            'fields': ('get_share_url',)
        }),
    )
    
    def get_cover(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;" />',
                obj.cover_image.url
            )
        return '-'
    get_cover.short_description = 'Cover'
    
    def get_progress(self, obj):
        percentage = obj.get_progress_percentage()
        current = obj.get_current_day()
        return f"{current}/{obj.duration} ({percentage}%)"
    get_progress.short_description = 'Progress'
    
    def get_social_stats(self, obj):
        """Social-first stats display"""
        followers = obj.get_follower_count()
        shares = obj.get_share_count()
        traffic = obj.traffic_sources
        
        # Show top traffic source
        top_source = max(traffic.items(), key=lambda x: x[1])[0] if traffic else 'None'
        
        return format_html(
            '👥 {} · 🔄 {} · 📊 {}',
            followers,
            shares,
            top_source
        )
    get_social_stats.short_description = 'Social Stats'
    
    def get_share_url(self, obj):
        if obj.slug:
            url = obj.get_share_url()
            return format_html(
                '<a href="{}" target="_blank">{}</a> 🚀',
                url,
                url
            )
        return '-'
    get_share_url.short_description = 'Share URL'
    
    actions = ['make_featured', 'remove_featured', 'make_public', 'make_private', 'enable_auto_import']
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} journeys marked as featured.')
    make_featured.short_description = 'Mark as featured'
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} journeys removed from featured.')
    remove_featured.short_description = 'Remove from featured'
    
    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} journeys made public.')
    make_public.short_description = 'Make public'
    
    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} journeys made private.')
    make_private.short_description = 'Make private'
    
    def enable_auto_import(self, request, queryset):
        updated = queryset.update(auto_import_enabled=True)
        self.message_user(request, f'{updated} journeys have auto-import enabled.')
    enable_auto_import.short_description = 'Enable auto-import'


# ============================================================================
# ACTIVITY ADMIN - KEPT & ENHANCED
# ============================================================================

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['get_thumbnail', 'journey', 'day_number_field', 'get_content_preview', 'source_platform', 'is_video', 'get_social_engagement', 'created_at']
    list_filter = ['is_video', 'source_platform', 'created_at', 'journey__category']
    search_fields = ['content', 'journey__title', 'source_url']
    readonly_fields = ['day_number_field', 'view_count', 'created_at', 'published_at', 'get_media_preview']
    autocomplete_fields = ['journey', 'imported_from']
    
    fieldsets = (
        ('Journey', {
            'fields': ('journey', 'day_number_field', 'actual_date')
        }),
        ('Content', {
            'fields': ('content', 'file', 'is_video', 'thumbnail', 'get_media_preview')
        }),
        ('SOCIAL SOURCE', {
            'fields': ('imported_from', 'source_url', 'source_platform', 'social_post_id', 'embed_html'),
            'classes': ('wide',)
        }),
        ('Social Engagement', {
            'fields': ('social_engagement', 'is_cross_posted', 'cross_posted_at'),
            'classes': ('collapse',)
        }),
        ('Stats', {
            'fields': ('view_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'published_at')
        }),
    )
    
    def get_thumbnail(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;" />',
                obj.thumbnail.url
            )
        elif obj.file and not obj.is_video:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;" />',
                obj.file.url
            )
        # Social source thumbnail
        elif obj.imported_from and obj.imported_from.thumbnail_url:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 8px; object-fit: cover;" />',
                obj.imported_from.thumbnail_url
            )
        return '-'
    get_thumbnail.short_description = 'Media'
    
    def get_content_preview(self, obj):
        return obj.content[:40] + '...' if len(obj.content) > 40 else obj.content
    get_content_preview.short_description = 'Content'
    
    def get_social_engagement(self, obj):
        """Display social engagement stats"""
        if obj.social_engagement:
            likes = obj.social_engagement.get('likes', 0)
            comments = obj.social_engagement.get('comments', 0)
            return format_html('❤️ {} · 💬 {}', likes, comments)
        
        # Fallback to local engagement
        loves = obj.get_love_count()
        comments = obj.get_comment_count()
        return f'❤️ {loves} · 💬 {comments}'
    get_social_engagement.short_description = 'Engagement'
    
    def get_media_preview(self, obj):
        if obj.file:
            if obj.is_video:
                return format_html(
                    '<video src="{}" controls style="max-width: 400px; max-height: 400px; border-radius: 12px;"></video>',
                    obj.file.url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 12px;" />',
                    obj.file.url
                )
        elif obj.imported_from and obj.imported_from.media_url:
            if obj.imported_from.media_type == 'video':
                return format_html(
                    '<video src="{}" controls style="max-width: 400px; max-height: 400px; border-radius: 12px;"></video>',
                    obj.imported_from.media_url
                )
            else:
                return format_html(
                    '<img src="{}" style="max-width: 400px; max-height: 400px; border-radius: 12px;" />',
                    obj.imported_from.media_url
                )
        return '-'
    get_media_preview.short_description = 'Media Preview'


# ============================================================================
# SOCIAL POST TEMPLATE ADMIN - NEW
# ============================================================================

@admin.register(SocialPostTemplate)
class SocialPostTemplateAdmin(admin.ModelAdmin):
    list_display = ['journey', 'platform', 'template_preview', 'auto_post', 'created_at']
    list_filter = ['platform', 'auto_post']
    search_fields = ['journey__title', 'template_text']
    autocomplete_fields = ['journey']
    
    def template_preview(self, obj):
        preview = obj.template_text[:60] + '...' if len(obj.template_text) > 60 else obj.template_text
        return preview
    template_preview.short_description = 'Template'


# ============================================================================
# REFERRAL TRACKING ADMIN - NEW
# ============================================================================

@admin.register(ReferralTracking)
class ReferralTrackingAdmin(admin.ModelAdmin):
    list_display = ['journey', 'source', 'session_id', 'created_at']
    list_filter = ['source', 'created_at']
    search_fields = ['journey__title', 'session_id', 'ip_address']
    readonly_fields = ['created_at']
    autocomplete_fields = ['journey']


# ============================================================================
# QUICK ADD TRACKER ADMIN - NEW
# ============================================================================

@admin.register(QuickAddTracker)
class QuickAddTrackerAdmin(admin.ModelAdmin):
    list_display = ['journey', 'user', 'source_platform', 'detected_day', 'added_at']
    list_filter = ['source_platform', 'added_at']
    search_fields = ['journey__title', 'user__username']
    readonly_fields = ['added_at']
    autocomplete_fields = ['journey', 'user', 'created_activity']


# ============================================================================
# TAG ADMIN - KEPT
# ============================================================================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'get_journey_count', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'get_journey_count']
    
    def get_journey_count(self, obj):
        count = obj.journeys.count()
        url = reverse('admin:main_journey_changelist') + f'?tags__id={obj.id}'
        return format_html('<a href="{}">{} journeys</a>', url, count)
    get_journey_count.short_description = 'Journeys'


# ============================================================================
# ENGAGEMENT ADMINS - KEPT
# ============================================================================

@admin.register(JourneyFollow)
class JourneyFollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'notify_on_activity', 'followed_at']
    list_filter = ['notify_on_activity', 'followed_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['followed_at']
    autocomplete_fields = ['user', 'journey']


@admin.register(ActivityLove)
class ActivityLoveAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'activity__content', 'activity__journey__title']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'activity']


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_content_preview', 'activity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content', 'activity__journey__title']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'activity']
    
    def get_content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = 'Comment'


@admin.register(JourneySave)
class JourneySaveAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['saved_at']
    autocomplete_fields = ['user', 'journey']


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['journey', 'user', 'platform', 'created_at']
    list_filter = ['platform', 'created_at']
    search_fields = ['journey__title', 'user__username']
    readonly_fields = ['created_at']
    autocomplete_fields = ['journey', 'user']


# ============================================================================
# NOTIFICATION ADMIN - KEPT
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_message_preview', 'viewed', 'created_at']
    list_filter = ['viewed', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'journey']
    actions = ['mark_as_viewed', 'mark_as_unviewed']
    
    def get_message_preview(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    get_message_preview.short_description = 'Message'
    
    def mark_as_viewed(self, request, queryset):
        updated = queryset.update(viewed=True)
        self.message_user(request, f'{updated} notifications marked as viewed.')
    mark_as_viewed.short_description = 'Mark as viewed'
    
    def mark_as_unviewed(self, request, queryset):
        updated = queryset.update(viewed=False)
        self.message_user(request, f'{updated} notifications marked as unviewed.')
    mark_as_unviewed.short_description = 'Mark as unviewed'


# ============================================================================
# REPORT ADMIN - KEPT
# ============================================================================

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['get_reported_item', 'reported_by', 'reason', 'resolved', 'created_at']
    list_filter = ['reason', 'resolved', 'created_at']
    search_fields = ['reported_by__username', 'description', 'journey__title', 'activity__content']
    readonly_fields = ['created_at']
    autocomplete_fields = ['journey', 'activity', 'reported_by']
    actions = ['mark_resolved', 'mark_unresolved']
    
    fieldsets = (
        ('Report Info', {
            'fields': ('journey', 'activity', 'reported_by', 'reason', 'description')
        }),
        ('Status', {
            'fields': ('resolved', 'created_at')
        }),
    )
    
    def get_reported_item(self, obj):
        if obj.journey:
            return format_html('<a href="{}">{}</a>', 
                reverse('admin:main_journey_change', args=[obj.journey.id]),
                obj.journey.title)
        elif obj.activity:
            return f"Activity: {obj.activity.content[:30]}"
        return '-'
    get_reported_item.short_description = 'Reported Item'
    
    def mark_resolved(self, request, queryset):
        updated = queryset.update(resolved=True)
        self.message_user(request, f'{updated} reports marked as resolved.')
    mark_resolved.short_description = 'Mark as resolved'
    
    def mark_unresolved(self, request, queryset):
        updated = queryset.update(resolved=False)
        self.message_user(request, f'{updated} reports marked as unresolved.')
    mark_unresolved.short_description = 'Mark as unresolved'


# ============================================================================
# FAQ ADMIN - KEPT
# ============================================================================

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_active']
    
    fieldsets = (
        ('Content', {
            'fields': ('category', 'question', 'answer')
        }),
        ('Display', {
            'fields': ('order', 'is_active')
        }),
    )


# ============================================================================
# JOURNEY TAG ADMIN (THROUGH MODEL) - KEPT
# ============================================================================

@admin.register(JourneyTag)
class JourneyTagAdmin(admin.ModelAdmin):
    list_display = ['journey', 'tag', 'added_at']
    list_filter = ['added_at']
    search_fields = ['journey__title', 'tag__name']
    readonly_fields = ['added_at']
    autocomplete_fields = ['journey', 'tag']


# ============================================================================
# CONTACT MESSAGE ADMIN - KEPT
# ============================================================================

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['created_at', 'ip_address']
    ordering = ['-created_at']


# ============================================================================
# SUBSCRIBER ADMIN - KEPT
# ============================================================================

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at', 'ip_address']
    search_fields = ['email']
    readonly_fields = ['subscribed_at', 'ip_address', 'user_agent']
    ordering = ['-subscribed_at']


# ============================================================================
# DASHBOARD CUSTOMIZATION
# ============================================================================

admin.site.site_header = 'Rallynex Administration'
admin.site.site_title = 'Rallynex Admin'
admin.site.index_title = 'Journey Organizer Dashboard - Social First'


# ============================================================================
# COMMENTED OUT / REMOVED (Not Social-First Focused)
# ============================================================================

"""
# REMOVED: Donation - Not core to social-first
@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    ...

# REMOVED: PostJourneyProduct - Not core to social-first
@admin.register(PostJourneyProduct)
class PostJourneyProductAdmin(admin.ModelAdmin):
    ...

# REMOVED: JourneyTemplate - Not core to social-first
@admin.register(JourneyTemplate)
class JourneyTemplateAdmin(admin.ModelAdmin):
    ...

# REMOVED: Funding-related fields from JourneyAdmin
# 'funding_enabled', 'funding_goal', 'funding_description' removed from fieldsets
"""