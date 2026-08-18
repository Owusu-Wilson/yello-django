from django.contrib import admin


class BaseModelAdmin(admin.ModelAdmin):
    """Admin base with a dynamic ``list_display`` and soft-delete helpers.

    If ``list_display`` is left empty it is derived from the model's fields
    (id, timestamps first, then everything else). When the model has a
    ``deleted_at`` column a soft-delete filter is added and a bulk
    "Hard delete selected objects" action is exposed.
    """

    list_display = ()

    def _supports_soft_delete(self):
        return "deleted_at" in [f.name for f in self.model._meta.fields]

    def get_list_display(self, request):
        if self.list_display:
            return self.list_display
        names = [f.name for f in self.model._meta.fields]
        ordered = [n for n in ("id", "created_at", "updated_at", "deleted_at") if n in names]
        remaining = [n for n in names if n not in ordered]
        return ordered + remaining

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        if self._supports_soft_delete():
            filters.append("deleted_at")
        return filters

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self._supports_soft_delete():
            actions["hard_delete"] = self.get_action("hard_delete")
        return actions

    @admin.action(description="Hard delete selected objects")
    def hard_delete(self, request, queryset):
        queryset.hard_delete()