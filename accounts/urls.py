# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # Lazy-loaded section URLs
    path('section/trending/', views.section_trending, name='section_trending'),
    path('section/rising/', views.section_rising, name='section_rising'),
    path('section/fastest/', views.section_fastest, name='section_fastest'),
    path('section/completed/', views.section_most_completed, name='section_most_completed'),
    path('section/watched/', views.section_most_watched, name='section_most_watched'),
    path('section/saved/', views.section_most_saved, name='section_most_saved'),
    path('section/suggested/', views.section_suggested, name='section_suggested'),
    path('section/new/', views.section_new_causes, name='section_new_causes'),
    path('section/category/<str:category>/', views.section_category, name='section_category'),
    
    # Tracking URLs
    path('track-category-impression/', views.track_category_impression, name='track_category_impression'),
    path('track-featured-impression/', views.track_featured_impression, name='track_featured_impression'),
]