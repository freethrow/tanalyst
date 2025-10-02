from .models import Article
from django.views.generic import ListView, DetailView, UpdateView, FormView
from django.db import models
from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from django.contrib import messages
from django.urls import reverse_lazy

from django.views.decorators.http import require_POST


from analyst.emails.notifications import send_latest_articles_email
from analyst.agents.translator import translate_untranslated_articles
from .forms import EmailArticlesForm
from django.conf import settings
from .tasks import scrape_ekapija, scrape_biznisrs, create_all_embeddings

VOYAGEAI_API_KEY = settings.VOYAGEAI_API_KEY

# Hardcoded sectors list
SECTORS = [
    "Abbigliamento e tessili",
    "Imprese edili per il restauro",
    "Piastrelle in ceramica",
    "Aerospazio",
    "Industria enologica",
    "Prodotti chimici",
    "Agro-alimentare",
    "Informatica",
    "Prodotti di gomma e plastica",
    "Apparecchiature e materiali per la sicurezza",
    "Infrastrutture",
    "Prodotti farmaceutici e relative materie prime",
    "Architettura e urbanistica",
    "Infrastrutture e sovrastrutture per strade ferrate",
    "Prodotti siderurgici",
    "Articoli decorativi e da regalo",
    "Intersettoriale",
    "Pulizia, disinfezione e disinfestazione",
    "Articoli per la casa e arredamento",
    "Istruzione e formazione",
    "Raccolta e smaltimento dei rifiuti",
    "Articoli per l'illuminazione",
    "Macchinari",
    "Restauro architettonico e strutturale",
    "Articoli sportivi e abbigliamento per lo sport",
    "Macchine agricole e per l'orticoltura",
    "Restauro artistico e storico",
    "Attrezzature aeronautiche ed aeroportuali",
    "Macchine confezionatrici",
    "Restauro monumentale museale e archeologico",
    "Attrezzature per alberghi, ristoranti e bar",
    "Macchine per la lavorazione del legno",
    "Ricerca e sviluppo",
    "Biotecnologie",
    "Macchine per la lavorazione della gomma e della plastica",
    "Riparazione e manutenzione",
    "Carta, tipografia, editoria e cartoleria",
    "Macchine per la produzione di gioielli",
    "Servizi commerciali",
    "Cinematografia",
    "Macchine per l'edilizia e per la produzione di materiali edili",
    "Servizi di sicurezza",
    "Consulenza e esperti",
    "Macchine per l'industria alimentare",
    "Servizi di telecomunicazione",
    "Cosmetici e prodotti per l'igiene personale",
    "Macchine per l'industria della carta e delle arti grafiche",
    "Servizi diversi",
    "E-commerce",
    "Macchine per l'industria delle calzature e della pelletteria",
    "Servizi finanziari",
    "Edilizia: Lavori e costruzioni",
    "Macchine per l'industria tessile",
    "Servizi informatici",
    "Elettrodomestici",
    "Macchine utensili per la lavorazione dei metalli",
    "Servizi tecnici",
    "Elettronica di consumo",
    "Materiali per l'edilizia",
    "Strumenti musicali",
    "Elettronica industriale e professionale",
    "Meccatronica",
    "Studi di architettura",
    "Energia",
    "Minerali e metalli",
    "Studi di ingegneria",
    "Energia elettrica",
    "Nanotecnologie",
    "Subfornitura",
    "Formazione",
    "Nautica",
    "Televisori e radio, audiovisivi",
    "Gas e energie alternative",
    "Non catalogabile merceologicamente",
    "Trasporti e logistica",
    "Gioielli e bigiotteria",
    "Ottica",
    "Turismo",
    "Impianti anti-inquinamento",
    "Pelli ed articoli di pelletteria",
    "Veicoli, industria meccanica, elettrotecnica ed elettronica",
    "Impianti di telecomunicazione",
    "Petrolio e derivati",
    "Vino e altre bevande",
    "Economia in generale",
]


