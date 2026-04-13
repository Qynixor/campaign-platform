from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

# ============================================================================
# URL PATTERNS
# ============================================================================

urlpatterns = [
    # Welcome/Onboarding
    path('welcome/', views.welcome_view, name='welcome'),

    
    # Onboarding
    path('onboarding/', views.onboarding_wizard_view, name='onboarding'),
    path('api/journey/quick-create/', views.api_quick_create_journey, name='api_quick_create_journey'),    
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset (using Django built-in views)
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
    path('', views.landing_view, name='landing'),
    path('discover/', views.discover_view, name='discover'),
    path('j/<slug:slug>/', views.journey_detail_view, name='journey_detail'),
    path('@<str:username>/', views.creator_profile_view, name='creator_profile'),
    
    # ============================================================================
    # BLOG
    # ============================================================================
    path('blog/', views.blog_list_view, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail_view, name='blog_detail'),
    
    # ============================================================================
    # STATIC PAGES
    # ============================================================================
    path('about/', views.about_view, name='about'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('contact/', views.contact_view, name='contact'),
    path('faq/', views.faq_view, name='faq'),
    
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
    # SOCIAL IMPORT
    # ============================================================================
    path('dashboard/social/', views.social_connections_view, name='social_connections'),
    path('dashboard/social/connect/<str:platform>/', views.connect_social_view, name='connect_social'),
    path('dashboard/social/callback/', views.social_callback_view, name='social_callback'),
    path('dashboard/social/<int:connection_id>/disconnect/', views.disconnect_social_view, name='disconnect_social'),
    
    path('dashboard/import/', views.import_queue_view, name='import_queue'),
    path('dashboard/import/quick/', views.quick_import_view, name='quick_import'),
    path('dashboard/import/<int:import_id>/process/', views.process_import_view, name='process_import'),
    
    # ============================================================================
    # PRODUCTS (POST-JOURNEY)
    # ============================================================================
    path('dashboard/journeys/<slug:slug>/products/new/', views.create_product_view, name='create_product'),
    path('dashboard/products/<int:product_id>/edit/', views.edit_product_view, name='edit_product'),
    
    # ============================================================================
    # DONATIONS
    # ============================================================================
    path('j/<slug:slug>/donate/', views.donation_view, name='donate'),
    path('donation/<int:donation_id>/process/', views.process_donation_view, name='process_donation'),
    path('donation/success/', views.donation_success_view, name='donation_success'),
    path('donation/cancel/', views.donation_cancel_view, name='donation_cancel'),
    
    # ============================================================================
    # ENGAGEMENT (AJAX/API)
    # ============================================================================
    path('api/journey/<slug:slug>/follow/', views.follow_journey_view, name='follow_journey'),
    path('api/journey/<slug:slug>/save/', views.save_journey_view, name='save_journey'),
    path('api/journey/<slug:slug>/share/', views.share_journey_view, name='share_journey'),
    path('api/activity/<int:activity_id>/love/', views.love_activity_view, name='love_activity'),
    path('api/activity/<int:activity_id>/comment/', views.comment_activity_view, name='comment_activity'),
    
    # ============================================================================
    # REPORTS
    # ============================================================================
    path('api/journey/<slug:slug>/report/', views.report_journey_view, name='report_journey'),
    path('api/activity/<int:activity_id>/report/', views.report_activity_view, name='report_activity'),
    
    # ============================================================================
    # NOTIFICATIONS (AJAX)
    # ============================================================================
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_read'),
    
    # ============================================================================
    # ANALYTICS API
    # ============================================================================
    path('api/journey/<slug:slug>/stats/', views.api_journey_stats_view, name='api_journey_stats'),
    path('api/activity/<int:activity_id>/stats/', views.api_activity_stats_view, name='api_activity_stats'),
    
    # ============================================================================
    # TINYMCE (for blog)
    # ============================================================================
    path('tinymce/', include('tinymce.urls')),
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