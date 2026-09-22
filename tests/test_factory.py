import pytest

from tests.models import TestPost
from yello.db.factory import Factory


class PostFactory(Factory):
    model = TestPost

    def definition(self) -> dict:
        return {"title": "A post"}


class TestFactoryBase:
    def test_definition_not_implemented_by_default(self):
        with pytest.raises(NotImplementedError):
            Factory().definition()

    @pytest.mark.django_db
    def test_make_returns_unsaved_instance(self):
        post = PostFactory().make()
        assert post.title == "A post"
        assert post.pk is not None  # UUID assigned client-side by BaseModel
        assert not TestPost.objects.filter(pk=post.pk).exists()

    def test_make_applies_overrides(self):
        post = PostFactory().make(title="Custom")
        assert post.title == "Custom"

    @pytest.mark.django_db
    def test_create_persists_instance(self):
        post = PostFactory().create()
        assert TestPost.objects.filter(pk=post.pk).exists()
