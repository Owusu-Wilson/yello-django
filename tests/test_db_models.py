import uuid

import pytest

from tests.models import TestPost
from yello.auth.models import User


@pytest.mark.django_db
class TestBaseModel:
    def test_create_sets_uuid_pk_and_timestamps(self):
        post = TestPost.objects.create(title="hello")
        assert isinstance(post.id, uuid.UUID)
        assert post.created_at is not None
        assert post.updated_at is not None
        assert post.deleted_at is None
        assert post.is_soft_deleted is False

    def test_id_is_not_editable(self):
        field = TestPost._meta.get_field("id")
        assert field.editable is False
        assert field.primary_key is True

    def test_default_manager_excludes_soft_deleted(self):
        post = TestPost.objects.create(title="x")
        post.delete()
        assert TestPost.objects.count() == 0
        assert TestPost.all_objects.count() == 1

    def test_soft_delete_sets_deleted_at(self):
        post = TestPost.objects.create(title="x")
        post.delete()
        assert post.deleted_at is not None
        assert post.is_soft_deleted is True
        post.refresh_from_db()
        assert post.deleted_at is not None

    def test_soft_delete_returns_django_tuple(self):
        post = TestPost.objects.create(title="x")
        result = post.delete()
        assert isinstance(result, tuple)
        assert result[0] == 1

    def test_hard_delete_removes_row(self):
        post = TestPost.objects.create(title="x")
        post.delete(hard=True)
        assert TestPost.all_objects.count() == 0

    def test_restore_clears_deleted_at(self):
        post = TestPost.objects.create(title="x")
        post.delete()
        post.restore()
        assert post.deleted_at is None
        assert TestPost.objects.count() == 1
        assert post.is_soft_deleted is False

    def test_restore_on_non_deleted_is_noop(self):
        post = TestPost.objects.create(title="x")
        post.restore()
        assert post.deleted_at is None
        assert TestPost.objects.count() == 1

    def test_soft_delete_is_bulk_safe(self):
        TestPost.objects.create(title="a")
        TestPost.objects.create(title="b")
        TestPost.objects.delete()
        assert TestPost.objects.count() == 0
        assert TestPost.all_objects.count() == 2


@pytest.mark.django_db
class TestManagers:
    def test_queryset_soft_delete(self):
        a = TestPost.objects.create(title="a")
        b = TestPost.objects.create(title="b")
        TestPost.objects.delete()
        a.refresh_from_db()
        b.refresh_from_db()
        assert a.deleted_at is not None
        assert b.deleted_at is not None

    def test_queryset_hard_delete(self):
        TestPost.objects.create(title="a")
        TestPost.objects.hard_delete()
        assert TestPost.all_objects.count() == 0

    def test_queryset_restore(self):
        TestPost.objects.create(title="a")
        TestPost.objects.create(title="b")
        TestPost.objects.delete()
        assert TestPost.objects.count() == 0
        TestPost.all_objects.restore()
        assert TestPost.objects.count() == 2
        assert TestPost.all_objects.count() == 2


@pytest.mark.django_db
class TestYelloUserManager:
    def test_create_user(self):
        user = User.objects.create_user(email="a@example.com", password="secret123")
        assert user.email == "a@example.com"
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("secret123")
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email=None, password="secret123")

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="root@example.com", password="secret123")
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_create_superuser_forces_staff_and_superuser(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="x@example.com", password="p", is_staff=False)
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="x@example.com", password="p", is_superuser=False)

    def test_user_model_settings(self):
        assert User.USERNAME_FIELD == "email"
        assert User.REQUIRED_FIELDS == []