"""material 应用的路由。

所有路由都带 ``<slug:kind>``，与页面上的身份视图保持一致；
具体权限由视图上的 ``require_person`` 装饰器判定。
"""

from django.urls import path

from material import views

urlpatterns = [
    path("<slug:kind>/", views.home, name="material"),
    path("<slug:kind>/create", views.create, name="material_create"),
    path("<slug:kind>/detail/<int:pk>", views.detail, name="material_detail"),
    path("<slug:kind>/edit/<int:pk>", views.edit, name="material_edit"),
    path("<slug:kind>/delete/<int:pk>", views.delete, name="material_delete"),
]