class ArticleListView(ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Get the queryset for pending articles (not yet approved/discarded).
        """
        queryset = Article.objects.filter(
            title_it__isnull=False,
            content_it__isnull=False,
            status=Article.PENDING,
        ).exclude(
            title_it__exact="",
            content_it__exact="",
        )
        return queryset.order_by("-article_date")


class ApprovedArticleListView(ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Get the queryset for approved articles that haven't been sent yet.
        """
        queryset = Article.objects.filter(
            title_it__isnull=False,
            content_it__isnull=False,
            status=Article.APPROVED,
        ).exclude(
            title_it__exact="",
            content_it__exact="",
        )
        return queryset.order_by("-time_translated")


class DiscardedArticleListView(ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"

    def get_queryset(self):
        """
        Get the queryset for discarded articles.
        """
        queryset = Article.objects.filter(
            title_it__isnull=False,
            content_it__isnull=False,
            status=Article.DISCARDED,
        ).exclude(
            title_it__exact="",
            content_it__exact="",
        )
        return queryset.order_by("-time_translated")


@require_POST
def validate_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get('HX-Request'):
        return HttpResponse(status=400)  # Bad request if not HTMX
    
    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_approved()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)

@require_POST
def discard_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get('HX-Request'):
        return HttpResponse(status=400)  # Bad request if not HTMX
    
    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_discarded()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)

@require_POST
def restore_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get('HX-Request'):
        return HttpResponse(status=400)  # Bad request if not HTMX
    
    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_pending()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)

def reset_all_articles_to_pending(request):
    """Reset all articles to PENDING status for testing purposes."""
    Article.objects.update(status=Article.PENDING)
    return HttpResponse("All articles reset to PENDING status")

def set_language(request):
    """Simple language switcher using session storage."""
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    
    if request.method == 'POST':
        language = request.POST.get('language', 'it')
        next_url = request.POST.get('next', '/')
        
        # Store language preference in session
        request.session['language'] = language
        
        # Redirect back to the page they came from
        return HttpResponseRedirect(next_url)
    
    # If not POST, redirect to home
    return HttpResponseRedirect('/')

class ArticleDetailView(DetailView):
    model = Article
    template_name = "article_detail.html"
    context_object_name = "article"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object
        related = []
        try:
            # Use existing embedding only; if missing, skip
            query_vector = getattr(article, "embedding", None)
            print(
                f"DEBUG: Article {article.id} has embedding: {query_vector is not None}"
            )
            print(
                f"DEBUG: Article fields: {[field.name for field in article._meta.get_fields()]}"
            )

            # If no embedding field, try to get some related articles by other means
            if query_vector is None:
                print(
                    "DEBUG: No embedding found, getting related by same sector/source"
                )
                # Get articles from same sector or source as fallback
                fallback_related = (
                    Article.objects.filter(
                        models.Q(sector=article.sector)
                        | models.Q(source=article.source)
                    )
                    .exclude(id=article.id)
                    .exclude(title_it__isnull=True)[:6]
                )

                related = []
                for art in fallback_related:
                    related.append(
                        {
                            "id": str(art.id),
                            "title_it": art.title_it or art.title_en,
                        }
                    )
                print(f"DEBUG: Found {len(related)} fallback related articles")
            elif query_vector is not None:
                cache_key = f"related:{article.id}"
                cached_related = cache.get(cache_key)
                if cached_related is not None:
                    context["related_articles"] = cached_related
                    return context

                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": "article_vector_index",
                            "path": "embedding",
                            "queryVector": query_vector,
                            "numCandidates": 50,
                            "limit": 10,
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "score": {"$meta": "vectorSearchScore"},
                            "title_it": 1,
                            "title_en": 1,
                        }
                    },
                ]

                results = list(Article.objects.raw_aggregate(pipeline))

                current_id_str = str(getattr(article, "id", ""))
                processed = []
                for r in results:
                    if isinstance(r, dict):
                        rid = str(r.get("_id", ""))
                        if rid and rid != current_id_str:
                            processed.append(
                                {
                                    "id": rid,
                                    "title_it": r.get("title_it") or r.get("title_en"),
                                }
                            )
                    else:
                        rid = str(getattr(r, "id", getattr(r, "_id", "")))
                        if rid and rid != current_id_str:
                            processed.append(
                                {
                                    "id": rid,
                                    "title_it": getattr(r, "title_it", None)
                                    or getattr(r, "title_en", None),
                                }
                            )

                related = processed[:6]
                print(f"DEBUG: Found {len(related)} related articles")
                if related:
                    cache.set(cache_key, related, 60 * 10)
                else:
                    cache.delete(cache_key)
        except Exception as e:
            # Fail quietly; do not block detail page
            print(f"Related articles error: {e}")

        context["related_articles"] = related
        print(f"DEBUG: Setting {len(related)} related articles in context")
        return context


