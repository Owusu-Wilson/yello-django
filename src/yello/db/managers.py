from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that soft-deletes rows in bulk instead of dropping them."""

    def delete(self):
        """Soft-delete every row in the queryset (updates ``deleted_at``)."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently remove every row in the queryset."""
        return super().delete()

    def restore(self):
        """Clear ``deleted_at`` on every row in the queryset."""
        return self.update(deleted_at=None)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Manager that includes soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset()
