import uuid

from django.db import models
from django.utils import timezone

from yello.db.managers import AllObjectsManager, SoftDeleteManager


class BaseModel(models.Model):
    """Abstract base for all Yello models.

    Provides a UUID primary key, ``created_at`` / ``updated_at`` timestamps and
    soft delete support. ``objects`` (the default manager) excludes soft-deleted
    rows; ``all_objects`` includes them.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, *, hard: bool = False):
        """Soft-delete by default; pass ``hard=True`` to remove the row."""
        if hard:
            return super().delete()
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}

    def restore(self) -> None:
        """Undo a soft delete."""
        if self.deleted_at is None:
            return
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_soft_deleted(self) -> bool:
        return self.deleted_at is not None
