from django.contrib import admin

from material.models import Category, Material


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "description")
    search_fields = ("name", "description")
    ordering = ("order", "id")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "source", "created_by", "updated_at")
    list_filter = ("category",)
    search_fields = ("title", "source", "body")
    autocomplete_fields = ("category",)
    date_hierarchy = "created_at"
