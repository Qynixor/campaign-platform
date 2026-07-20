from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

# ============================================================================
# URL PATTERNS - BUILD IN PUBLIC FOCUS
# ============================================================================

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION
    # ============================================================================
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ============================================================================
    # PASSWORD RESET - CUSTOM (Shows link directly on page)
    # ============================================================================
    path('password-reset/', 
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),
    
    path('password-reset/done/',
         views.CustomPasswordResetDoneView.as_view(),
         name='password_reset_done'),
    
    path('password-reset/<uidb64>/<token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    
    path('password-reset/complete/',
         views.CustomPasswordResetCompleteView.as_view(),
         name='password_reset_complete'),

    # ============================================================================
    # PUBLIC PAGES - Discover Build in Public Journeys
    # ============================================================================
    path('', views.landing_view, name='landing'),
    path('discover/', views.discover_view, name='discover'),
    path('j/<slug:slug>/', views.journey_detail_view, name='journey_detail'),
    path('@<str:username>/', views.creator_profile_view, name='creator_profile'),

    # ============================================================================
    # STATIC PAGES
    # ============================================================================
    path('about/', views.about_view, name='about'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('contact/', views.contact_view, name='contact'),

    # ============================================================================
    # DASHBOARD - Builder's Control Center
    # ============================================================================
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/journeys/', views.my_journeys_view, name='my_journeys'),
    path('dashboard/saved/', views.saved_journeys_view, name='saved_journeys'),
    path('dashboard/notifications/', views.notifications_view, name='notifications'),
    path('dashboard/settings/', views.profile_settings_view, name='profile_settings'),
    
    # ============================================================================
    # JOURNEY MANAGEMENT - Create and Edit Build in Public Journeys
    # ============================================================================
    path('dashboard/journeys/new/', views.create_journey_view, name='create_journey'),
    path('dashboard/journeys/<slug:slug>/edit/', views.edit_journey_view, name='edit_journey'),
    path('dashboard/journeys/<slug:slug>/settings/', views.journey_settings_view, name='journey_settings'),
    path('dashboard/journeys/<slug:slug>/delete/', views.delete_journey_view, name='delete_journey'),
    path('dashboard/journeys/<slug:slug>/export/', views.export_journey_view, name='export_journey'),
    path('dashboard/exports/<int:export_id>/download/', views.download_export_view, name='download_export'),
    
    # ============================================================================
    # CONTENT MANAGEMENT - Daily Build Logs (Activities)
    # ============================================================================
    path('dashboard/journeys/<slug:slug>/content/', views.journey_content_view, name='journey_content'),
    path('dashboard/journeys/<slug:slug>/entry/new/', views.create_activity_view, name='create_activity'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/', views.create_activity_view, name='create_activity_day'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/edit/', views.edit_activity_view, name='edit_activity'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/delete/', views.delete_activity_view, name='delete_activity'),
    
    # ============================================================================
    # REFLECTIONS - Personal Reflections on Building Journey
    # ============================================================================
    path('dashboard/reflections/', views.reflection_view, name='reflection_view'),
    path('dashboard/reflections/new/', views.create_reflection_view, name='create_reflection'),
    path('dashboard/reflections/<int:pk>/', views.reflection_detail_view, name='reflection_detail'),
    path('dashboard/reflections/<int:pk>/edit/', views.edit_reflection_view, name='edit_reflection'),
    path('dashboard/reflections/<int:pk>/delete/', views.delete_reflection_view, name='delete_reflection'),
    
    # ============================================================================
    # ENGAGEMENT - Follow, Save, Comment (AJAX/API)
    # ============================================================================
    path('api/journey/<slug:slug>/follow/', views.follow_journey_view, name='follow_journey'),
    path('api/journey/<slug:slug>/save/', views.save_journey_view, name='save_journey'),
    
    # Comments
    path('api/journey/<slug:slug>/comment/', views.comment_journey_view, name='comment_journey'),
    path('api/journey/<slug:slug>/<int:day_number>/comment/', views.comment_activity_view, name='comment_activity'),
    path('api/comment/<int:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),
    
    # ============================================================================
    # NOTIFICATIONS - Real-time Updates (AJAX)
    # ============================================================================
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_read'),
    
    # ============================================================================
    # TOOLBOX - Creator Tools Hub
    # ============================================================================
    path('toolbox/', views.toolbox_view, name='toolbox'),
    
    # ============================================================================
    # NEWSLETTER
    # ============================================================================
    path('newsletter/signup/', views.newsletter_signup_view, name='newsletter_signup'),
    
    # ============================================================================
    # THEME TOGGLE - Dark/Light Mode
    # ============================================================================
    path('api/toggle-theme/', views.toggle_theme, name='toggle_theme'),

    # ============================================================================
    # ADVANCED ANALYTICS - Build in Public Metrics
    # ============================================================================
    path('j/<slug:slug>/analytics/', views.journey_analytics, name='journey_analytics'),
    path('j/<slug:slug>/metrics/', views.journey_metrics, name='journey_metrics'),
    path('api/journey/<slug:slug>/<int:day_number>/metric/', views.add_metric_entry, name='add_metric_entry'),

    # ============================================================================
    # GOALS & MILESTONES - Track Progress
    # ============================================================================
    path('j/<slug:slug>/goals/', views.journey_goals, name='journey_goals'),
    path('j/<slug:slug>/goal/create/', views.create_goal, name='create_goal'),
    path('j/<slug:slug>/goal/<int:goal_id>/update/', views.update_goal_progress, name='update_goal_progress'),
    path('j/<slug:slug>/goal/<int:goal_id>/delete/', views.delete_goal, name='delete_goal'),
    
    # ============================================================================
    # JOURNEY DASHBOARD - Complete Overview
    # ============================================================================
    path('j/<slug:slug>/dashboard/', views.journey_dashboard, name='journey_dashboard'),
    
    # ============================================================================
    # JOURNEY CUSTOMIZATION - Brand Your Journey
    # ============================================================================
    path('j/<slug:slug>/customize/', views.journey_customize, name='journey_customize'),

    # ============================================================================
    # MONETIZATION URLS - Rallynex Plus
    # ============================================================================
    
    # Subscription Plans
    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/subscribe/<int:plan_id>/', views.subscribe, name='subscribe'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/cancel/<int:subscription_id>/', views.cancel_subscription, name='cancel_subscription'),
    
    # One-Time Product Purchases
    path('products/', views.product_list, name='product_list'),
    path('products/purchase/<int:product_id>/', views.purchase_product, name='purchase_product'),
    path('products/success/<int:purchase_id>/', views.purchase_success, name='purchase_success'),
    
    # Paid Exports
    path('export/request/<int:journey_id>/', views.request_export, name='request_export'),
    path('export/download/<int:export_id>/', views.export_download, name='export_download'),
    
    # Custom Themes
    path('theme/customize/<int:journey_id>/', views.theme_customization, name='theme_customization'),
    path('theme/apply/<int:theme_id>/', views.apply_theme, name='apply_theme'),
    
    # AI Progress Reports
    path('ai/report/generate/<int:journey_id>/', views.generate_ai_report, name='generate_ai_report'),
    path('ai/report/view/<int:report_id>/', views.view_ai_report, name='view_ai_report'),
    
    # Storage Management
    path('storage/dashboard/', views.storage_dashboard, name='storage_dashboard'),
    
    # Payment Dashboard
    path('payments/dashboard/', views.subscription_dashboard, name='subscription_dashboard'),
    
    # PayPal Webhook
    path('webhook/paypal/', views.paypal_webhook, name='paypal_webhook'),
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