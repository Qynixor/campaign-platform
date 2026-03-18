# main/context_processors.py
from .boost_utils import get_featured_spot_campaigns, record_boost_impression

def featured_spot_processor(request):
    """
    Context processor to add featured spot campaigns to ALL templates automatically
    """
    featured_spot_campaigns = get_featured_spot_campaigns(limit=5)
    
    # Record impressions
    for item in featured_spot_campaigns:
        if item.get('type') == 'boosted' and 'boost' in item:
            record_boost_impression(
                item['boost'],
                request,
                'featured_spot_sidebar'
            )
    
    return {
        'featured_spot_campaigns': featured_spot_campaigns
    }