# middlewares.py

from django.conf import settings


class LegalLinksMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.privacy_policy_link = settings.PRIVACY_POLICY_LINK
        request.terms_of_service_link = settings.TERMS_OF_SERVICE_LINK
        response = self.get_response(request)
        return response



# Create a file called middleware.py in your main Django app
# (the one containing settings.py)

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
                
            from django.http import HttpResponsePermanentRedirect
            return HttpResponsePermanentRedirect(new_url)
        
        return self.get_response(request)