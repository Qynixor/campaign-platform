from django.urls import path, include
from . import views
from .views import CustomLoginView
from .views import CampaignDeleteView
# urls.py
from .views import ChatDetailView
from django.views.generic.base import RedirectView
from .views import get_activity_comments, post_activity_comment, like_activity_comment

from .views import campaign_story_list, campaign_story_detail
from .views import get_comments, post_comment
urlpatterns = [
    path('get_comments/', get_comments, name='get_comments'),
    path('post_comment/', post_comment, name='post_comment'),
  path('product/<int:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
path('product/<int:product_id>/mark-out-of-stock/', views.mark_out_of_stock, name='mark_out_of_stock'),
   path('campaign/<int:campaign_id>/engagement/', views.campaign_engagement_data, name='campaign_engagement'),
    path('landing/', views.explore_campaigns, name='explore_campaigns'),
    path('verify/', views.verify_profile, name='verify_profile'),
    path('campaign/<int:campaign_id>/join_leave/', views.join_leave_campaign, name='join_leave_campaign'),
    path('campaign/<int:campaign_id>/joiners/', views.campaign_joiners, name='campaign_joiners'),

 path('edit/', views.edit_gif, name='edit_gif'),

    path('campaign/delete/<int:pk>/', CampaignDeleteView.as_view(), name='campaign-delete'),
    path('libraries/', views.library_affiliates, name='library_affiliates'),
    path('news/', views.news_affiliates, name='news_affiliates'),

    path('poster-canva/', views.poster_canva, name='poster_canva'),

    path('video-canva/', views.video_canva, name='video_canva'),

       path('login/', CustomLoginView.as_view(), name='login'),
  
    path('rallynex-logo/', views.rallynex_logo, name='rallynex_logo'),
   path('campaign/<int:campaign_id>/update_visibilit/', views.update_visibilit, name='update_visibilit'),

    path('subscribe/', views.subscribe, name='subscribe'),
    path('jobs/', views.jobs, name='jobs'),
    path('events/', views.events, name='events'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('project_support/', views.project_support, name='project_support'),

    path('campaign/<int:campaign_id>/top-participants/', views.top_participants_view, name='top_participants'),
     path('quran/', views.quran_view, name='quran_view'),
    path('adhkar/', views.adhkar_list, name='adhkar_list'),
    path('adhkar/<int:adhkar_id>/', views.adhkar_detail, name='adhkar_detail'),
       path('hadith/', views.hadith_list, name='hadith_list'),
    path('hadith/<int:hadith_id>/', views.hadith_detail, name='hadith_detail'),
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
    path('suggest/', views.suggest, name='suggest'),
  
    path('affiliate-links/', views.affiliate_links, name='affiliate_links'),

     path('platformfund/', views.platformfund_view, name='platformfund'),
   
    path('campaign/<int:campaign_id>/', views.view_campaign, name='view_campaign'),  # Corrected URL pattern
    path('update_visibility/<int:campaign_id>/', views.update_visibility, name='update_visibility'),
    path('update_hidden_links/', views.update_hidden_links, name='update_hidden_links'),
 path('upload/', views.upload_file, name='upload_file'),
      path('campaign/<int:campaign_id>/donate/', views.create_donation, name='create_donation'),
       path('campaign/<int:campaign_id>/join-sound-tribe/', views.join_sound_tribe, name='join_sound_tribe'),
    path('campaign/<int:campaign_id>/sound-tribe-data/', views.get_sound_tribe_data, name='get_sound_tribe_data'),
    path('search_profile_results/', views.search_profile_results, name='search_profile_results'),
    path('search/', views.search_campaign, name='search_campaign'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('create-chat/', views.create_chat, name='create_chat'),
   path('chat/<int:chat_id>/', ChatDetailView.as_view(), name='chat_detail'),
    path('user/chats/', views.user_chats, name='user_chats'),
    path('chat/<int:chat_id>/add_participants/', views.add_participants, name='add_participants'),
    path('chat/<int:chat_id>/remove_participants/', views.remove_participants, name='remove_participants'),
    path('chat/<int:chat_id>/delete/', views.delete_chat, name='delete_chat'),
    path('campaign/<int:campaign_id>/toggle-love/', views.toggle_love, name='toggle_love'),
    path('campaign/<int:campaign_id>/support/', views.support, name='support'),
    path('campaign/<int:campaign_id>/support-campaign/', views.campaign_support, name='campaign_support'),
    path('thank-you/', views.thank_you, name='thank_you'),
    path('home', views.home, name='home'),
    path('manage_campaigns/', views.manage_campaigns, name='manage_campaigns'),
    path('face', views.face, name='face'),
    path('create_campaign/', views.create_campaign, name='create_campaign'),
    path('edit-profile/<str:username>/', views.profile_edit, name='edit_profile'),
  path('user-profile/@<str:username>/', views.profile_view, name='profile_view'),
path('toggle_follow/', views.toggle_follow, name='toggle_follow'),
      path('follow_user/<int:user_id>/', views.follow_user, name='follow_user'),
    path('unfollow_user/<int:user_id>/', views.unfollow_user, name='unfollow_user'),
    path('followers/<str:username>/', views.follower_list, name='follower_list'),
    path('following/<str:username>/', views.following_list, name='following_list'),
    path('private-campaign/', views.private_campaign, name='private_campaign'),
    path('recreate-campaign/<int:campaign_id>/', views.recreate_campaign, name='recreate_campaign'),
     path('success/', views.success_page, name='success_page'),
    path('campaign/<int:campaign_id>/activity/create/', views.create_activity, name='create_activity'),
    path('campaign/<int:campaign_id>/activity_list/', views.activity_list, name='activity_list'),
    path('campaign/<int:campaign_id>/comments/', views.campaign_comments, name='campaign_comments'),
   path('like_dislike_comment/', views.like_dislike_comment, name='like_dislike_comment'),
path('post_comment/', views.post_comment, name='post_comment'),
path('get_comments/', views.get_comments, name='get_comments'),
path('get_replies/<int:comment_id>/', views.get_replies, name='get_replies'),
    path('record_campaign_view/<int:campaign_id>/', views.record_campaign_view, name='record_campaign_view'),
# marketing 
    path('blog/', views.blog_list, name='blog_list'),  # List of all blogs
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),  # Single blog post

    path('success-stories/', views.success_stories, name='success_stories'),
    path('campaign-stories/', campaign_story_list, name='campaign_story_list'),
    path('campaign-stories/<slug:slug>/', campaign_story_detail, name='campaign_story_detail'),
  
 path('chat/<int:chat_id>/send/', views.send_message, name='send_message'),
    path('testimonial/', views.testimonial, name='testimonial'),
 path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('project_support/', views.project_support, name='project_support'),
    path('hiw/', views.hiw, name='hiw'),
    path('faq/', views.faq_view, name='faq'),
     path('about/', views.aboutus, name='aboutus'),
         path('fund/', views.fund, name='fund'),
       path('geno/', views.geno, name='geno'),
      path('get_activity_comments/<int:activity_id>/', views.get_activity_comments, name='get_activity_comments'),
    path('post_activity_comment/', views.post_activity_comment, name='post_activity_comment'),
    path('like_activity_comment/', views.like_activity_comment, name='like_activity_comment'),
    path('post_comment_reply/', views.post_comment_reply, name='post_comment_reply'),
    path('get_comment_replies/<int:comment_id>/', views.get_comment_replies, name='get_comment_replies'),
    path('like_comment_reply/', views.like_comment_reply, name='like_comment_reply'),

    path('campaign/<int:campaign_id>/pledge/', views.create_pledge, name='create_pledge'), 
    path('campaign/<int:campaign_id>/pledgers/', views.campaign_pledgers_view, name='campaign_pledgers'),
# urls.py
path('pledge/<int:pledge_id>/toggle-fulfillment/', views.toggle_pledge_fulfillment, name='toggle_pledge_fulfillment'),

    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),


path('pledge-payment/<int:pledge_id>/', views.pledge_payment_page, name='pledge_payment_page'),
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


]