def test_tasks(request):
    # translate_untranslated_articles.delay()
    
    create_all_embeddings.delay()
    return HttpResponse("Task has been triggered.")


def vector_search(request):
    if request.method == "POST":
        query = request.POST.get("query", "").strip()
        # If query is empty, return empty results quickly
        is_htmx = (
            request.headers.get("HX-Request") == "true"
            or request.headers.get("Hx-Request") == "true"
        )
        if not query:
            if is_htmx:
                return render(
                    request, "partials/vector_search_results.html", {"results": []}
                )
            return render(
                request, "vector_search.html", {"results": [], "query": query}
            )
        if query:
            import voyageai

            # Initialize Voyage client
            voyage_client = voyageai.Client(api_key=VOYAGEAI_API_KEY)

            try:
                query_embedding = voyage_client.embed(
                    [query], model="voyage-3.5-lite", input_type="query"
                ).embeddings[0]
            except Exception as e:
                print(f"Error generating query embedding: {e}")
                if is_htmx:
                    # Return an empty results grid; page will still show the error if needed in full render
                    return render(
                        request, "partials/vector_search_results.html", {"results": []}
                    )
                return render(
                    request,
                    "vector_search.html",
                    {"results": [], "query": query, "error": str(e)},
                )

            # MongoDB Atlas Vector Search aggregation
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "article_vector_index",  # Make sure this index exists
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": 50,
                        "limit": 18,
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "score": {"$meta": "vectorSearchScore"},
                        "title_en": 1,
                        "title_it": 1,
                        "content_en": 1,
                        "content_it": 1,
                        "sector": 1,
                        "source": 1,
                        "date": 1,
                        "url": 1,
                        "status": 1,
                        "score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]

            # Execute aggregation without view-level caching
            results = list(Article.objects.raw_aggregate(pipeline))

            print("Raw results:", results)

            # Normalize results: handle both dicts and Article instances
            processed_results = []
            for result in results:
                if isinstance(result, dict):
                    item = dict(result)
                    # Convert score to percentage (0-100)
                    try:
                        item["score"] = float(item.get("score", 0)) * 100
                    except (TypeError, ValueError):
                        item["score"] = 0
                    # Convert ObjectId to string for template
                    if "_id" in item:
                        item["_id"] = str(item["_id"])
                        # Also provide a generic 'id' for URL reversing
                        item["id"] = item["_id"]
                    processed_results.append(item)
                else:
                    # It's likely an Article instance; map needed fields into a dict
                    item = {
                        "_id": str(getattr(result, "_id", getattr(result, "id", ""))),
                        "title_en": getattr(result, "title_en", None),
                        "title_it": getattr(result, "title_it", None),
                        "content_en": getattr(result, "content_en", None),
                        "content_it": getattr(result, "content_it", None),
                        "sector": getattr(result, "sector", None),
                        "source": getattr(result, "source", None),
                        "date": getattr(result, "date", None),
                        "url": getattr(result, "url", None),
                    }
                    # Provide 'id' for URL reversing
                    item["id"] = getattr(result, "id", item["_id"]) or item["_id"]
                    # Score might be present as an annotated attribute
                    try:
                        item["score"] = float(getattr(result, "score", 0)) * 100
                    except (TypeError, ValueError):
                        item["score"] = 0
                    processed_results.append(item)
            print(processed_results)

            if is_htmx:
                return render(
                    request,
                    "partials/vector_search_results.html",
                    {"results": processed_results},
                )
            return render(
                request,
                "vector_search.html",
                {"results": processed_results, "query": query},
            )

    return render(request, "vector_search.html")


