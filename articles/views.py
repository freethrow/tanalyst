from .models import Article
from django.views.generic import ListView, DetailView
from django.conf import settings


print(settings.GROQ_API_KEY)  # Debugging line to check if the key is loaded correctly


class ArticleListView(ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Get the queryset for the view, filtering out articles that have no Italian title.
        """
        queryset = self.model.objects.exclude(title_it__isnull=True)
        return queryset.order_by("-time_translated")


class ArticleDetailView(DetailView):
    model = Article
    template_name = "article_detail.html"
    context_object_name = "article"
