from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import (
    Profile, SocialConnection, ImportedContent,
    Journey, Activity, JourneyFollow, Tag, JourneyTag,
    ActivityLove, ActivityComment, JourneySave, Share,
    Donation, Notification, PostJourneyProduct,
    Report, Blog, FAQ, JourneyTemplate
)


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
        ('Verification & Payments', {
            'fields': ('profile_verified', 'paypal_email')
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
# SOCIAL CONNECTION ADMIN
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
# IMPORTED CONTENT ADMIN
# ============================================================================

@admin.register(ImportedContent)
class ImportedContentAdmin(admin.ModelAdmin):
    list_display = ['get_thumbnail', 'platform', 'get_caption_preview', 'status', 'detected_day', 'assigned_journey', 'imported_at']
    list_filter = ['platform', 'status', 'media_type', 'imported_at']
    search_fields = ['caption', 'platform_post_id', 'assigned_journey__title']
    readonly_fields = ['imported_at', 'processed_at', 'get_media_preview']
    actions = ['approve_selected', 'ignore_selected']
    
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
        ('Assignment', {
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


# ============================================================================
# INLINE MODELS
# ============================================================================

class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ['day_number_field', 'content', 'is_video', 'get_love_count', 'created_at']
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


class DonationInline(admin.TabularInline):
    model = Donation
    extra = 0
    fields = ['donor_name', 'amount', 'status', 'created_at']
    readonly_fields = ['created_at']


class JourneyTagInline(admin.TabularInline):
    model = JourneyTag
    extra = 1
    autocomplete_fields = ['tag']


# ============================================================================
# JOURNEY ADMIN
# ============================================================================

@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = ['get_cover', 'title', 'creator', 'category', 'journey_type', 'get_progress', 'get_stats', 'is_public', 'created_at']
    list_filter = ['category', 'journey_type', 'is_public', 'is_active', 'is_featured', 'funding_enabled', 'created_at']
    search_fields = ['title', 'description', 'creator__user__username', 'slug']
    readonly_fields = ['slug', 'view_count', 'unique_viewers', 'total_watch_time', 'created_at', 'updated_at', 'get_absolute_url']
    autocomplete_fields = ['creator']
    
    inlines = [ActivityInline, JourneyFollowInline, DonationInline, JourneyTagInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('creator', 'title', 'slug', 'description', 'category', 'journey_type', 'template_style')
        }),
        ('Visuals', {
            'fields': ('cover_image', 'cover_video')
        }),
        ('Structure', {
            'fields': ('duration', 'duration_unit', 'start_date', 'end_date', 'milestones')
        }),
        ('Settings', {
            'fields': ('is_public', 'is_active', 'is_featured', 'allow_comments', 'auto_import_enabled', 'import_hashtag')
        }),
        ('Funding', {
            'fields': ('funding_enabled', 'funding_goal', 'funding_description'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'unique_viewers', 'total_watch_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at')
        }),
        ('Links', {
            'fields': ('get_absolute_url',)
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
    
    def get_stats(self, obj):
        followers = obj.get_follower_count()
        loves = obj.get_love_count()
        return format_html('👥 {} · ❤️ {}', followers, loves)
    get_stats.short_description = 'Stats'
    
    def get_absolute_url(self, obj):
        if obj.slug:
            url = reverse('journey_detail', kwargs={'slug': obj.slug})
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return '-'
    get_absolute_url.short_description = 'Public URL'
    
    actions = ['make_featured', 'remove_featured', 'make_public', 'make_private']
    
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


# ============================================================================
# JOURNEY TEMPLATE ADMIN
# ============================================================================

@admin.register(JourneyTemplate)
class JourneyTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'template_style', 'price', 'is_free', 'usage_count', 'is_active')
    list_filter = ('category', 'template_style', 'is_free', 'is_active')
    search_fields = ('title', 'description')


# ============================================================================
# ACTIVITY ADMIN
# ============================================================================

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['get_thumbnail', 'journey', 'day_number_field', 'get_content_preview', 'is_video', 'get_engagement', 'created_at']
    list_filter = ['is_video', 'created_at', 'journey__category']
    search_fields = ['content', 'journey__title']
    readonly_fields = ['day_number_field', 'view_count', 'created_at', 'published_at', 'get_media_preview']
    autocomplete_fields = ['journey']
    
    fieldsets = (
        ('Journey', {
            'fields': ('journey', 'day_number_field')
        }),
        ('Content', {
            'fields': ('content', 'file', 'is_video', 'thumbnail', 'get_media_preview')
        }),
        ('Source', {
            'fields': ('imported_from', 'source_url')
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
        return '-'
    get_thumbnail.short_description = 'Media'
    
    def get_content_preview(self, obj):
        return obj.content[:40] + '...' if len(obj.content) > 40 else obj.content
    get_content_preview.short_description = 'Content'
    
    def get_engagement(self, obj):
        loves = obj.get_love_count()
        comments = obj.get_comment_count()
        return f'❤️ {loves} · 💬 {comments}'
    get_engagement.short_description = 'Engagement'
    
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
        return '-'
    get_media_preview.short_description = 'Media Preview'


# ============================================================================
# TAG ADMIN
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
# ENGAGEMENT ADMINS
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
# DONATION ADMIN
# ============================================================================

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['journey', 'get_donor', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['journey__title', 'donor__username', 'donor_name', 'donor_email', 'paypal_order_id']
    readonly_fields = ['created_at', 'completed_at']
    autocomplete_fields = ['journey', 'donor']
    actions = ['mark_completed', 'mark_failed']
    
    fieldsets = (
        ('Donation Info', {
            'fields': ('journey', 'amount', 'message')
        }),
        ('Donor Info', {
            'fields': ('donor', 'donor_name', 'donor_email')
        }),
        ('Status', {
            'fields': ('status', 'paypal_order_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at')
        }),
    )
    
    def get_donor(self, obj):
        if obj.donor:
            return obj.donor.username
        return obj.donor_name or 'Anonymous'
    get_donor.short_description = 'Donor'
    get_donor.admin_order_field = 'donor__username'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} donations marked as completed.')
    mark_completed.short_description = 'Mark as completed'
    
    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} donations marked as failed.')
    mark_failed.short_description = 'Mark as failed'


# ============================================================================
# NOTIFICATION ADMIN
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
# POST-JOURNEY PRODUCT ADMIN
# ============================================================================

@admin.register(PostJourneyProduct)
class PostJourneyProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'journey', 'product_type', 'price', 'is_active', 'created_at']
    list_filter = ['product_type', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'journey__title']
    readonly_fields = ['created_at']
    autocomplete_fields = ['journey']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('journey', 'product_type', 'title', 'description', 'price')
        }),
        ('Files', {
            'fields': ('pdf_file', 'video_file')
        }),
        ('Coaching', {
            'fields': ('coaching_calendar_link', 'coaching_duration')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )


# ============================================================================
# REPORT ADMIN
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
# BLOG ADMIN
# ============================================================================

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'view_count', 'published_at', 'created_at']
    list_filter = ['category', 'status', 'created_at', 'published_at']
    search_fields = ['title', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['view_count', 'created_at', 'updated_at']
    autocomplete_fields = ['author']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'excerpt', 'content')
        }),
        ('Media', {
            'fields': ('featured_image',)
        }),
        ('Meta', {
            'fields': ('author', 'category', 'status')
        }),
        ('Stats', {
            'fields': ('view_count',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at')
        }),
    )
    
    actions = ['publish_selected', 'archive_selected']
    
    def publish_selected(self, request, queryset):
        updated = queryset.update(status='published', published_at=timezone.now())
        self.message_user(request, f'{updated} blog posts published.')
    publish_selected.short_description = 'Publish selected'
    
    def archive_selected(self, request, queryset):
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} blog posts archived.')
    archive_selected.short_description = 'Archive selected'


# ============================================================================
# FAQ ADMIN
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
# JOURNEY TAG ADMIN (THROUGH MODEL)
# ============================================================================

@admin.register(JourneyTag)
class JourneyTagAdmin(admin.ModelAdmin):
    list_display = ['journey', 'tag', 'added_at']
    list_filter = ['added_at']
    search_fields = ['journey__title', 'tag__name']
    readonly_fields = ['added_at']
    autocomplete_fields = ['journey', 'tag']


# ============================================================================
# DASHBOARD CUSTOMIZATION
# ============================================================================

admin.site.site_header = 'Rallynex Administration'
admin.site.site_title = 'Rallynex Admin'
admin.site.index_title = 'Journey Organizer Dashboard'