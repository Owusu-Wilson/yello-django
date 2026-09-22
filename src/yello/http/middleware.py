"""Base for src/app/Http/Middleware classes."""


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def before(self, request):
        """Return an HttpResponse to short-circuit, or None to continue."""
        return None

    def after(self, request, response):
        """Return the (optionally mutated) response."""
        return response

    def __call__(self, request):
        early = self.before(request)
        if early is not None:
            return early
        response = self.get_response(request)
        return self.after(request, response)
