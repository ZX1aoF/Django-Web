"""user 应用的路由。

命名约定：``login`` / ``register`` 不带参数时是「选择身份」页，
带 ``kind`` 参数的分别是 ``login_detail`` / ``register_detail``。
"""

from django.urls import path

from user import views

urlpatterns = [
    path("login/", views.home, name="login"),
    path("login/<slug:kind>", views.login, name="login_detail"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.register_home, name="register"),
    path("register/<slug:kind>", views.register, name="register_detail"),
    path("update/<slug:kind>", views.update, name="update"),
]
