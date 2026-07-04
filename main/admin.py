from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from . import models


# ============================================================================
# CUSTOM ADMIN SITE
# ============================================================================

class RallynexAdminSite(admin.AdminSite):
    """Custom admin site with Rallynex branding"""
    site_header = "Rallynex Admin"
    site_title = "Rallynex Documentation Platform"
    index_title = "Documentation Management"
    
    def get_app_list(self, request):
        """Customize app list for cleaner display"""
        app_list = super().get_app_list(request)
        
        # Reorder apps for documentation focus
        for app in app_list:
            if app['app_label'] == 'main':
                # Rename models for clarity
                model_mapping = {
                    'Journeys': 'Journeys & Documentation',
                    'Profiles': 'Users & Profiles',
                    'Activities': 'Journal Entries',
                    'Journal entries': 'Free-form Journals',
                    'Notifications': 'Notifications',
                    'Comments': 'Comments & Feedback',
                }
                for model in app.get('models', []):
                    if model.get('name') in model_mapping:
                        model['name'] = model_mapping[model['name']]
        
        return app_list


# Initialize custom admin site
admin_site = RallynexAdminSite(name='rallynex_admin')


# ============================================================================
# INLINE ADMIN CLASSES
# ============================================================================

class ActivityInline(admin.TabularInline):
    """Inline activities for journey admin"""
    model = models.Activity
    fields = (
        'day_number_field', 
        'title', 
        'content_preview', 
        'mood', 
        'is_published',
        'created_at'
    )
    readonly_fields = ('content_preview', 'created_at', 'updated_at')
    extra = 0
    ordering = ['-day_number_field']
    show_change_link = True
    can_delete = True
    max_num = 0
    
    def content_preview(self, obj):
        """Show truncated content preview"""
        if obj.content:
            return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
        return '-'
    content_preview.short_description = 'Content Preview'


class JourneyTagInline(admin.TabularInline):
    """Inline tags for journey admin"""
    model = models.JourneyTag
    extra = 1
    autocomplete_fields = ['tag']


class JourneyFollowInline(admin.TabularInline):
    """Inline followers for journey admin"""
    model = models.JourneyFollow
    fields = ('user', 'followed_at')
    readonly_fields = ('followed_at',)
    extra = 0
    can_delete = True
    show_change_link = True


class CommentInline(admin.TabularInline):
    """Inline comments for journey admin"""
    model = models.Comment
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    can_delete = True
    show_change_link = True


# ============================================================================
# MODEL ADMIN CLASSES
# ============================================================================

