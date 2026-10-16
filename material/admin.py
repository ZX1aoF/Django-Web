from django.contrib import admin
from django.utils import timezone

from material.models import Category, Material


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "description")
    search_fields = ("name", "description")
    ordering = ("order", "id")


@admin.action(description="标记为已通过")
def approve_selected(modeladmin, request, queryset):
    queryset.update(status=Material.Status.APPROVED, reviewed_at=timezone.now())


@admin.action(description="标记为已驳回")
def reject_selected(modeladmin, request, queryset):
    queryset.update(status=Material.Status.REJECTED, reviewed_at=timezone.now())


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "author_display",
        "source",
        "updated_at",
    )
    list_filter = ("status", "category")
    search_fields = ("title", "source", "body")
    autocomplete_fields = ("category",)
    date_hierarchy = "created_at"
    actions = (approve_selected, reject_selected)

    @admin.display(description="提交人")
    def author_display(self, obj):
        return obj.author_name
