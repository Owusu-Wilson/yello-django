from django.db import models

from yello.db.models import BaseModel


class TestPost(BaseModel):
    __test__ = False  # don't let pytest collect this as a test class

    title = models.CharField(max_length=255)
    owner = models.ForeignKey(
        "yello_auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )

    class Meta:
        app_label = "tests"