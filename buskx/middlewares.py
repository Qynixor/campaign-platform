# File: /app/buskx/middlewares.py
from django.conf import settings
from django.http import HttpResponsePermanentRedirect

class LegalLinksMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.privacy_policy_link = settings.PRIVACY_POLICY_LINK
        request.terms_of_service_link = settings.TERMS_OF_SERVICE_LINK
        response = self.get_response(request)
        return response

class WWWRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for www.rallynex.com
        host = request.get_host()
        
        if host.startswith('www.'):
            # Remove www. and redirect permanently (301)
            new_host = host[4:]  # Remove 'www.'
            new_url = f"https://{new_host}{request.path}"
            
            # Preserve query parameters if any
            if request.GET:
                new_url += '?' + request.GET.urlencode()
                
            return HttpResponsePermanentRedirect(new_url)  # Fixed: removed extra ]
        
        return self.get_response(request)


# middleware.py
from django.db import connection
from django.db.utils import OperationalError
import time

class DatabaseHealthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check and refresh database connection if needed
        try:
            connection.ensure_connection()
        except OperationalError:
            # Connection is dead, close it and try to reconnect
            connection.close()
            try:
                connection.ensure_connection()
            except OperationalError as e:
                # Log the error but continue - views will handle it
                print(f"Database connection error: {e}")
        
        response = self.get_response(request)
        return response



# buskx/middleware.py
class ForceRemoveNoindexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Completely remove X-Robots-Tag if it exists
        if 'X-Robots-Tag' in response:
            del response['X-Robots-Tag']
        return response