class ArticleEditView(UpdateView):
    """
    Class-based view for editing articles.
    Allows editing of all article fields including titles, content, metadata, and status flags.
    Dynamically includes Serbian fields when English fields are not available.
    """

    model = Article
    template_name = "article_edit.html"
    context_object_name = "article"

    def get_form_class(self):
        """Create form class with only Italian fields editable, original fields as read-only."""
        article = self.get_object()

        # Italian fields and status field are editable
        fields = ["title_it", "content_it", "status"]

        # Create form widgets
        form_widgets = {
            "content_it": forms.Textarea(attrs={"rows": 20, "class": "min-h-[400px]"}),
        }

        # Create Meta class dynamically
        Meta = type(
            "Meta", (), {"model": Article, "fields": fields, "widgets": form_widgets}
        )

        # Create form class dynamically
        DynamicArticleForm = type(
            "DynamicArticleForm", (forms.ModelForm,), {"Meta": Meta}
        )

        return DynamicArticleForm

    def get_success_url(self):
        """Redirect to the article detail page after successful edit."""
        return reverse_lazy("articles:article_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        """Handle successful form submission."""
        title = (
            self.object.title_it
            or getattr(self.object, "title_en", None)
            or getattr(self.object, "title_rs", None)
            or "Untitled"
        )
        messages.success(
            self.request, f'Article "{title}" has been updated successfully.'
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle form validation errors."""
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        """Add extra context for the template."""
        context = super().get_context_data(**kwargs)
        article = self.object

        # Determine source language and content
        has_english = bool(
            getattr(article, "title_en", None) or getattr(article, "content_en", None)
        )
        has_serbian = bool(
            getattr(article, "title_rs", None) or getattr(article, "content_rs", None)
        )

        if has_english:
            context["source_language"] = "English"
            context["source_title"] = getattr(article, "title_en", "")
            context["source_content"] = getattr(article, "content_en", "")
        elif has_serbian:
            context["source_language"] = "Serbian"
            context["source_title"] = getattr(article, "title_rs", "")
            context["source_content"] = getattr(article, "content_rs", "")
        else:
            context["source_language"] = None
            context["source_title"] = ""
            context["source_content"] = ""

        # Page title
        title = (
            article.title_it
            or getattr(article, "title_en", None)
            or getattr(article, "title_rs", None)
            or "Untitled"
        )
        context["page_title"] = f"Edit: {title}"

        return context


class SectorListView(ListView):
    """
    View to display all available sectors.
    """

    template_name = "sectors.html"
    context_object_name = "sectors"

    def get_queryset(self):
        """Return the list of sectors with article counts."""
        sectors_with_counts = []
        for sector in SECTORS:
            count = (
                Article.objects.filter(sector=sector, content_it__isnull=False)
                .exclude(content_it__exact="")
                .count()
            )
            sectors_with_counts.append({"name": sector, "count": count})
        return sectors_with_counts


class SectorDetailView(ListView):
    """
    View to display articles for a specific sector.
    """

    model = Article
    template_name = "sector_detail.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        """Get articles for the specified sector."""
        sector = self.kwargs["sector"]
        return (
            Article.objects.filter(sector=sector, content_it__isnull=False)
            .exclude(content_it__exact="")
            .order_by("-time_translated")
        )

    def get_context_data(self, **kwargs):
        """Add sector name to context."""
        context = super().get_context_data(**kwargs)
        context["sector"] = self.kwargs["sector"]
        context["sector_exists"] = self.kwargs["sector"] in SECTORS
        return context


class SendArticlesEmailView(FormView):
    """
    View for sending latest articles via email.
    """

    template_name = "send_email.html"
    form_class = EmailArticlesForm
    success_url = reverse_lazy("articles:home")

    def form_valid(self, form):
        """Process the form and start the email task."""
        email = form.cleaned_data["email"]
        num_articles = form.cleaned_data["num_articles"]
        subject = form.cleaned_data.get("subject") or None

        # Start the email task asynchronously
        try:
            send_latest_articles_email.delay(
                recipient_email=email, subject=subject, num_articles=num_articles
            )

            # Success message
            messages.success(
                self.request,
                f"Email will be sent to {email} with {num_articles} articles",
            )

        except Exception as e:
            # Error message
            messages.error(self.request, f"Error scheduling email: {str(e)}")

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add extra context for the template."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Invia Articoli via Email"

        # Count approved articles ready to be sent
        approved_articles = Article.objects.filter(
            status=Article.APPROVED,
            title_it__isnull=False,
            content_it__isnull=False
        ).exclude(
            title_it__exact="",
            content_it__exact=""
        ).count()
        
        context["approved_articles"] = approved_articles

        return context
