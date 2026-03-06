from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from tinymce.widgets import TinyMCE

from .models import (
    # Core models
    Profile, Campaign, CampaignView, SupportCampaign, Love, Comment, CommentLike,
    Activity, VideoScreenshot, ActivityLove, ActivityComment, ActivityCommentLike,
    Notification, Report, NotInterested, UserVerification, ChangemakerAward,
    Conversation, DirectMessage, ActiveAudioSession,
    
    # Marketing models
    Blog, CampaignStory, FAQ,
    
    # Monetization models
    Donation, Pledge, CampaignProduct, Transaction, Cart, CartItem,
)


# ============================================================================
# PROFILE ADMIN
# ============================================================================

class CampaignInline(admin.TabularInline):
    model = Campaign
    extra = 0

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'profile_verified', 'is_changemaker')
    search_fields = ('user__username', 'location', 'bio')
    list_filter = ('profile_verified',)
    readonly_fields = ('user',)
    inlines = [CampaignInline]
    actions = ['verify_users']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def verify_users(self, request, queryset):
        for profile in queryset:
            profile.profile_verified = True
            profile.save()
        self.message_user(request, "Selected profiles have been verified.")
    verify_users.short_description = "Verify selected users"

    def is_changemaker(self, obj):
        return obj.is_changemaker()
    is_changemaker.boolean = True
    is_changemaker.short_description = 'Changemaker'

admin.site.register(Profile, ProfileAdmin)


# ============================================================================
# CAMPAIGN ADMIN
# ============================================================================

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'is_active', 'timestamp')
    search_fields = ('user__user__username', 'title', 'content')
    list_filter = ('category', 'is_active', 'timestamp')
    raw_id_fields = ('user', 'tags')
    readonly_fields = ('timestamp', 'end_date', 'duration_last_updated')


@admin.register(CampaignView)
class CampaignViewAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'user', 'timestamp')
    search_fields = ('campaign__title', 'user__user__username')
    list_filter = ('timestamp',)
    raw_id_fields = ('campaign', 'user')


# ============================================================================
# SUPPORT & ENGAGEMENT ADMIN
# ============================================================================

@admin.register(SupportCampaign)
class SupportCampaignAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'category', 'donate_monetary_visible', 'pledge_visible', 'campaign_product_visible')
    list_filter = ('category',)
    search_fields = ('user__username', 'campaign__title')
    raw_id_fields = ('user', 'campaign')

@admin.register(Love)
class LoveAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign')  # Remove 'timestamp'
    search_fields = ('user__username', 'campaign__title')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'timestamp', 'text_preview')
    search_fields = ('user__user__username', 'campaign__title', 'text')
    list_filter = ('timestamp',)
    raw_id_fields = ('user', 'campaign', 'parent_comment')
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Comment'


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'is_like', 'timestamp')
    list_filter = ('is_like',)
    raw_id_fields = ('user', 'comment')


# ============================================================================
# ACTIVITY ADMIN
# ============================================================================

class VideoScreenshotInline(admin.TabularInline):
    model = VideoScreenshot
    extra = 0
    fields = ['order', 'timestamp']
    raw_id_fields = ['activity']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'campaign', 'short_content', 'is_video', 'timestamp')
    list_filter = ('is_video', 'video_processed')
    search_fields = ('content',)
    raw_id_fields = ('campaign',)
    inlines = [VideoScreenshotInline]
    
    fieldsets = (
        (None, {
            'fields': ('campaign', 'content', 'file')
        }),
        ('Video Processing', {
            'fields': ('is_video', 'video_processed', 'screenshot_count'),
            'classes': ('collapse',)
        }),
    )
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if obj.content and len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content'


@admin.register(VideoScreenshot)
class VideoScreenshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity', 'order', 'timestamp')
    raw_id_fields = ('activity',)


@admin.register(ActivityLove)
class ActivityLoveAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'timestamp')
    raw_id_fields = ('user', 'activity')


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'content_preview', 'timestamp')
    search_fields = ('content', 'user__username')
    raw_id_fields = ('user', 'activity', 'parent_comment')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Comment'


@admin.register(ActivityCommentLike)
class ActivityCommentLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'comment', 'timestamp')
    raw_id_fields = ('user', 'comment')


@admin.register(ActiveAudioSession)
class ActiveAudioSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity', 'started_at', 'last_heartbeat')
    raw_id_fields = ('user', 'activity')


# ============================================================================
# MESSAGING ADMIN
# ============================================================================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'updated_at', 'last_message_preview')
    search_fields = ('user1__username', 'user2__username')
    list_filter = ('updated_at',)
    raw_id_fields = ('user1', 'user2')
    
    def last_message_preview(self, obj):
        last_msg = obj.last_message
        return last_msg.content[:50] + '...' if last_msg and last_msg.content else ''


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'content_preview', 'timestamp', 'read')
    list_filter = ('read', 'timestamp')
    search_fields = ('sender__username', 'recipient__username', 'content')
    raw_id_fields = ('conversation', 'sender', 'recipient')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message'


