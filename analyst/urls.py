from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from articles import views as articles_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", articles_views.login_view, name="login"),
    path("logout/", articles_views.logout_view, name="logout"),
    path("", include("articles.urls", namespace="articles")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
