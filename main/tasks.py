# your_app/tasks.py
from celery import shared_task
from django.core.cache import cache
import time

@shared_task(bind=True, max_retries=3)
def fetch_content_background(self, imported_content_id):
    """Fetch and store real content in the background"""
    from .models import ImportedContent
    from .services.content_fetcher import ContentFetcher
    
    try:
        imported = ImportedContent.objects.get(id=imported_content_id)
        
        # Check if already processed
        if imported.processing_status == 'stored':
            return f"Content {imported.id} already stored"
        
        fetcher = ContentFetcher(imported)
        result = fetcher.fetch_and_store()
        return f"Successfully fetched content for {imported.id}"
        
    except ImportedContent.DoesNotExist:
        return f"Content {imported_content_id} not found"
        
    except Exception as e:
        # Retry with exponential backoff
        try:
            self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        except Exception:
            # Mark as failed after max retries
            try:
                imported = ImportedContent.objects.get(id=imported_content_id)
                imported.processing_status = 'failed'
                imported.processing_error = str(e)
                imported.save()
            except:
                pass
            return f"Failed: {e}"