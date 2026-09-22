from django.http import HttpResponse

from yello.http.middleware import Middleware


class BlockEverything(Middleware):
    def before(self, request):
        return HttpResponse("blocked", status=403)


class AddHeader(Middleware):
    def after(self, request, response):
        response["X-Test"] = "yes"
        return response


class TestMiddleware:
    def test_before_can_short_circuit(self):
        mw = BlockEverything(get_response=lambda request: HttpResponse("should not run"))
        response = mw(request=object())
        assert response.status_code == 403
        assert response.content == b"blocked"

    def test_after_can_mutate_response(self):
        mw = AddHeader(get_response=lambda request: HttpResponse("ok"))
        response = mw(request=object())
        assert response["X-Test"] == "yes"

    def test_default_passes_through(self):
        mw = Middleware(get_response=lambda request: HttpResponse("passthrough"))
        response = mw(request=object())
        assert response.content == b"passthrough"
