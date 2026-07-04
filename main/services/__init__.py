# main/services/__init__.py

# Remove the content_fetcher import (not needed for documentation-first site)
# from .content_fetcher import ContentFetcher

# Import the FAQ service
from .faq_service import get_ai_response

__all__ = ['get_ai_response']