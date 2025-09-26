from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "articles"

urlpatterns = [
    # Home page - redirect to news or use a separate home view
    path("", views.ArticleListView.as_view(), name="home"),
    # About page - static template view
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    # Article detail page
    path("article/<str:pk>/", views.ArticleDetailView.as_view(), name="article_detail"),
]
