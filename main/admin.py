from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Profile,
    Journey,
    Activity,
    Reflection,
    SocialPublish,
    Notification,
    Comment,
    JourneyFollow,
    JourneySave,
    Tag,
    JourneyTag,
    Export,
    ContactMessage,
    Subscriber,
)


# ============================================================================
# PROFILE ADMIN
# ============================================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_display_name', 'location', 'get_journey_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'bio', 'location']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'image', 'bio', 'location')
        }),
        ('Social Links', {
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
    
    def get_journey_count(self, obj):
        return obj.get_journey_count()
    get_journey_count.short_description = 'Journeys'


# ============================================================================
# JOURNEY ADMIN
# ============================================================================

class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 1
    fields = ['day_number_field', 'title', 'content', 'mood', 'activity_type', 'is_published']
    readonly_fields = ['created_at', 'updated_at']


class ReflectionInline(admin.TabularInline):
    model = Reflection
    extra = 0
    fields = ['summary', 'reflection_type', 'mood', 'is_private']
    readonly_fields = ['created_at']


class JourneyTagInline(admin.TabularInline):
    model = JourneyTag
    extra = 1
    fields = ['tag']


@admin.register(Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'creator', 'category', 'journey_type', 'get_progress',
        'privacy_status', 'is_active', 'is_featured', 'view_count', 'created_at'
    ]
    list_filter = [
        'category', 'journey_type', 'privacy_status', 'is_active', 'is_featured', 
        'is_archived', 'allow_comments', 'created_at'
    ]
    search_fields = [
        'title', 'slug', 'description', 'creator__user__username', 
        'creator__user__email', 'fitness_goal', 'wellness_focus', 'custom_goal'
    ]
    readonly_fields = [
        'slug', 'view_count', 'unique_viewers', 'created_at', 'updated_at',
        'get_absolute_url_display', 'get_activities_count', 'get_reflections_count'
    ]
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ActivityInline, ReflectionInline, JourneyTagInline]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'creator', 'title', 'slug', 'description', 'category', 'journey_type'
            )
        }),
        ('Goals & Focus', {
            'fields': (
                'fitness_goal', 'wellness_focus', 'custom_goal'
            ),
            'classes': ('collapse',)
        }),
        ('Visuals & Style', {
            'fields': ('cover_image', 'template_style')
        }),
        ('Structure', {
            'fields': ('duration', 'current_day_override', 'start_date', 'end_date')
        }),
        ('Privacy & Settings', {
            'fields': ('privacy_status', 'allow_comments')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_archived')
        }),
        ('Analytics', {
            'fields': ('view_count', 'unique_viewers', 'get_activities_count', 'get_reflections_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_progress(self, obj):
        progress = obj.get_progress_percentage()
        return format_html(
            '<div style="width:100px; background:#f0f0f0; border-radius:10px; overflow:hidden;">'
            '<div style="width:{}%; background:#3b82f6; color:white; text-align:center; font-size:10px; padding:2px 0;">{}%</div>'
            '</div>',
            progress, progress
        )
    get_progress.short_description = 'Progress'
    
    def get_absolute_url_display(self, obj):
        return format_html(
            '<a href="{}" target="_blank">View on Site</a>',
            obj.get_absolute_url()
        )
    get_absolute_url_display.short_description = 'URL'
    
    def get_activities_count(self, obj):
        return obj.activities.count()
    get_activities_count.short_description = 'Activities'
    
    def get_reflections_count(self, obj):
        return obj.reflections.count()
    get_reflections_count.short_description = 'Reflections'
    
    actions = ['mark_featured', 'unmark_featured', 'make_public', 'make_private', 'archive_journeys']
    
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)
    mark_featured.short_description = 'Mark selected as featured'
    
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)
    unmark_featured.short_description = 'Unmark featured'
    
    def make_public(self, request, queryset):
        queryset.update(privacy_status='public')
    make_public.short_description = 'Make selected public'
    
    def make_private(self, request, queryset):
        queryset.update(privacy_status='private')
    make_private.short_description = 'Make selected private'
    
    def archive_journeys(self, request, queryset):
        queryset.update(is_archived=True, is_active=False)
    archive_journeys.short_description = 'Archive selected journeys'


# ============================================================================
# ACTIVITY ADMIN
# ============================================================================

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'journey', 'day_number_field', 'get_date_display', 
        'mood', 'activity_type', 'is_published', 'created_at'
    ]
    list_filter = [
        'journey', 'mood', 'activity_type', 'intensity', 'is_published', 
        'is_draft', 'created_at'
    ]
    search_fields = [
        'title', 'content', 'summary', 'journey__title', 'journey__creator__user__username'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'published_at', 'get_display_html_preview',
        'get_formatted_metrics_display'
    ]
    fieldsets = (
        ('Journey & Day', {
            'fields': ('journey', 'day_number_field', 'actual_date')
        }),
        ('Content', {
            'fields': ('title', 'content', 'summary')
        }),
        ('Workout Details', {
            'fields': ('activity_type', 'duration_minutes', 'intensity'),
            'classes': ('collapse',)
        }),
        ('Mood & Metrics', {
            'fields': ('mood', 'progress_metrics', 'get_formatted_metrics_display'),
        }),
        ('Media', {
            'fields': ('media_file', 'is_video', 'thumbnail', 'media_caption'),
            'classes': ('collapse',)
        }),
        ('Location', {
            'fields': ('location',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_draft', 'is_published', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_date_display(self, obj):
        return obj.get_date_display()
    get_date_display.short_description = 'Date'
    
    def get_display_html_preview(self, obj):
        html = obj.get_display_html()
        if html:
            return format_html(html)
        return 'No media'
    get_display_html_preview.short_description = 'Media Preview'
    
    def get_formatted_metrics_display(self, obj):
        if obj.progress_metrics:
            html = '<ul style="margin:0; padding-left:20px;">'
            for key, value in obj.progress_metrics.items():
                html += f'<li><strong>{key}:</strong> {value}</li>'
            html += '</ul>'
            return format_html(html)
        return 'No metrics'
    get_formatted_metrics_display.short_description = 'Metrics'


# ============================================================================
# REFLECTION ADMIN
# ============================================================================

@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = [
        'summary', 'user', 'reflection_type', 'mood', 'energy_level', 
        'sleep_hours', 'is_private', 'created_at'
    ]
    list_filter = [
        'reflection_type', 'mood', 'is_private', 'created_at'
    ]
    search_fields = [
        'summary', 'reflection', 'user__username', 'user__email'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User & Context', {
            'fields': ('user', 'related_journey', 'related_activity', 'reflection_type')
        }),
        ('Content', {
            'fields': ('summary', 'reflection')
        }),
        ('Mood & Energy', {
            'fields': ('mood', 'energy_level', 'sleep_hours')
        }),
        ('Privacy', {
            'fields': ('is_private',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# SOCIAL PUBLISH ADMIN
# ============================================================================

@admin.register(SocialPublish)
class SocialPublishAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'platform', 'journey', 'status', 'scheduled_at', 'published_at', 'created_at'
    ]
    list_filter = [
        'platform', 'status', 'created_at'
    ]
    search_fields = [
        'user__username', 'journey__title', 'share_text'
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User & Content', {
            'fields': ('user', 'journey', 'activity', 'platform', 'share_text', 'share_image')
        }),
        ('Publish Details', {
            'fields': ('publish_url', 'publish_id', 'status', 'scheduled_at', 'published_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# NOTIFICATION ADMIN
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'message_short', 'is_read', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'created_at'
    ]
    search_fields = [
        'user__username', 'message'
    ]
    readonly_fields = ['created_at']
    fieldsets = (
        ('User & Type', {
            'fields': ('user', 'notification_type')
        }),
        ('Content', {
            'fields': ('message', 'redirect_link')
        }),
        ('Context', {
            'fields': ('related_journey', 'related_activity'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def message_short(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_short.short_description = 'Message'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark selected as unread'


# ============================================================================
# COMMENT ADMIN
# ============================================================================

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_short', 'journey', 'activity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content', 'journey__title']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User & Context', {
            'fields': ('user', 'journey', 'activity')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_short(self, obj):
        return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
    content_short.short_description = 'Content'


# ============================================================================
# JOURNEY FOLLOW ADMIN
# ============================================================================

@admin.register(JourneyFollow)
class JourneyFollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'notify_on_new_entry', 'notify_on_completion', 'followed_at']
    list_filter = ['notify_on_new_entry', 'notify_on_completion', 'followed_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['followed_at']
    fieldsets = (
        ('User & Journey', {
            'fields': ('user', 'journey')
        }),
        ('Notifications', {
            'fields': ('notify_on_new_entry', 'notify_on_completion')
        }),
        ('Timestamps', {
            'fields': ('followed_at',),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# JOURNEY SAVE ADMIN
# ============================================================================

@admin.register(JourneySave)
class JourneySaveAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['saved_at']
    fieldsets = (
        ('User & Journey', {
            'fields': ('user', 'journey')
        }),
        ('Timestamps', {
            'fields': ('saved_at',),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# TAG ADMIN
# ============================================================================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    fieldsets = (
        ('Tag', {
            'fields': ('name', 'slug')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(JourneyTag)
class JourneyTagAdmin(admin.ModelAdmin):
    list_display = ['journey', 'tag', 'added_at']
    list_filter = ['added_at']
    search_fields = ['journey__title', 'tag__name']
    readonly_fields = ['added_at']


# ============================================================================
# EXPORT ADMIN
# ============================================================================

@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'journey', 'format', 'status', 'file_size', 
        'requested_at', 'completed_at'
    ]
    list_filter = ['format', 'status', 'include_media', 'include_comments', 'include_reflections']
    search_fields = ['user__username', 'journey__title', 'error_message']
    readonly_fields = ['requested_at', 'completed_at', 'expires_at']
    fieldsets = (
        ('User & Journey', {
            'fields': ('user', 'journey')
        }),
        ('Export Details', {
            'fields': ('format', 'include_media', 'include_comments', 'include_reflections')
        }),
        ('File', {
            'fields': ('file_url', 'file_size')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('requested_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['retry_failed_exports']
    
    def retry_failed_exports(self, request, queryset):
        queryset.update(status='pending', error_message='')
    retry_failed_exports.short_description = 'Retry failed exports'


# ============================================================================
# CONTACT MESSAGE ADMIN
# ============================================================================

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'user', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['name', 'email', 'message', 'user__username']
    readonly_fields = ['created_at', 'ip_address']
    fieldsets = (
        ('Sender', {
            'fields': ('name', 'email', 'user')
        }),
        ('Message', {
            'fields': ('subject', 'message', 'ai_response')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'created_at'),
            'classes': ('collapse',)
        }),
    )


# ============================================================================
# SUBSCRIBER ADMIN
# ============================================================================

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    list_filter = ['subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at', 'ip_address']
    fieldsets = (
        ('Email', {
            'fields': ('email',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'subscribed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_subscribers_csv']
    
    def export_subscribers_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="subscribers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Email', 'Subscribed At'])
        
        for subscriber in queryset:
            writer.writerow([subscriber.email, subscriber.subscribed_at])
        
        return response
    export_subscribers_csv.short_description = 'Export selected subscribers to CSV'


# ============================================================================
# CUSTOM ADMIN SITE SETUP
# ============================================================================

class RallynexAdminSite(admin.AdminSite):
    site_header = 'Rallynex Admin'
    site_title = 'Rallynex Admin Portal'
    index_title = 'Welcome to Rallynex Admin'


# Uncomment to use custom admin site:
# admin_site = RallynexAdminSite(name='rallynex_admin')
# admin_site.register(Profile, ProfileAdmin)
# ... etc

# Register all models with the default admin site
# (Already registered via @admin.register decorators)

# ============================================================================
# DASHBOARD WIDGETS (Optional)
# ============================================================================

def get_admin_dashboard_widgets():
    """
    Returns data for admin dashboard widgets.
    Call this from a custom admin view or template.
    """
    from django.db.models import Count
    
    return {
        'total_users': User.objects.count(),
        'total_journeys': Journey.objects.count(),
        'total_activities': Activity.objects.count(),
        'total_reflections': Reflection.objects.count(),
        'active_journeys': Journey.objects.filter(is_active=True).count(),
        'public_journeys': Journey.objects.filter(privacy_status='public').count(),
        'journeys_by_category': Journey.objects.values('category').annotate(count=Count('id')),
        'recent_activities': Activity.objects.order_by('-created_at')[:10],
        'recent_users': User.objects.order_by('-date_joined')[:10],
    }


# ============================================================================
# ADMIN THEME CUSTOMIZATION (Optional)
# ============================================================================

# Add custom CSS to admin
class RallynexAdminMixin:
    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

# To use, inherit from this mixin in your admin classes:
# class ProfileAdmin(RallynexAdminMixin, admin.ModelAdmin):
#     ...