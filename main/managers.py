# managers.py
from django.db import models
from django.utils import timezone
from django.db.models import Q, Case, When, Value, IntegerField

class BoostedJourneyManager(models.Manager):
    def get_active_for_placement(self, placement_type):
        """Get all active boosts for a specific placement"""
        now = timezone.now()
        return self.filter(
            placement_type=placement_type,
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        )
    
    def get_search_boosts(self, search_terms):
        """
        Get active search boosts matching keywords
        Returns queryset ordered by bid_amount (highest first)
        """
        now = timezone.now()
        
        # Split search terms into list
        if isinstance(search_terms, str):
            search_words = search_terms.lower().split()
        else:
            search_words = search_terms
        
        # Build Q objects for keyword matching
        keyword_queries = Q()
        for word in search_words:
            keyword_queries |= Q(keywords__icontains=word)
        
        return self.filter(
            placement_type='search',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        ).filter(keyword_queries).order_by('-bid_amount')
    
    def get_featured_boosts(self, limit=5):
        """Get active featured section boosts"""
        now = timezone.now()
        return self.filter(
            placement_type='featured',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        ).order_by('?')[:limit]  # Random order for variety
    
    def get_category_boosts(self, category):
        """Get active category page boosts for specific category"""
        now = timezone.now()
        return self.filter(
            placement_type='category',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now,
            categories__icontains=category
        ).order_by('-created_at')
    
    def get_bundled_boosts(self):
        """Get active bundle placements"""
        now = timezone.now()
        return self.filter(
            placement_type='bundle',
            status='active',
            is_paid=True,
            start_date__lte=now,
            end_date__gte=now
        )