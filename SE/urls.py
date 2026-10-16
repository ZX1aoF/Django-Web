"""SE URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from user.views import home

urlpatterns = [
    # 首页：选择「学生 / 管理员」身份。命名用 index，避免与 user.urls 里的 login 重名
    path("", home, name="index"),
    path("admin/", admin.site.urls),
    path("user/", include("user.urls")),
    path("material/", include("material.urls")),
]

# 开发环境下由 Django 直接托管用户上传的素材附件；
# 正式部署时应交给 Nginx 之类的静态服务器处理。
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
