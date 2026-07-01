from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

# ============================================================================
# URL PATTERNS - SOCIAL-FIRST FOCUSED
# ============================================================================

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'),
         name='password_reset_complete'),

    # ============================================================================
    # PUBLIC PAGES
    # ============================================================================
    # Landing page is the root URL - also aliased as home_feed for navbar
    path('', views.landing_view, name='landing'),
    path('home/', views.landing_view, name='home_feed'),  # ← ADD THIS ALIAS
    path('discover/', views.discover_view, name='discover'),
    path('j/<slug:slug>/', views.journey_detail_view, name='journey_detail'),
    path('@<str:username>/', views.creator_profile_view, name='creator_profile'),

    # ============================================================================
    # STATIC PAGES
    # ============================================================================
    path('about/', views.about_view, name='about'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('faq/', views.faq_view, name='faq'),
    path('contact/', views.contact_view, name='contact'),
    
    # ============================================================================
    # CONVERSION / NEWSLETTER
    # ============================================================================
    path('start/', views.conversion_start_view, name='conversion_start'),

    # ============================================================================
    # DASHBOARD
    # ============================================================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/journeys/', views.my_journeys_view, name='my_journeys'),
    path('dashboard/saved/', views.saved_journeys_view, name='saved_journeys'),
    path('dashboard/notifications/', views.notifications_view, name='notifications'),
    path('dashboard/settings/', views.profile_settings_view, name='profile_settings'),
    
    # ============================================================================
    # JOURNEY MANAGEMENT
    # ============================================================================
    path('dashboard/journeys/new/', views.create_journey_view, name='create_journey'),
    path('dashboard/journeys/<slug:slug>/edit/', views.edit_journey_view, name='edit_journey'),
    path('dashboard/journeys/<slug:slug>/settings/', views.journey_settings_view, name='journey_settings'),
    path('dashboard/journeys/<slug:slug>/delete/', views.delete_journey_view, name='delete_journey'),
    
    # ============================================================================
    # CONTENT MANAGEMENT
    # ============================================================================
    path('dashboard/journeys/<slug:slug>/content/', views.journey_content_view, name='journey_content'),
    path('dashboard/journeys/<slug:slug>/post/', views.post_activity_view, name='post_activity'),
    path('dashboard/journeys/<slug:slug>/post/<int:day_number>/', views.post_activity_view, name='post_activity_day'),
    path('dashboard/activities/<int:activity_id>/delete/', views.delete_activity_view, name='delete_activity'),
    
    # ============================================================================
    # SOCIAL IMPORT - CRITICAL (Social-First)
    # ============================================================================
    # Social connections
    path('dashboard/social/', views.social_connections_view, name='social_connections'),
    path('dashboard/social/connect/<str:platform>/', views.connect_social_view, name='connect_social'),
    path('dashboard/social/callback/', views.social_callback_view, name='social_callback'),
    path('dashboard/social/<int:connection_id>/disconnect/', views.disconnect_social_view, name='disconnect_social'),
    
    # Import content
    path('dashboard/import/', views.import_queue_view, name='import_queue'),
    path('dashboard/import/quick/', views.quick_import_view, name='quick_import'),
    path('dashboard/import/<int:import_id>/process/', views.process_import_view, name='process_import'),
    
    # Social templates
    path('dashboard/journeys/<slug:slug>/social-templates/', views.social_template_view, name='social_template'),
    path('dashboard/social-templates/<int:template_id>/delete/', views.delete_social_template_view, name='delete_social_template'),
    
    # API preview
    path('api/preview/', views.api_preview_url, name='api_preview_url'),
    
    # ============================================================================
    # API ENDPOINTS - SOCIAL-FIRST
    # ============================================================================
    path('api/social-settings/<int:connection_id>/', views.api_social_settings, name='api_social_settings'),
    path('api/social-template/<int:template_id>/', views.api_social_template, name='api_social_template'),
    
    # ============================================================================
    # TEMPLATE STORE - ADD THIS
    # ============================================================================
    path('templates/', views.template_store_view, name='template_store'),
    
    # ============================================================================
    # ENGAGEMENT (AJAX/API)
    # ============================================================================
    path('api/journey/<slug:slug>/follow/', views.follow_journey_view, name='follow_journey'),
    path('api/journey/<slug:slug>/save/', views.save_journey_view, name='save_journey'),
    path('api/journey/<slug:slug>/share/', views.share_journey_view, name='share_journey'),
    path('api/activity/<int:activity_id>/love/', views.love_activity_view, name='love_activity'),
    path('api/activity/<int:activity_id>/comment/', views.comment_activity_view, name='comment_activity'),
    
    # ============================================================================
    # NOTIFICATIONS (AJAX)
    # ============================================================================
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_read'),
    
    # ============================================================================
    # REPORTS
    # ============================================================================
    path('api/journey/<slug:slug>/report/', views.report_journey_view, name='report_journey'),
    path('api/activity/<int:activity_id>/report/', views.report_activity_view, name='report_activity'),
    
    # ============================================================================
    # THEME TOGGLE
    # ============================================================================
    path('api/toggle-theme/', views.toggle_theme, name='toggle_theme'),
    
    # ============================================================================
    # BLOG
    # ============================================================================
    path('blog/', views.blog_index, name='blog_index'),
    path('blog/why-instagram/', views.blog_instagram, name='blog_instagram'),
    path('blog/posts-not-journeys/', views.blog_posts_not_journeys, name='blog_posts_not_journeys'),
    path('blog/challenge-to-product/', views.blog_challenge_product, name='blog_challenge_product'),
    path('blog/journey-50-pieces/', views.blog_journey_content, name='blog_journey_content'),
    path('blog/scattered-to-structured/', views.blog_scattered_posts, name='blog_scattered_posts'),
    path('blog/buried-asset/', views.blog_buried_asset, name='blog_buried_asset'),
    path('blog/blind-spot/', views.blog_blind_spot, name='blog_blind_spot'),
    path('blog/30-day-challenge-fails/', views.blog_challenge_fails, name='blog_challenge_fails'),
    path('blog/journey-page-for-coaches/', views.blog_journey_page, name='blog_journey_page'), 
    path('blog/challenge-lost-after-day-7/', views.blog_challenge_lost, name='blog_challenge_lost'),

    # In main/urls.py, add this to the urlpatterns:

# ============================================================================
# TOOLBOX
# ============================================================================
path('toolbox/', views.toolbox_view, name='toolbox'),
]

# ============================================================================
# MEDIA & STATIC (Development only)
# ============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ============================================================================
# CUSTOM ERROR HANDLERS
# ============================================================================
handler404 = 'main.views.handler404'
handler500 = 'main.views.handler500'
handler403 = 'main.views.handler403'