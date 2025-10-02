from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "articles"

urlpatterns = [
    # Home page - shows pending articles
    path("", views.ArticleListView.as_view(), name="home"),
    # Approved articles page - shows approved articles ready for email
    path("approved/", views.ApprovedArticleListView.as_view(), name="approved"),
    # Discarded articles page - shows discarded articles with restore option
    path("discarded/", views.DiscardedArticleListView.as_view(), name="discarded"),
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
    path("validate-article/<str:article_id>/", views.validate_article, name="validate_article"),
    path("discard-article/<str:article_id>/", views.discard_article, name="discard_article"),
    path("restore-article/<str:article_id>/", views.restore_article, name="restore_article"),
    path("reset-pending/", views.reset_all_articles_to_pending, name="reset_all_articles_to_pending"),
    path("set-language/", views.set_language, name="set_language"),
    path("remove-embeddings/", views.remove_all_embeddings, name="remove_all_embeddings"),
    path("embedding-management/", views.embedding_management, name="embedding_management"),
    path("generate-summary/", views.generate_summary, name="generate_summary"),
    path("weekly-summaries/", views.weekly_summaries_list, name="weekly_summaries"),
    path("weekly-summary/<str:summary_id>/", views.weekly_summary_detail, name="weekly_summary_detail"),
]
