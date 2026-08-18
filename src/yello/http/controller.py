from rest_framework.views import APIView


class Controller(APIView):
    """Base class for all generated controllers.

    This is sugar over DRF's dispatch — not a replacement. Subclasses implement
    Laravel-style action methods (``index``/``store``/``show``/``update``/
    ``destroy``), which this class maps onto DRF's ``get``/``post``/``put``/
    ``delete`` under the hood. Subclasses can still drop down to raw DRF
    ``Request``/``Response`` objects at any time.
    """

    def index(self, request):
        raise NotImplementedError

    def store(self, request):
        raise NotImplementedError

    def show(self, request, pk):
        raise NotImplementedError

    def update(self, request, pk):
        raise NotImplementedError

    def destroy(self, request, pk):
        raise NotImplementedError

    def get(self, request, pk=None, *args, **kwargs):
        return self.show(request, pk) if pk else self.index(request)

    def post(self, request, *args, **kwargs):
        return self.store(request)

    def put(self, request, pk, *args, **kwargs):
        return self.update(request, pk)

    def delete(self, request, pk, *args, **kwargs):
        return self.destroy(request, pk)