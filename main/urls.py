from django.urls import path, include
from . import views

from .views import CustomLoginView
from .views import CampaignDeleteView

from django.views.generic.base import RedirectView
from .views import get_activity_comments, post_activity_comment, like_activity_comment

from .views import campaign_story_list, campaign_story_detail

urlpatterns = [

  path('product/<int:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
path('product/<int:product_id>/mark-out-of-stock/', views.mark_out_of_stock, name='mark_out_of_stock'),
   path('campaign/<int:campaign_id>/engagement/', views.campaign_engagement_data, name='campaign_engagement'),
       # Redirect deleted project-support to landing page
    # ADD THIS REDIRECT - when users visit /project-support/, send them to /landing/
 # Handle both with and without trailing slash:
path('project-support', RedirectView.as_view(
    pattern_name='explore_campaigns',
    permanent=True
)),
path('project-support/', RedirectView.as_view(
    pattern_name='explore_campaigns',
    permanent=True
)),

path('project_support', RedirectView.as_view(
    pattern_name='explore_campaigns',
    permanent=True
)),
path('project_support/', RedirectView.as_view(
    pattern_name='explore_campaigns',
    permanent=True
)),
    path('landing/', views.explore_campaigns, name='explore_campaigns'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('face/', views.face, name='face'),

       path('success-stories/', views.success_stories, name='success_stories'),

 path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
  
    path('hiw/', views.hiw, name='hiw'),
    path('faq/', views.faq_view, name='faq'),
     path('about/', views.aboutus, name='aboutus'),
         path('fund/', views.fund, name='fund'),
       path('geno/', views.geno, name='geno'),
    
    path('verify/', views.verify_profile, name='verify_profile'),
    path('campaign/<int:campaign_id>/join_leave/', views.join_leave_campaign, name='join_leave_campaign'),
   
 path('edit/', views.edit_gif, name='edit_gif'),

    path('campaign/delete/<int:pk>/', CampaignDeleteView.as_view(), name='campaign-delete'),

       path('login/', CustomLoginView.as_view(), name='login'),
  
    path('rallynex-logo/', views.rallynex_logo, name='rallynex_logo'),
  

    path('campaign/<int:campaign_id>/top-participants/', views.top_participants_view, name='top_participants'),
     path('project-support/', views.project_support, name='project_support'),
    # Other URL patterns...
      # Other URL patterns for your project
      path('campaigns/mark_not_interested/<int:campaign_id>/', views.mark_not_interested, name='mark_not_interested'),
    path('campaign/<int:campaign_id>/report/',views.report_campaign, name='report_campaign'),
    path('upload_image/',views.upload_image, name='upload_image'),
    path('campaign/<int:campaign_id>/product/', views.product_manage, name='product_manage'),
    path('campaign/<int:campaign_id>/product/<int:product_id>/', views.product_manage, name='product_edit'),
    # Other URL patterns.
     path('changemakers/', views.changemakers_view, name='changemakers_view'),
    path('love_activity/<int:activity_id>/', views.love_activity, name='love_activity'),
   path('activity/<int:activity_id>/', views.activity_detail, name='activity_detail'),

    path('delete/<int:campaign_id>/', views.delete_campaign, name='delete_campaign'),
path('add_activity_comment/<int:activity_id>/', views.add_activity_comment, name='add_activity_comment'),
 
   
    path('campaign/<int:campaign_id>/', views.view_campaign, name='view_campaign'),  # Corrected URL pattern
  
    path('update_hidden_links/', views.update_hidden_links, name='update_hidden_links'),
 path('upload/', views.upload_file, name='upload_file'),
      path('campaign/<int:campaign_id>/donate/', views.create_donation, name='create_donation'),
    
    path('search_profile_results/', views.search_profile_results, name='search_profile_results'),
    path('search/', views.search_campaign, name='search_campaign'),
    path('notifications/', views.notification_list, name='notification_list'),
 

    path('campaign/<int:campaign_id>/support/', views.support, name='support'),
    path('campaign/<int:campaign_id>/support-campaign/', views.campaign_support, name='campaign_support'),
    path('thank-you/', views.thank_you, name='thank_you'),
   
    path('manage_campaigns/', views.manage_campaigns, name='manage_campaigns'),

    path('create_campaign/', views.create_campaign, name='create_campaign'),
    path('edit-profile/<str:username>/', views.profile_edit, name='edit_profile'),
  path('user-profile/@<str:username>/', views.profile_view, name='profile_view'),
 

    path('recreate-campaign/<int:campaign_id>/', views.recreate_campaign, name='recreate_campaign'),
     path('success/', views.success_page, name='success_page'),
    path('campaign/<int:campaign_id>/activity/create/', views.create_activity, name='create_activity'),
    path('campaign/<int:campaign_id>/activity_list/', views.activity_list, name='activity_list'),
    path('campaign/<int:campaign_id>/comments/', views.campaign_comments, name='campaign_comments'),

    path('record_campaign_view/<int:campaign_id>/', views.record_campaign_view, name='record_campaign_view'),
# marketing 
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('blog/<slug:slug>/view/', views.blog_view_increment, name='blog_view_increment'),
    path('blog/<slug:slug>/like/', views.blog_like, name='blog_like'),
    path('blog/<slug:slug>/share/', views.blog_share, name='blog_share'),
 
# Add this to your urlpatterns
path('new-causes/', views.new_causes, name='new_causes'),

    path('campaign-stories/', campaign_story_list, name='campaign_story_list'),
    path('campaign-stories/<slug:slug>/', campaign_story_detail, name='campaign_story_detail'),

    path('testimonial/', views.testimonial, name='testimonial'),

  # These should be in your urlpatterns:
path('love_activity/<int:activity_id>/', views.love_activity, name='love_activity'),
path('get_activity_comments/<int:activity_id>/', views.get_activity_comments, name='get_activity_comments'),
path('post_activity_comment/', views.post_activity_comment, name='post_activity_comment'),
path('like_activity_comment/', views.like_activity_comment, name='like_activity_comment'),

# Add these to your urlpatterns if they're missing:
path('post_comment_reply/', views.post_comment_reply, name='post_comment_reply'),
path('get_comment_replies/<int:comment_id>/', views.get_comment_replies, name='get_comment_replies'),
path('like_comment_reply/', views.like_comment_reply, name='like_comment_reply'),




path('initiate-pledge-payment/<int:pledge_id>/', views.initiate_pledge_payment, name='initiate_pledge_payment'),
path('pledge-payment-callback/<int:pledge_id>/', views.pledge_payment_callback, name='pledge_payment_callback'),
path('pledge-success/<int:pledge_id>/', views.pledge_success, name='pledge_success'),
path('pledge-failure/', views.pledge_failure, name='pledge_failure'),



  

    path('donate/<int:campaign_id>/', views.create_donation, name='create_donation'),
    path('donate/callback/<int:donation_id>/', views.donation_payment_callback, name='donation_payment_callback'),
    path('donate/success/<int:donation_id>/', views.donation_success, name='donation_success'),
    path('donate/failure/', views.donation_failure, name='donation_failure'),


      path("product/<int:product_id>/paypal/", views.initiate_paypal_payment, name="initiate_paypal_payment"),
    path("paypal/callback/", views.paypal_payment_callback, name="paypal_payment_callback"),
    path("payment/success/<int:transaction_id>/", views.payment_success, name="payment_success"),
    path("payment/failure/", views.payment_failure, name="payment_failure"),
    path("transactions/", views.transaction_history, name="transaction_history"),
  

    
    # Common URLs
    path('success-page/', views.success_page, name='success_page'),
   
# DM URLs - ALL 4 ARE REQUIRED
path('dm/inbox/', views.dm_inbox, name='dm_inbox'),
path('dm/<int:dm_id>/', views.dm_page, name='dm_page'),
path('dm/start/<int:user_id>/', views.start_dm, name='start_dm'),
path('dm/<int:dm_id>/send/', views.send_dm_message, name='send_dm_message'),  # THIS ONE WAS MISSING
# Add these to your existing urlpatterns
path('update-activity/', views.update_activity, name='update_activity'),
path('check-status/<int:user_id>/', views.check_status, name='check_status'),
path('campaign/<int:campaign_id>/pledge/', views.create_pledge, name='create_pledge'),
# urls.py

# Add this line to your urlpatterns:
path('campaign/<int:campaign_id>/pledgers/', views.campaign_pledgers_view, name='campaign_pledgers'),

    # In urls.py
# In urls.py
path('debug-video/<int:activity_id>/', views.debug_video_processing, name='debug_video'),



    # Supporters and Following (empty templates for now)
    path('<str:username>/supporters/', views.supporters_view, name='supporters'),
    path('<str:username>/following/causes/', views.following_causes_view, name='following_causes'),

# Add these to your urlpatterns

# Journey URLs
# Add these to your urlpatterns

# Journey URLs
path('journey/', views.journey, name='journey'),
path('journey/<int:campaign_id>/', views.journey, name='campaign_journey'),

# Interaction URLs (using regular JSON responses for reliability)
path('campaign/<int:campaign_id>/toggle-love/', views.toggle_love, name='toggle_love'),
path('campaign/<int:campaign_id>/toggle-follow/', views.toggle_follow, name='toggle_follow'),
path('campaign/<int:campaign_id>/toggle-save/', views.toggle_save, name='toggle_save'),
path('campaign/<int:campaign_id>/get-comments/', views.get_comments, name='get_comments'),
path('campaign/<int:campaign_id>/post-comment/', views.post_comment, name='post_comment'),
path('campaign/<int:campaign_id>/get-stats/', views.get_stats, name='get_stats'),
path('campaign/<int:campaign_id>/get-menu/', views.get_menu, name='get_menu'),

# Clone URL
path('journey/<int:original_id>/clone/', views.clone_journey, name='clone_journey'),
]












