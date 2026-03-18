# boost_utils.py
from django.utils import timezone
from django.db.models import Count, Q
from .models import BoostedJourney, Campaign, BoostedJourneyImpression, BoostedJourneyClick
import random

def get_featured_spot_campaigns(limit=5, exclude_campaign_ids=None):
    """
    Get campaigns for featured spot (right sidebar)
    Weighted rotation: higher flat_fee = more visibility
    """
    now = timezone.now()
    
    # Get active featured boosts - ONLY 'featured' placement, NOT bundle
    featured_boosts = BoostedJourney.objects.filter(
        placement_type='featured',  # ← Only featured, no bundle
        status='active',
        is_paid=True,
        start_date__lte=now,
        end_date__gte=now
    ).select_related('campaign__user__user')
    
    boosted_campaigns = []
    weighted_pool = []
    
    # Create weighted pool based on flat_fee
    for boost in featured_boosts:
        if exclude_campaign_ids and boost.campaign_id in exclude_campaign_ids:
            continue
            
        # Add to result list
        boosted_campaigns.append({
            'campaign': boost.campaign,
            'type': 'boosted',
            'boost': boost,
            'reason': 'featured_boost',
            'weight': int(boost.flat_fee / 10) or 1  # Every $10 = 1 weight
        })
        
        # Add to weighted pool for selection
        weight = int(boost.flat_fee / 10) or 1
        weighted_pool.extend([boost] * weight)
    
    # Select from weighted pool without duplicates
    selected_boosts = []
    selected_ids = set()
    
    if weighted_pool:
        random.shuffle(weighted_pool)
        for boost in weighted_pool:
            if len(selected_boosts) >= len(boosted_campaigns):
                break
            if boost.id not in selected_ids:
                selected_boosts.append(boost)
                selected_ids.add(boost.id)
    
    # Reorder boosted_campaigns based on weighted selection
    if selected_boosts:
        boost_order = {b.id: i for i, b in enumerate(selected_boosts)}
        boosted_campaigns.sort(key=lambda x: boost_order.get(x['boost'].id, 999))
    
    # If we need more campaigns to reach limit, get most relevant organic campaigns
    if len(boosted_campaigns) < limit:
        existing_ids = [item['campaign'].id for item in boosted_campaigns]
        if exclude_campaign_ids:
            existing_ids.extend(exclude_campaign_ids)
        
        organic_needed = limit - len(boosted_campaigns)
        
        organic_campaigns = Campaign.objects.filter(
            is_active=True
        ).exclude(
            id__in=existing_ids
        ).annotate(
            relevance_score=Count('loves') + Count('comments') * 2
        ).order_by('-relevance_score', '-timestamp')[:organic_needed]
        
        for campaign in organic_campaigns:
            boosted_campaigns.append({
                'campaign': campaign,
                'type': 'organic',
                'reason': 'trending'
            })
    
    return boosted_campaigns[:limit]


def get_search_boosts(search_terms):
    """
    Get search boosts ordered by: bids first (highest), then flat fees (highest)
    """
    from .models import BoostedJourney
    from django.utils import timezone
    from django.db.models import Q
    
    now = timezone.now()
    
    # Split search terms
    if isinstance(search_terms, str):
        search_words = search_terms.lower().split()
    else:
        search_words = search_terms
    
    # Build keyword query
    keyword_queries = Q()
    for word in search_words:
        keyword_queries |= Q(keywords__icontains=word)
    
    # Get all matching boosts - ONLY 'search' placement
    all_boosts = BoostedJourney.objects.filter(
        placement_type='search',  # ← Only search
        status='active',
        is_paid=True,
        start_date__lte=now,
        end_date__gte=now
    ).filter(keyword_queries).select_related('campaign__user__user')
    
    # Separate and order
    bid_boosts = all_boosts.filter(bid_amount__gt=0).order_by('-bid_amount')
    flat_boosts = all_boosts.filter(bid_amount=0, flat_fee__gt=0).order_by('-flat_fee')
    
    # Format results
    results = []
    
    for boost in bid_boosts:
        results.append({
            'campaign': boost.campaign,
            'boost': boost,
            'type': 'sponsored',
            'payment_type': 'bid',
            'amount': boost.bid_amount
        })
    
    for boost in flat_boosts:
        results.append({
            'campaign': boost.campaign,
            'boost': boost,
            'type': 'sponsored',
            'payment_type': 'flat',
            'amount': boost.flat_fee
        })
    
    return results


def get_category_boosts(category, limit=3):
    """
    Get category page boosts ordered by flat_fee (highest first)
    """
    from .models import BoostedJourney
    from django.utils import timezone
    
    now = timezone.now()
    
    boosts = BoostedJourney.objects.filter(
        placement_type='category',  # ← Only category
        status='active',
        is_paid=True,
        start_date__lte=now,
        end_date__gte=now,
        categories__icontains=category
    ).order_by('-flat_fee')[:limit].select_related('campaign__user__user')
    
    results = []
    for boost in boosts:
        results.append({
            'campaign': boost.campaign,
            'boost': boost,
            'type': 'sponsored',
            'amount': boost.flat_fee
        })
    
    return results


def record_boost_impression(boost, request, placement_context):
    """Record an impression for analytics"""
    try:
        impression = BoostedJourneyImpression.objects.create(
            boosted_journey=boost,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            placement_context=placement_context
        )
        # Update counter on boost
        boost.impressions += 1
        boost.last_impression_at = timezone.now()
        boost.save(update_fields=['impressions', 'last_impression_at'])
        return impression
    except Exception as e:
        print(f"Error recording impression: {e}")
        return None


def record_boost_click(boost, request, placement_context):
    """Record a click for analytics"""
    try:
        click = BoostedJourneyClick.objects.create(
            boosted_journey=boost,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            placement_context=placement_context
        )
        # Update counter on boost
        boost.clicks += 1
        boost.last_click_at = timezone.now()
        boost.save(update_fields=['clicks', 'last_click_at'])
        return click
    except Exception as e:
        print(f"Error recording click: {e}")
        return None