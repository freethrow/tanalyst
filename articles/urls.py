from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "articles"

urlpatterns = [
    # Home page - redirect to news or use a separate home view
    path("", views.ArticleListView.as_view(), name="home"),
    path("validated-unused/", views.ValidatedUnusedArticleListView.as_view(), name="validated-unused"),
    # About page - static template view
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    # Article detail page
    path("article/<str:pk>/", views.ArticleDetailView.as_view(), name="article_detail"),
    # Article edit page
    path("article/<str:pk>/edit/", views.ArticleEditView.as_view(), name="article_edit"),
    # Test Celery task trigger
    path("test-tasks/", views.test_tasks, name="test_tasks"),
    # Vector search page
    path("vector-search/", views.vector_search, name="vector_search"),
    # Sectors pages
    path("settori/", views.SectorListView.as_view(), name="sectors"),
    path("settori/<str:sector>/", views.SectorDetailView.as_view(), name="sector_detail"),
    # Email articles page
    path("invia-email/", views.SendArticlesEmailView.as_view(), name="send_email"),
]