@admin.register(models.Profile, site=admin_site)
class ProfileAdmin(admin.ModelAdmin):
    """Admin for user profiles"""
    
    list_display = (
        'user', 
        'get_display_name', 
        'get_journey_count', 
        'get_total_entries',
        'location',
        'created_at'
    )
    
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'bio', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'image', 'bio', 'location')
        }),
        ('Social Links (Optional)', {
            'fields': ('website', 'twitter', 'instagram'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_display_name(self, obj):
        return obj.get_display_name()
    get_display_name.short_description = 'Display Name'
    get_display_name.admin_order_field = 'user__username'
    
    def get_journey_count(self, obj):
        return obj.journeys.count()
    get_journey_count.short_description = 'Journeys'
    
    def get_total_entries(self, obj):
        return models.Activity.objects.filter(journey__creator=obj).count()
    get_total_entries.short_description = 'Total Entries'


@admin.register(models.Journey, site=admin_site)
class JourneyAdmin(admin.ModelAdmin):
    """Admin for journeys — documentation focus"""
    
    list_display = (
        'title',
        'creator_display',
        'journey_type',
        'category',
        'progress_display',
        'entry_count',
        'privacy_status',
        'is_active',
        'created_at'
    )
    
    list_filter = (
        'journey_type',
        'category',
        'privacy_status',
        'is_active',
        'is_featured',
        'is_archived',
        'created_at',
        ('creator', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'title', 
        'slug', 
        'description',
        'creator__user__username',
        'creator__user__first_name',
        'creator__user__last_name'
    )
    
    readonly_fields = (
        'slug', 
        'created_at', 
        'updated_at',
        'activity_count',
        'follower_count',
        'save_count'
    )
    
    prepopulated_fields = {'slug': ('title',)}
    
    inlines = [ActivityInline, JourneyTagInline, JourneyFollowInline, CommentInline]
    
    actions = [
        'make_public',
        'make_private',
        'make_unlisted',
        'mark_featured',
        'unmark_featured',
        'archive_journeys',
        'activate_journeys',
        'export_journey_data'
    ]
    
    fieldsets = (
        ('Essential Information', {
            'fields': (
                'creator',
                'title',
                'slug',
                'description',
                'category',
                'journey_type'
            )
        }),
        ('Structure', {
            'fields': (
                'duration',
                'current_day_override',
                'milestones',
                'start_date',
                'end_date'
            )
        }),
        ('Visuals', {
            'fields': ('cover_image',),
            'classes': ('collapse',)
        }),
        ('Privacy & Settings', {
            'fields': (
                'privacy_status',
                'allow_comments'
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_featured',
                'is_archived'
            )
        }),
        ('Statistics', {
            'fields': (
                'activity_count',
                'follower_count',
                'save_count'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # ==================== CUSTOM METHODS ====================
    
    def creator_display(self, obj):
        """Display creator name with link to profile"""
        return format_html(
            '<a href="{}">{}</a>',
            f'/admin/main/profile/{obj.creator.pk}/change/',
            obj.creator.get_display_name()
        )
    creator_display.short_description = 'Creator'
    creator_display.admin_order_field = 'creator__user__username'
    
    def progress_display(self, obj):
        """Display progress as a progress bar"""
        progress = obj.get_progress_percentage()
        color = '#10b981' if progress >= 100 else '#3b82f6' if progress >= 50 else '#f59e0b'
        return format_html(
            '<div style="background: #f3f4f6; border-radius: 4px; padding: 2px; min-width: 80px;">'
            '<div style="background: {}; width: {}%; border-radius: 4px; padding: 2px 4px; '
            'text-align: center; color: white; font-size: 11px; font-weight: 500;">{}%</div>'
            '</div>',
            color,
            progress,
            progress
        )
    progress_display.short_description = 'Progress'
    
    def entry_count(self, obj):
        """Count of entries in this journey"""
        return obj.activities.count()
    entry_count.short_description = 'Entries'
    
    def activity_count(self, obj):
        """Statistics display for readonly field"""
        return obj.activities.count()
    activity_count.short_description = 'Total Entries'
    
    def follower_count(self, obj):
        """Follower count"""
        return obj.followers.count()
    follower_count.short_description = 'Followers'
    
    def save_count(self, obj):
        """Save/bookmark count"""
        return obj.saves.count()
    save_count.short_description = 'Saves'
    
    # ==================== CUSTOM ACTIONS ====================
    
    def make_public(self, request, queryset):
        """Make selected journeys public"""
        updated = queryset.update(privacy_status='public', is_active=True)
        self.message_user(request, f'{updated} journey(s) set to public.')
    make_public.short_description = 'Set to Public'
    
    def make_private(self, request, queryset):
        """Make selected journeys private"""
        updated = queryset.update(privacy_status='private')
        self.message_user(request, f'{updated} journey(s) set to private.')
    make_private.short_description = 'Set to Private'
    
    def make_unlisted(self, request, queryset):
        """Make selected journeys unlisted"""
        updated = queryset.update(privacy_status='unlisted')
        self.message_user(request, f'{updated} journey(s) set to unlisted.')
    make_unlisted.short_description = 'Set to Unlisted'
    
    def mark_featured(self, request, queryset):
        """Mark selected journeys as featured"""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} journey(s) marked as featured.')
    mark_featured.short_description = 'Mark as Featured'
    
    def unmark_featured(self, request, queryset):
        """Unmark selected journeys as featured"""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} journey(s) unmarked as featured.')
    unmark_featured.short_description = 'Unmark as Featured'
    
    def archive_journeys(self, request, queryset):
        """Archive selected journeys"""
        updated = queryset.update(is_archived=True, is_active=False)
        self.message_user(request, f'{updated} journey(s) archived.')
    archive_journeys.short_description = 'Archive Journeys'
    
    def activate_journeys(self, request, queryset):
        """Activate selected journeys"""
        updated = queryset.update(is_active=True, is_archived=False)
        self.message_user(request, f'{updated} journey(s) activated.')
    activate_journeys.short_description = 'Activate Journeys'
    
    def export_journey_data(self, request, queryset):
        """Export journey data (placeholder)"""
        count = queryset.count()
        self.message_user(request, f'Export started for {count} journey(s). Download will be ready soon.')
    export_journey_data.short_description = 'Export Journey Data'


@admin.register(models.Activity, site=admin_site)
class ActivityAdmin(admin.ModelAdmin):
    """Admin for journey entries"""
    
    list_display = (
        'journey_title',
        'day_number_field',
        'title_display',
        'content_preview',
        'mood',
        'actual_date',
        'is_published',
        'created_at'
    )
    
    list_filter = (
        'mood',
        'is_published',
        'is_draft',
        'created_at',
        'actual_date',
        ('journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'title',
        'content',
        'summary',
        'journey__title',
        'journey__creator__user__username'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    
    fieldsets = (
        ('Entry Content', {
            'fields': (
                'journey',
                'day_number_field',
                'title',
                'content',
                'summary'
            )
        }),
        ('Media', {
            'fields': ('media_file', 'thumbnail', 'media_caption'),
            'classes': ('collapse',)
        }),
        ('Mood & Metrics', {
            'fields': ('mood', 'progress_metrics', 'location'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_published', 'is_draft', 'actual_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'publish_entries',
        'unpublish_entries',
        'mark_as_draft',
        'mark_as_published'
    ]
    
    # ==================== CUSTOM METHODS ====================
    
    def journey_title(self, obj):
        """Display journey title with link"""
        return format_html(
            '<a href="{}">{}</a>',
            f'/admin/main/journey/{obj.journey.pk}/change/',
            obj.journey.title
        )
    journey_title.short_description = 'Journey'
    journey_title.admin_order_field = 'journey__title'
    
    def title_display(self, obj):
        """Display title or day number"""
        return obj.title or f'Day {obj.day_number_field}'
    title_display.short_description = 'Title'
    
    def content_preview(self, obj):
        """Preview of content"""
        if obj.content:
            return obj.content[:60] + ('...' if len(obj.content) > 60 else '')
        return '-'
    content_preview.short_description = 'Content'
    
    # ==================== CUSTOM ACTIONS ====================
    
    def publish_entries(self, request, queryset):
        """Publish selected entries"""
        updated = queryset.update(is_published=True, is_draft=False)
        self.message_user(request, f'{updated} entry(s) published.')
    publish_entries.short_description = 'Publish Entries'
    
    def unpublish_entries(self, request, queryset):
        """Unpublish selected entries"""
        updated = queryset.update(is_published=False)
        self.message_user(request, f'{updated} entry(s) unpublished.')
    unpublish_entries.short_description = 'Unpublish Entries'
    
    def mark_as_draft(self, request, queryset):
        """Mark selected entries as draft"""
        updated = queryset.update(is_draft=True, is_published=False)
        self.message_user(request, f'{updated} entry(s) marked as draft.')
    mark_as_draft.short_description = 'Mark as Draft'
    
    def mark_as_published(self, request, queryset):
        """Mark selected entries as published"""
        updated = queryset.update(is_published=True, is_draft=False)
        self.message_user(request, f'{updated} entry(s) marked as published.')
    mark_as_published.short_description = 'Mark as Published'


@admin.register(models.JournalEntry, site=admin_site)
class JournalEntryAdmin(admin.ModelAdmin):
    """Admin for free-form journal entries"""
    
    list_display = (
        'user',
        'title_display',
        'content_preview',
        'related_journey',
        'is_private',
        'mood',
        'created_at'
    )
    
    list_filter = (
        'is_private',
        'mood',
        'created_at',
        'updated_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('related_journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'title',
        'content',
        'user__username',
        'user__first_name',
        'user__last_name',
        'tags'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Content', {
            'fields': ('user', 'title', 'content', 'media_files', 'tags')
        }),
        ('Context', {
            'fields': ('related_journey', 'related_activity', 'location')
        }),
        ('Privacy & Mood', {
            'fields': ('is_private', 'mood')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # ==================== CUSTOM METHODS ====================
    
    def title_display(self, obj):
        """Display truncated title"""
        return obj.title[:50] + ('...' if len(obj.title) > 50 else '')
    title_display.short_description = 'Title'
    
    def content_preview(self, obj):
        """Preview of content"""
        return obj.content[:60] + ('...' if len(obj.content) > 60 else '')
    content_preview.short_description = 'Content'


@admin.register(models.SocialPublish, site=admin_site)
class SocialPublishAdmin(admin.ModelAdmin):
    """Admin for social publishing — optional sharing"""
    
    list_display = (
        'user',
        'journey',
        'platform',
        'status',
        'published_at',
        'created_at'
    )
    
    list_filter = (
        'platform',
        'status',
        'created_at',
        'published_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'share_text',
        'user__username',
        'journey__title',
        'publish_id'
    )
    
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    
    fieldsets = (
        ('Publishing Information', {
            'fields': ('user', 'journey', 'activity', 'platform')
        }),
        ('Content', {
            'fields': ('share_text', 'share_image')
        }),
        ('Status', {
            'fields': ('status', 'publish_url', 'publish_id', 'scheduled_at', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'publish_now',
        'approve_publish',
        'reject_publish'
    ]
    
    # ==================== CUSTOM ACTIONS ====================
    
    def publish_now(self, request, queryset):
        """Publish selected items immediately"""
        updated = queryset.update(status='published', published_at=timezone.now())
        self.message_user(request, f'{updated} item(s) published.')
    publish_now.short_description = 'Publish Now'
    
    def approve_publish(self, request, queryset):
        """Approve selected items for publishing"""
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} item(s) approved for publishing.')
    approve_publish.short_description = 'Approve for Publishing'
    
    def reject_publish(self, request, queryset):
        """Reject selected items"""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} item(s) rejected.')
    reject_publish.short_description = 'Reject'


@admin.register(models.Comment, site=admin_site)
class CommentAdmin(admin.ModelAdmin):
    """Admin for comments"""
    
    list_display = (
        'user',
        'content_preview',
        'journey_display',
        'activity_display',
        'created_at'
    )
    
    list_filter = (
        'created_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('journey', admin.RelatedOnlyFieldListFilter),
        ('activity', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'content',
        'user__username',
        'journey__title'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Comment', {
            'fields': ('user', 'content', 'journey', 'activity')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['delete_comments']
    
    # ==================== CUSTOM METHODS ====================
    
    def content_preview(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_preview.short_description = 'Content'
    
    def journey_display(self, obj):
        if obj.journey:
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/main/journey/{obj.journey.pk}/change/',
                obj.journey.title
            )
        return '-'
    journey_display.short_description = 'Journey'
    
    def activity_display(self, obj):
        if obj.activity:
            return f'Day {obj.activity.day_number_field}'
        return '-'
    activity_display.short_description = 'Activity'
    
    # ==================== CUSTOM ACTIONS ====================
    
    def delete_comments(self, request, queryset):
        """Delete selected comments"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} comment(s) deleted.')
    delete_comments.short_description = 'Delete Selected Comments'


@admin.register(models.Notification, site=admin_site)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for notifications — minimal"""
    
    list_display = (
        'user',
        'notification_type',
        'message_preview',
        'is_read',
        'created_at'
    )
    
    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
        ('user', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'message',
        'user__username'
    )
    
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Notification', {
            'fields': (
                'user',
                'notification_type',
                'message',
                'redirect_link',
                'related_journey',
                'related_activity'
            )
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'delete_notifications']
    
    # ==================== CUSTOM METHODS ====================
    
    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Message'
    
    # ==================== CUSTOM ACTIONS ====================
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')
    mark_as_read.short_description = 'Mark as Read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notification(s) marked as unread.')
    mark_as_unread.short_description = 'Mark as Unread'
    
    def delete_notifications(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} notification(s) deleted.')
    delete_notifications.short_description = 'Delete Notifications'


@admin.register(models.JourneyFollow, site=admin_site)
class JourneyFollowAdmin(admin.ModelAdmin):
    """Admin for journey followers"""
    
    list_display = (
        'user',
        'journey',
        'notify_on_new_entry',
        'followed_at'
    )
    
    list_filter = (
        'notify_on_new_entry',
        'followed_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'user__username',
        'journey__title'
    )
    
    readonly_fields = ('followed_at',)


@admin.register(models.JourneySave, site=admin_site)
class JourneySaveAdmin(admin.ModelAdmin):
    """Admin for journey saves/bookmarks"""
    
    list_display = (
        'user',
        'journey',
        'saved_at'
    )
    
    list_filter = (
        'saved_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'user__username',
        'journey__title'
    )
    
    readonly_fields = ('saved_at',)


@admin.register(models.Tag, site=admin_site)
class TagAdmin(admin.ModelAdmin):
    """Admin for tags"""
    
    list_display = ('name', 'slug', 'journey_count', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    def journey_count(self, obj):
        return obj.journeys.count()
    journey_count.short_description = 'Journeys'


@admin.register(models.Export, site=admin_site)
class ExportAdmin(admin.ModelAdmin):
    """Admin for exports"""
    
    list_display = (
        'user',
        'journey',
        'format',
        'status',
        'file_size_display',
        'requested_at',
        'completed_at'
    )
    
    list_filter = (
        'format',
        'status',
        'requested_at',
        'completed_at',
        ('user', admin.RelatedOnlyFieldListFilter),
        ('journey', admin.RelatedOnlyFieldListFilter),
    )
    
    search_fields = (
        'user__username',
        'journey__title'
    )
    
    readonly_fields = (
        'requested_at',
        'completed_at',
        'file_size',
        'file_url'
    )
    
    fieldsets = (
        ('Export Information', {
            'fields': ('user', 'journey', 'format')
        }),
        ('Options', {
            'fields': ('include_media', 'include_comments')
        }),
        ('Status', {
            'fields': ('status', 'file_url', 'file_size', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['retry_export', 'delete_exports']
    
    # ==================== CUSTOM METHODS ====================
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f'{obj.file_size} B'
            elif obj.file_size < 1048576:
                return f'{obj.file_size / 1024:.1f} KB'
            else:
                return f'{obj.file_size / 1048576:.1f} MB'
        return '-'
    file_size_display.short_description = 'File Size'
    
    # ==================== CUSTOM ACTIONS ====================
    
    def retry_export(self, request, queryset):
        """Retry failed exports"""
        updated = queryset.filter(status='failed').update(status='pending')
        self.message_user(request, f'{updated} export(s) queued for retry.')
    retry_export.short_description = 'Retry Failed Exports'
    
    def delete_exports(self, request, queryset):
        """Delete selected exports"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} export(s) deleted.')
    delete_exports.short_description = 'Delete Exports'


@admin.register(models.ContactMessage, site=admin_site)
class ContactMessageAdmin(admin.ModelAdmin):
    """Admin for contact messages"""
    
    list_display = ('name', 'email', 'subject', 'user', 'created_at')
    list_filter = ('created_at', 'subject')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)


@admin.register(models.Subscriber, site=admin_site)
class SubscriberAdmin(admin.ModelAdmin):
    """Admin for email subscribers"""
    
    list_display = ('email', 'subscribed_at')
    list_filter = ('subscribed_at',)
    search_fields = ('email',)
    readonly_fields = ('subscribed_at',)


# ============================================================================
# REGISTER WITH DEFAULT ADMIN SITE (Fallback)
# ============================================================================

# Also register with default admin site
admin.site.register(models.Profile, ProfileAdmin)
admin.site.register(models.Journey, JourneyAdmin)
admin.site.register(models.Activity, ActivityAdmin)
admin.site.register(models.JournalEntry, JournalEntryAdmin)
admin.site.register(models.SocialPublish, SocialPublishAdmin)
admin.site.register(models.Comment, CommentAdmin)
admin.site.register(models.Notification, NotificationAdmin)
admin.site.register(models.JourneyFollow, JourneyFollowAdmin)
admin.site.register(models.JourneySave, JourneySaveAdmin)
admin.site.register(models.Tag, TagAdmin)
admin.site.register(models.Export, ExportAdmin)
admin.site.register(models.ContactMessage, ContactMessageAdmin)
admin.site.register(models.Subscriber, SubscriberAdmin)