from django.http import HttpResponsePermanentRedirect


class NonWWWRedirectMiddleware:
    """
    Redirect www.rallynex.com to rallynex.com
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        
        # Redirect www to non-www
        if host.startswith('www.'):
            new_host = host[4:]  # Remove 'www.'
            new_url = request.build_absolute_uri().replace(host, new_host)
            return HttpResponsePermanentRedirect(new_url)
        
        return self.get_response(request)