# ============================================================================
# NOTIFICATION & REPORTING ADMIN
# ============================================================================

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_preview', 'viewed', 'timestamp', 'campaign_notification')
    list_filter = ('viewed', 'campaign_notification', 'timestamp')
    search_fields = ('user__username', 'message')
    raw_id_fields = ('user', 'campaign')
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'reported_by', 'reason', 'timestamp')
    search_fields = ('campaign__title', 'reported_by__user__username', 'reason', 'description')
    list_filter = ('reason', 'timestamp')
    raw_id_fields = ('campaign', 'reported_by')
    actions = ['delete_reported_campaigns']

    def delete_reported_campaigns(self, request, queryset):
        for report in queryset:
            campaign = report.campaign
            campaign_title = campaign.title
            campaign.delete()
            self.message_user(request, f'The campaign "{campaign_title}" has been deleted.', messages.SUCCESS)
    delete_reported_campaigns.short_description = "Delete selected campaigns"


@admin.register(NotInterested)
class NotInterestedAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'timestamp')
    raw_id_fields = ('user', 'campaign')


# ============================================================================
# VERIFICATION & AWARDS ADMIN
# ============================================================================

@admin.register(UserVerification)
class UserVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'submission_date', 'verified_on')
    search_fields = ('user__username', 'document_type', 'status')
    list_filter = ('status', 'document_type', 'submission_date')
    readonly_fields = ('submission_date',)
    actions = ['approve_verifications', 'reject_verifications']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status == 'Rejected' and obj.rejection_reason:
            message = f"Your verification for {obj.document_type} has been rejected. Reason: {obj.rejection_reason}."
            Notification.objects.create(user=obj.user, message=message)
        elif obj.status == 'Approved':
            message = f"Your verification for {obj.document_type} has been approved."
            Notification.objects.create(user=obj.user, message=message)

    def approve_verifications(self, request, queryset):
        for verification in queryset:
            verification.status = 'Approved'
            verification.verified_on = timezone.now()
            verification.save()
            message = f"Your verification for {verification.document_type} has been approved."
            Notification.objects.create(user=verification.user, message=message)
        self.message_user(request, f"{queryset.count()} verifications approved.")
    approve_verifications.short_description = "Approve selected verifications"

    def reject_verifications(self, request, queryset):
        for verification in queryset:
            verification.status = 'Rejected'
            verification.save()
        self.message_user(request, f"{queryset.count()} verifications rejected. Please add rejection reasons individually.")
    reject_verifications.short_description = "Reject selected verifications"


@admin.register(ChangemakerAward)
class ChangemakerAwardAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'award', 'timestamp')
    search_fields = ('user__user__username', 'campaign__title', 'award')
    list_filter = ('award', 'timestamp')
    raw_id_fields = ('user', 'campaign')
    ordering = ('-timestamp',)


# ============================================================================
# MARKETING & CONTENT ADMIN
# ============================================================================

from .forms import BlogForm

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    form = BlogForm
    list_display = ('title', 'category', 'status', 'author', 'created_at', 'view_count')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'content', 'excerpt', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('view_count', 'like_count', 'share_count', 'seo_score')
    raw_id_fields = ('author', 'related_posts')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'author')
        }),
        ('SEO & Metadata', {
            'fields': ('meta_title', 'meta_description', 'focus_keyword', 'canonical_url')
        }),
        ('Media', {
            'fields': ('featured_image', 'og_image')
        }),
        ('Status & Organization', {
            'fields': ('status', 'category', 'tags', 'published_at')
        }),
        ('Related Content', {
            'fields': ('related_posts',)
        }),
        ('Statistics', {
            'fields': ('estimated_reading_time', 'view_count', 'like_count', 'share_count', 'seo_score'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CampaignStory)
class CampaignStoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'display_image')
    list_filter = ('created_at',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'display_image')

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'content', 'image'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" style="border-radius: 5px;" />', obj.image.url)
        return "No Image"
    display_image.short_description = "Image Preview"


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'answer_preview')
    list_filter = ('category',)
    search_fields = ('question', 'answer')
    
    def answer_preview(self, obj):
        return obj.answer[:75] + '...' if len(obj.answer) > 75 else obj.answer
    answer_preview.short_description = 'Answer'


# ============================================================================
# MONETIZATION ADMIN
# ============================================================================

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('user', 'campaign', 'amount', 'fulfilled', 'timestamp')
    list_filter = ('fulfilled', 'timestamp')
    search_fields = ('user__username', 'campaign__title')
    raw_id_fields = ('user', 'campaign')
    readonly_fields = ('timestamp',)


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'campaign', 'amount', 'is_fulfilled', 'payment_status', 'timestamp')
    list_filter = ('is_fulfilled', 'payment_status', 'timestamp')
    search_fields = ('user__username', 'anonymous_name', 'contact', 'campaign__title')
    raw_id_fields = ('user', 'campaign')
    readonly_fields = ('timestamp',)
    
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return obj.anonymous_name or "Anonymous"
    user_display.short_description = 'User'


@admin.register(CampaignProduct)
class CampaignProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'price', 'stock_quantity', 'stock_status', 'is_active')
    list_filter = ('campaign', 'is_active', 'stock_status')
    search_fields = ('name', 'description', 'campaign__title')
    list_editable = ('price', 'stock_quantity', 'is_active')
    raw_id_fields = ('campaign',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'buyer', 'amount', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'payout_status', 'created_at')
    search_fields = ('buyer__username', 'product__name', 'tx_ref')
    raw_id_fields = ('product', 'buyer')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items_display', 'total_price_display', 'updated_at')
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
    
    def total_items_display(self, obj):
        return obj.total_items
    total_items_display.short_description = 'Items'
    
    def total_price_display(self, obj):
        return f"${obj.total_price}"
    total_price_display.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price', 'added_at')
    raw_id_fields = ('cart', 'product')

