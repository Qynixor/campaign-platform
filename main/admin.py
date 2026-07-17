from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from . import models


# ============================================================================
# PROFILE ADMIN
# ============================================================================
@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_display_name', 'location', 'get_journey_count', 'created_at']
    list_filter = ['location', 'created_at']
    search_fields = ['user__username', 'user__email', 'bio', 'location']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'image', 'bio', 'location')
        }),
        ('Social Links', {
            'fields': ('website', 'twitter', 'linkedin', 'github'),
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
    model = models.Activity
    extra = 0
    fields = ['day_number_field', 'title', 'activity_type', 'is_published', 'created_at']
    readonly_fields = ['created_at']
    ordering = ['-day_number_field']


class JourneyTagInline(admin.TabularInline):
    model = models.JourneyTag
    extra = 1
    autocomplete_fields = ['tag']


@admin.register(models.Journey)
class JourneyAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'creator', 'category', 'journey_type', 
        'privacy_status', 'progress_bar', 'is_active', 'created_at'
    ]
    list_filter = [
        'category', 'journey_type', 'privacy_status', 
        'is_active', 'is_featured', 'is_archived', 'created_at'
    ]
    search_fields = ['title', 'description', 'creator__user__username', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['slug', 'view_count', 'unique_viewers', 'follower_count', 'created_at', 'updated_at']
    
    inlines = [ActivityInline, JourneyTagInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('creator', 'title', 'slug', 'description', 'category', 'journey_type')
        }),
        ('Build in Public Details', {
            'fields': ('product_stage', 'product_url', 'github_url'),
            'classes': ('collapse',)
        }),
        ('Visuals', {
            'fields': ('cover_image', 'template_style')
        }),
        ('Structure', {
            'fields': ('duration', 'current_day_override', 'start_date', 'end_date')
        }),
        ('Privacy & Community', {
            'fields': ('privacy_status', 'allow_comments', 'allow_followers')
        }),
        ('Analytics', {
            'fields': ('view_count', 'unique_viewers', 'follower_count'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_archived')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_public', 'make_private', 'feature_journey', 'archive_journey']
    
    def progress_bar(self, obj):
        progress = obj.get_progress_percentage()
        return format_html(
            '<div style="background: #e5e7eb; border-radius: 10px; height: 20px; width: 100px; overflow: hidden;">'
            '<div style="background: #3B82F6; height: 100%; width: {}%; text-align: center; color: white; font-size: 11px; line-height: 20px;">{}%</div>'
            '</div>',
            progress, progress
        )
    progress_bar.short_description = 'Progress'
    
    def make_public(self, request, queryset):
        queryset.update(privacy_status='public')
    make_public.short_description = "Make selected journeys Public"
    
    def make_private(self, request, queryset):
        queryset.update(privacy_status='private')
    make_private.short_description = "Make selected journeys Private"
    
    def feature_journey(self, request, queryset):
        queryset.update(is_featured=True)
    feature_journey.short_description = "Feature selected journeys"
    
    def archive_journey(self, request, queryset):
        queryset.update(is_archived=True, is_active=False)
    archive_journey.short_description = "Archive selected journeys"


# ============================================================================
# ACTIVITY ADMIN
# ============================================================================
@admin.register(models.Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'journey', 'activity_type', 'product_area',
        'day_number_field', 'is_published', 'is_draft', 'created_at'
    ]
    list_filter = [
        'activity_type', 'product_area', 'is_published', 'is_draft',
        'journey__category', 'created_at'
    ]
    search_fields = ['title', 'content', 'summary', 'journey__title']
    readonly_fields = ['created_at', 'updated_at', 'published_at']
    
    fieldsets = (
        ('Relationships', {
            'fields': ('journey',)
        }),
        ('Content', {
            'fields': ('title', 'content', 'summary')
        }),
        ('Activity Details', {
            'fields': ('activity_type', 'product_area', 'hours_spent')
        }),
        ('Media', {
            'fields': ('media_file', 'is_video', 'thumbnail', 'media_caption'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('day_number_field', 'actual_date')
        }),
        ('Metrics', {
            'fields': ('custom_metrics',),
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
    
    actions = ['publish_entries', 'unpublish_entries']
    
    def publish_entries(self, request, queryset):
        queryset.update(is_published=True, is_draft=False)
    publish_entries.short_description = "Publish selected entries"
    
    def unpublish_entries(self, request, queryset):
        queryset.update(is_published=False)
    unpublish_entries.short_description = "Unpublish selected entries"


# ============================================================================
# REFLECTION ADMIN
# ============================================================================
@admin.register(models.Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'summary', 'reflection_type', 'is_private', 'created_at']
    list_filter = ['reflection_type', 'is_private', 'created_at']
    search_fields = ['user__username', 'summary', 'reflection']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Relationships', {
            'fields': ('user', 'related_journey', 'related_activity')
        }),
        ('Content', {
            'fields': ('reflection_type', 'summary', 'reflection')
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
# TAG ADMIN
# ============================================================================
@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']


# ============================================================================
# COMMENT ADMIN
# ============================================================================
@admin.register(models.Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_preview', 'journey', 'activity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


# ============================================================================
# NOTIFICATION ADMIN
# ============================================================================
@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'message_preview', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


# ============================================================================
# JOURNEY FOLLOW ADMIN
# ============================================================================
@admin.register(models.JourneyFollow)
class JourneyFollowAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'followed_at']
    list_filter = ['followed_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['followed_at']


# ============================================================================
# JOURNEY SAVE ADMIN
# ============================================================================
@admin.register(models.JourneySave)
class JourneySaveAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['saved_at']


# ============================================================================
# EXPORT ADMIN
# ============================================================================
@admin.register(models.Export)
class ExportAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'format', 'status', 'file_size', 'requested_at']
    list_filter = ['format', 'status', 'requested_at']
    search_fields = ['user__username', 'journey__title']
    readonly_fields = ['requested_at', 'completed_at', 'expires_at']


# ============================================================================
# CONTACT & SUBSCRIBER ADMIN
# ============================================================================
@admin.register(models.ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['created_at', 'ip_address']


@admin.register(models.Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    list_filter = ['subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at', 'ip_address']


# ============================================================================
# SOCIAL PUBLISH ADMIN
# ============================================================================
@admin.register(models.SocialPublish)
class SocialPublishAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'status', 'journey', 'created_at']
    list_filter = ['platform', 'status', 'created_at']
    search_fields = ['user__username', 'share_text']
    readonly_fields = ['created_at', 'updated_at', 'published_at']


# ============================================================================
# SUBSCRIPTION ADMIN
# ============================================================================
@admin.register(models.SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'is_active']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(models.UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'plan', 'start_date']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']


# ============================================================================
# ONE-TIME PRODUCT ADMIN
# ============================================================================
@admin.register(models.OneTimeProduct)
class OneTimeProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_type', 'payment_type', 'price_min', 'is_active']
    list_filter = ['product_type', 'payment_type', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(models.UserPurchase)
class UserPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'amount_paid', 'status', 'purchased_at']
    list_filter = ['status', 'purchased_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['purchased_at']


# ============================================================================
# PAID PRODUCTS ADMIN
# ============================================================================
@admin.register(models.PaidJourneyExport)
class PaidJourneyExportAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'format', 'is_downloaded', 'created_at']
    list_filter = ['format', 'is_downloaded', 'created_at']
    search_fields = ['user__username', 'journey__title']


@admin.register(models.CustomTheme)
class CustomThemeAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'theme_type', 'is_active', 'created_at']
    list_filter = ['theme_type', 'is_active']
    search_fields = ['user__username', 'name']


@admin.register(models.PaidCustomTheme)
class PaidCustomThemeAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'theme_type', 'is_active', 'created_at']
    list_filter = ['theme_type', 'is_active']
    search_fields = ['user__username', 'name']


@admin.register(models.PaidExtraStorage)
class PaidExtraStorageAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_mb', 'used_mb', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__username']


@admin.register(models.PaidAIProgressReport)
class PaidAIProgressReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'journey', 'status', 'is_downloaded', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'journey__title']


@admin.register(models.PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'currency', 'transaction_type', 'is_successful', 'created_at']
    list_filter = ['transaction_type', 'is_successful', 'created_at']
    search_fields = ['user__username', 'paypal_transaction_id']
    readonly_fields = ['created_at']


# ============================================================================
# CUSTOM ADMIN SITE CONFIGURATION
# ============================================================================
admin.site.site_header = 'Rallynex Admin'
admin.site.site_title = 'Rallynex Admin Portal'
admin.site.index_title = 'Welcome to Rallynex Administration'

# Group models in the admin index
admin.site._registry = dict(sorted(admin.site._registry.items(), key=lambda x: x[0]._meta.verbose_name_plural))