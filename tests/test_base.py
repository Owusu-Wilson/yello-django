from types import SimpleNamespace

import pytest
from django.contrib.admin import AdminSite
from django.test import RequestFactory
from rest_framework import status
from rest_framework.response import Response

from tests.models import TestPost
from yello.admin.base import BaseModelAdmin
from yello.auth.models import User
from yello.http.controller import Controller
from yello.policy.base import Policy


class TestController:
    def test_get_without_pk_maps_to_index(self):
        class IndexOnly(Controller):
            def index(self, request):
                return Response({"ok": True})

        factory = RequestFactory()
        response = IndexOnly.as_view()(factory.get("/"))
        assert response.data == {"ok": True}

    def test_get_with_pk_maps_to_show(self):
        class ShowOnly(Controller):
            def show(self, request, pk):
                return Response({"pk": pk})

        factory = RequestFactory()
        response = ShowOnly.as_view()(factory.get("/3/"), pk="3")
        assert response.data == {"pk": "3"}

    def test_post_maps_to_store(self):
        class StoreOnly(Controller):
            def store(self, request):
                return Response({"created": True}, status=status.HTTP_201_CREATED)

        factory = RequestFactory()
        response = StoreOnly.as_view()(factory.post("/"))
        assert response.status_code == status.HTTP_201_CREATED

    def test_put_maps_to_update(self):
        class UpdateOnly(Controller):
            def update(self, request, pk):
                return Response({"updated": pk})

        factory = RequestFactory()
        response = UpdateOnly.as_view()(factory.put("/3/"), pk="3")
        assert response.data == {"updated": "3"}

    def test_delete_maps_to_destroy(self):
        class DestroyOnly(Controller):
            def destroy(self, request, pk):
                return Response(status=status.HTTP_204_NO_CONTENT)

        factory = RequestFactory()
        response = DestroyOnly.as_view()(factory.delete("/3/"), pk="3")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_unimplemented_actions_raise(self):
        factory = RequestFactory()
        with pytest.raises(NotImplementedError):
            Controller.as_view()(factory.get("/"))


class TestPolicy:
    def test_before_default_returns_none(self):
        assert Policy().before("user") is None

    def test_direct_method_call(self):
        class OwnerPolicy(Policy):
            def update(self, user, obj):
                return obj["owner"] == user

        policy = OwnerPolicy()
        assert policy.update("me", {"owner": "me"}) is True
        assert policy.update("me", {"owner": "you"}) is False


class TestBaseModelAdmin:
    def _admin(self):
        return BaseModelAdmin(TestPost, AdminSite())

    def test_dynamic_list_display(self):
        request = SimpleNamespace(GET={})
        display = self._admin().get_list_display(request)
        assert "id" in display
        assert "created_at" in display
        assert "updated_at" in display
        assert "deleted_at" in display
        assert display[0] == "id"

    @pytest.mark.django_db
    def test_soft_delete_actions_and_filter(self):
        user = User.objects.create_superuser(email="admin@example.com", password="x")
        request = RequestFactory().get("/admin/")
        request.user = user
        admin = self._admin()
        actions = admin.get_actions(request)
        assert "hard_delete" in actions
        filters = admin.get_list_filter(request)
        assert "deleted_at" in filters