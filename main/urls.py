from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

# ============================================================================
# URL PATTERNS - DOCUMENTATION-FIRST
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
    path('blog/', views.blog_view, name='blog'),

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
    path('dashboard/journeys/<slug:slug>/export/', views.export_journey_view, name='export_journey'),
    path('dashboard/exports/<int:export_id>/download/', views.download_export_view, name='download_export'),
    
    # ============================================================================
    # CONTENT MANAGEMENT (Entries/Activities)
    # ============================================================================
    path('dashboard/journeys/<slug:slug>/content/', views.journey_content_view, name='journey_content'),
    path('dashboard/journeys/<slug:slug>/entry/new/', views.create_activity_view, name='create_activity'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/', views.create_activity_view, name='create_activity_day'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/edit/', views.edit_activity_view, name='edit_activity'),
    path('dashboard/journeys/<slug:slug>/entry/<int:day_number>/delete/', views.delete_activity_view, name='delete_activity'),
    
    # ============================================================================
    # JOURNAL ENTRIES (Free-Form Documentation)
    # ============================================================================
    path('dashboard/journal/', views.journal_view, name='journal_view'),
    path('dashboard/journal/new/', views.journal_create_view, name='journal_create'),
    path('dashboard/journal/<int:pk>/', views.journal_detail_view, name='journal_detail'),
    path('dashboard/journal/<int:pk>/edit/', views.journal_edit_view, name='journal_edit'),
    path('dashboard/journal/<int:pk>/delete/', views.journal_delete_view, name='journal_delete'),
    
    # ============================================================================
    # ENGAGEMENT (AJAX/API)
    # ============================================================================
    path('api/journey/<slug:slug>/follow/', views.follow_journey_view, name='follow_journey'),
    path('api/journey/<slug:slug>/save/', views.save_journey_view, name='save_journey'),
    
    # Comments
    path('api/journey/<slug:slug>/comment/', views.comment_journey_view, name='comment_journey'),
    path('api/journey/<slug:slug>/<int:day_number>/comment/', views.comment_activity_view, name='comment_activity'),
    path('api/comment/<int:comment_id>/delete/', views.delete_comment_view, name='delete_comment'),
    
    # ============================================================================
    # NOTIFICATIONS (AJAX)
    # ============================================================================
    path('api/notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read_view, name='mark_all_read'),
     path('toolbox/', views.dashboard_view, name='toolbox'),    
    # ============================================================================
    # NEWSLETTER
    # ============================================================================
    path('newsletter/signup/', views.newsletter_signup_view, name='newsletter_signup'),
    
    # ============================================================================
    # THEME TOGGLE
    # ============================================================================
    path('api/toggle-theme/', views.toggle_theme, name='toggle_theme'),
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