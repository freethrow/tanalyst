
import os
from django.conf import settings

from .models import Article
from .utils import perform_vector_search, generate_query_embedding
from django.views.generic import ListView, DetailView, UpdateView, FormView
from django.db import models
from django import forms
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_POST
from django.views.generic import View, TemplateView, DetailView, ListView, UpdateView, FormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator






from analyst.emails.notifications import send_latest_articles_email
from analyst.agents.translator import translate_untranslated_articles
from .forms import EmailArticlesForm
from django.conf import settings
from .tasks import scrape_ekapija, scrape_biznisrs, scrape_novaekonomija, create_all_embeddings
from analyst.agents.summarizer import get_latest_weekly_summary, get_weekly_summaries
from celery.result import AsyncResult
from django.http import JsonResponse
import json
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.utils.html import escape
from datetime import datetime
import io

# PDF imports removed - now using WeasyPrint in weasyprint_generators.py


# Helper function to check if user is staff/admin
def is_staff(user):
    return user.is_staff or user.is_superuser


# Custom mixin for staff-only views with translated error message
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that restricts access to staff users only.
    Shows a translated error message when non-staff users try to access.
    """
    def test_func(self):
        return is_staff(self.request.user)
    
    def handle_no_permission(self):
        """Show error message and redirect to home."""
        if self.request.user.is_authenticated:
            # User is logged in but not staff
            messages.error(
                self.request,
                _("This action can only be performed by an administrator")
            )
        return redirect('articles:home')


# Decorator for staff-only function views with translated error message
def staff_required(view_func):
    """
    Decorator for function-based views that requires staff access.
    Shows a translated error message when non-staff users try to access.
    """
    from functools import wraps
    
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if is_staff(request.user):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(
                request,
                _("This action can only be performed by an administrator")
            )
            return redirect('articles:home')
    
    return wrapper


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


class ArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"

    def get_queryset(self):
        """
        Get the queryset for pending articles (not yet approved/discarded).
        """
        return Article.objects.with_italian_translations()\
            .filter(status=Article.PENDING)\
            .order_by("-scraped_at")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_title'] = _('Inbox')
        return context


class ApprovedArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"

    def get_queryset(self):
        """
        Get the queryset for approved articles that haven't been sent yet.
        """
        return Article.objects.with_italian_translations()\
            .filter(status=Article.APPROVED)\
            .order_by("-time_translated")
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_title'] = _('Approved Articles')
        return context


class DiscardedArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"

    def get_queryset(self):
        """
        Get the queryset for discarded articles.
        """
        return Article.objects.with_italian_translations()\
            .filter(status=Article.DISCARDED)\
            .order_by("-time_translated")
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_title'] = _('Discarded Articles')
        return context


class SentArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"
    
    def get_queryset(self):
        """
        Get the queryset for sent articles (articles that have been included in emails).
        """
        return Article.objects.with_italian_translations()\
            .filter(status=Article.SENT)\
            .order_by("-time_translated")
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_title'] = _('Sent Articles')
        return context


class AllArticlesListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"
    
    def get_queryset(self):
        """
        Get the queryset for all articles with Italian translation regardless of status.
        """
        return Article.objects.with_italian_translations().order_by("-scraped_at")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_title'] = _('All Articles')
        return context


@require_POST
@login_required
def validate_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get("HX-Request"):
        return HttpResponse(status=400)  # Bad request if not HTMX

    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_approved()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)


@require_POST
@login_required
def discard_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get("HX-Request"):
        return HttpResponse(status=400)  # Bad request if not HTMX

    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_discarded()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)


@require_POST
@login_required
def restore_article(request, article_id):
    # Check if request is from HTMX
    if not request.headers.get("HX-Request"):
        return HttpResponse(status=400)  # Bad request if not HTMX

    try:
        article = Article.objects.get(id=article_id)
        article.mark_as_pending()
        # Return empty response - HTMX will remove the card due to hx-swap="outerHTML"
        return HttpResponse()
    except Article.DoesNotExist:
        return HttpResponse(status=404)


@staff_required
def reset_all_articles_to_pending(request):
    """Reset all articles to PENDING status for testing purposes (Admin only)."""
    Article.objects.update(status=Article.PENDING)
    return HttpResponse("All articles reset to PENDING status")


def set_language(request):
    """Language switcher using Django's i18n system via GET or POST."""
    from django.http import HttpResponseRedirect
    from django.utils import translation

    method = request.method
    # Support both GET (from menu links) and POST (if used elsewhere)
    data = request.GET if method == "GET" else request.POST

    # Debug: Show incoming data and current session
    print(f"[set_language] METHOD={method} DATA={data}")
    print(
        f"[set_language] Current session language: {request.session.get('_language')}"
    )

    language = data.get("language", "en")
    next_url = data.get("next", "/")

    # Debug output
    print(f"[set_language] Switching to: {language}")
    if language in ["en", "it"]:
        # Activate language now
        translation.activate(language)
        # Persist in session
        request.session["_language"] = language
        print(f"[set_language] Stored in session: {request.session.get('_language')}")

    # Redirect back to the page they came from
    response = HttpResponseRedirect(next_url)
    # Also persist in cookie for middleware and consistency
    response.set_cookie("django_language", language, max_age=365 * 24 * 60 * 60)
    return response


class ArticleDetailView(LoginRequiredMixin, DetailView):
    model = Article
    template_name = "article_detail.html"
    context_object_name = "article"
    login_url = "/login/"

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
                    .exclude(title_it__isnull=True)
                    .exclude(title_it__iexact="NON PERTINENT")
                    .exclude(content_it__isnull=True)
                    .exclude(content_it="")[:6]
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
                        "$match": {
                            "$and": [
                                {"title_it": {"$ne": "NON PERTINENT"}},
                                {"title_it": {"$ne": "non pertinent"}},
                                {"content_it": {"$ne": None}},
                                {"content_it": {"$ne": ""}},
                            ]
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


@staff_required
def test_tasks(request):
    """Trigger embedding generation task (Admin only)."""
    from django.contrib import messages
    from django.shortcuts import redirect
    
    # Start embedding generation task
    create_all_embeddings.delay()
    
    # Add success message in both languages
    messages.success(request, _("Embeddings generation started") + " / Iniziata la creazione di embeddings")
    
    return redirect("articles:home")


@staff_required
def generate_summary(request):
    """Trigger weekly summary generation (Admin only)."""
    try:
        # Import the task directly
        from analyst.agents.summarizer import generate_weekly_summary_task

        # Start the summary generation task
        task = generate_weekly_summary_task.delay(weeks_back=2)

        message = f"✅ Weekly summary generation started. Task ID: {task.id}"
        return HttpResponse(message)

    except Exception as e:
        error_message = f"❌ Error starting summary generation: {str(e)}"
        return HttpResponse(error_message, status=500)


@login_required
def weekly_summaries_list(request):
    """Display list of weekly summaries."""
    try:
        summaries = get_weekly_summaries(limit=20)

        # Convert MongoDB _id to id for template consistency
        for summary in summaries:
            summary["id"] = str(summary["_id"])

        context = {"summaries": summaries, "total_summaries": len(summaries)}

        return render(request, "weekly_summaries.html", context)

    except Exception as e:
        error_message = f"❌ Error retrieving summaries: {str(e)}"
        return HttpResponse(error_message, status=500)


@login_required
def weekly_summary_detail(request, summary_id):
    """Display detailed view of a specific weekly summary."""
    from pymongo import MongoClient
    from bson import ObjectId
    import os

    try:
        # Get MongoDB connection
        mongo_uri = getattr(
            settings,
            "MONGODB_URI",
            os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true"),
        )
        mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))

        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        summaries_collection = db["weekly_summaries"]

        # Get the specific summary
        summary = summaries_collection.find_one({"_id": ObjectId(summary_id)})

        client.close()

        if not summary:
            return HttpResponse("Summary not found", status=404)

        # Convert MongoDB _id to id for template consistency
        summary["id"] = str(summary["_id"])

        context = {"summary": summary}

        return render(request, "weekly_summary_detail.html", context)

    except Exception as e:
        error_message = f"❌ Error retrieving summary: {str(e)}"
        return HttpResponse(error_message, status=500)


@staff_required
def remove_all_embeddings(request):
    """Remove all embeddings from articles to prepare for regeneration (Admin only)."""
    from pymongo import MongoClient
    import os

    try:
        # Get MongoDB connection
        mongo_uri = getattr(
            settings,
            "MONGODB_URI",
            os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true"),
        )
        mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))

        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db["articles"]

        # Remove embedding-related fields from all articles
        result = collection.update_many(
            {},  # Match all documents
            {
                "$unset": {
                    "embedding": "",
                    "embedding_model": "",
                    "embedding_created_at": "",
                    "embedding_dimensions": "",
                    "embedding_error": "",
                    "embedding_failed_at": "",
                }
            },
        )

        client.close()

        message = (
            f"✅ Successfully removed embeddings from {result.modified_count} articles"
        )
        return HttpResponse(message)

    except Exception as e:
        error_message = f"❌ Error removing embeddings: {str(e)}"
        return HttpResponse(error_message, status=500)


@staff_required
def embedding_management(request):
    """View for managing embeddings - show stats and provide management options (Admin only)."""
    from pymongo import MongoClient
    import os

    try:
        # Get MongoDB connection
        mongo_uri = getattr(
            settings,
            "MONGODB_URI",
            os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true"),
        )
        mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))

        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db["articles"]

        # Get embedding statistics
        total_articles = collection.count_documents({})

        # Articles with embeddings
        with_embeddings = collection.count_documents({"embedding": {"$exists": True}})

        # Articles without embeddings
        without_embeddings = total_articles - with_embeddings

        # Get embedding models used
        models_pipeline = [
            {"$match": {"embedding_model": {"$exists": True}}},
            {"$group": {"_id": "$embedding_model", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        # Convert _id to id for template compatibility
        models_stats = [{"id": doc["_id"], "count": doc["count"]} for doc in collection.aggregate(models_pipeline)]

        # Articles with errors
        with_errors = collection.count_documents({"embedding_error": {"$exists": True}})

        client.close()

        context = {
            "total_articles": total_articles,
            "with_embeddings": with_embeddings,
            "without_embeddings": without_embeddings,
            "models_stats": models_stats,
            "with_errors": with_errors,
            "embedding_percentage": round((with_embeddings / total_articles * 100), 1)
            if total_articles > 0
            else 0,
        }

        return render(request, "embedding_management.html", context)

    except Exception as e:
        error_message = f"❌ Error getting embedding statistics: {str(e)}"
        return HttpResponse(error_message, status=500)


@login_required
def vector_search(request):
    if request.method == "POST":
        query = request.POST.get("query", "").strip()
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
        
        try:
            # Perform vector search using utility function
            processed_results = perform_vector_search(
                query=query,
                article_model=Article,
                index_name="article_vector_index",
                num_candidates=100,
                limit=50,
            )
            
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
            
        except Exception as e:
            print(f"Error performing vector search: {e}")
            if is_htmx:
                return render(
                    request, "partials/vector_search_results.html", {"results": []}
                )
            return render(
                request,
                "vector_search.html",
                {"results": [], "query": query, "error": str(e)},
            )

    return render(request, "vector_search.html")


class ArticleEditView(LoginRequiredMixin, UpdateView):
    """
    Class-based view for editing articles.
    Allows editing of all article fields including titles, content, metadata, and status flags.
    """

    login_url = "/login/"
    """
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
            "content_it": forms.Textarea(
                attrs={"rows": 40, "cols": 60, "class": "min-h-[400px] font-light p-2"}
            ),
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


class SectorListView(LoginRequiredMixin, ListView):
    """
    View to display all available sectors.
    """

    login_url = "/login/"

    template_name = "sectors.html"
    context_object_name = "sectors"

    def get_queryset(self):
        """Return the list of sectors with article counts, sorted by count descending."""
        sectors_with_counts = []
        for sector in SECTORS:
            count = Article.objects.with_italian_translations().filter(sector=sector).count()
            sectors_with_counts.append({"name": sector, "count": count})
        # Sort by count in descending order
        return sorted(sectors_with_counts, key=lambda x: x["count"], reverse=True)


class SectorDetailView(LoginRequiredMixin, ListView):
    """
    View to display articles for a specific sector.
    """

    login_url = "/login/"

    model = Article
    template_name = "sector_detail.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        """Get articles for the specified sector."""
        sector = self.kwargs["sector"]
        return (
            Article.objects.with_italian_translations()
            .filter(sector=sector)
            .order_by("-time_translated")
        )

    def get_context_data(self, **kwargs):
        """Add sector name to context."""
        context = super().get_context_data(**kwargs)
        context["sector"] = self.kwargs["sector"]
        context["sector_exists"] = self.kwargs["sector"] in SECTORS
        return context


class SendArticlesEmailView(StaffRequiredMixin, FormView):
    """
    View for sending latest articles via email.
    Admin only - restricted to staff users.
    """

    login_url = "/login/"

    template_name = "send_email.html"
    form_class = EmailArticlesForm
    success_url = reverse_lazy("articles:home")

    def form_valid(self, form):
        """Process the form and start the email task."""
        email = form.cleaned_data.get("email")
        send_to_all_users = form.cleaned_data.get("send_to_all_users", False)
        num_articles = form.cleaned_data["num_articles"]
        subject = form.cleaned_data.get("subject") or None

        # Check if there are any approved articles ready to be sent
        approved_articles = Article.objects.with_italian_translations().filter(status=Article.APPROVED).count()

        # If no approved articles, redirect back to home with a message
        if approved_articles == 0:
            messages.warning(
                self.request,
                "Non ci sono articoli approvati da inviare. Per favore seleziona alcune notizie per approvazione."
            )
            return redirect('articles:home')
            
        # Check if we're sending to all users
        if send_to_all_users:
            # Count users with email addresses
            from django.contrib.auth.models import User
            user_count = User.objects.exclude(email__isnull=True).exclude(email="").count()
            if user_count == 0:
                messages.warning(
                    self.request,
                    "Non ci sono utenti con indirizzi email nel sistema."
                )
                return redirect('articles:send_email')

        # Start the email task asynchronously
        try:
            send_latest_articles_email.delay(
                recipient_email=email if not send_to_all_users else None,
                subject=subject,
                num_articles=num_articles,
                send_to_all_users=send_to_all_users
            )

            # Success message
            if send_to_all_users:
                messages.success(
                    self.request,
                    f"Email will be sent to all users with email addresses, containing {num_articles} articles",
                )
            else:
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
        approved_articles = (
            Article.objects.filter(
                status=Article.APPROVED,
                title_it__isnull=False,
                content_it__isnull=False,
            )
            .exclude(title_it__exact="", content_it__exact="")
            .count()
        )

        context["approved_articles"] = approved_articles

        return context


# Authentication Views
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect("articles:home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            next_url = request.GET.get("next", "articles:home")
            return redirect(next_url)
        else:
            return render(
                request, "login.html", {"error": "Invalid username or password"}
            )

    return render(request, "login.html")


@login_required
def logout_view(request):
    """User logout view"""
    auth_logout(request)
    return redirect("login")


@staff_required
def scrapers_view(request):
    """Manual scrapers page"""
    return render(request, "scrapers.html")


@staff_required
def translation_service_view(request):
    """Translation service page"""
    return render(request, "translation_service.html")


@staff_required
@require_POST
def trigger_translation(request):
    """Trigger translation task for untranslated articles"""
    try:
        # Trigger the Celery task
        translate_untranslated_articles.delay()
        messages.success(
            request,
            _(
                "Translation service started successfully. Articles will be translated shortly."
            ),
        )
    except Exception as e:
        messages.error(
            request, _("Error starting translation: %(error)s") % {"error": str(e)}
        )

    return redirect("articles:home")


@staff_required
@require_POST
def trigger_scraper(request, scraper_name):
    """Trigger a specific scraper task"""
    print(f"DEBUG: trigger_scraper called with scraper_name: '{scraper_name}'")
    print(f"DEBUG: scraper_name type: {type(scraper_name)}")
    scraper_tasks = {
        "ekapija": (
            scrape_ekapija,
            _(
                "Ekapija scraper started successfully. New articles will appear shortly."
            ),
        ),
        "biznisrs": (
            scrape_biznisrs,
            _(
                "BiznisRS scraper started successfully. New articles will appear shortly."
            ),
        ),
        "novaekonomija": (
            scrape_novaekonomija,
            _(
                "Nova Ekonomija scraper started successfully. New articles will appear shortly."
            ),
        ),
    }

    if scraper_name not in scraper_tasks:
        messages.error(request, _("Invalid scraper name"))
        return redirect("articles:home")

    task_func, success_message = scraper_tasks[scraper_name]

    try:
        # Trigger the Celery task
        task_func.delay()
        messages.success(request, success_message)
    except Exception as e:
        messages.error(
            request, _("Error starting scraper: %(error)s") % {"error": str(e)}
        )

    return redirect("articles:home")


@staff_required
def generate_pdf_report(request):
    """Generate PDF report of approved articles using WeasyPrint"""
    # Get approved articles with Italian translations
    articles = (
        Article.objects.with_italian_translations()
        .filter(status=Article.APPROVED)
        .order_by("-article_date")

    )

    if not articles.exists():
        messages.error(
            request,
            "❌ Nessun articolo approvato disponibile per generare il report PDF. "
            "Approva alcuni articoli prima di generare il report.",
        )
        return redirect("articles:approved")
    
    # Use the WeasyPrint PDF generator
    from .weasyprint_generators import ArticlesPDFGenerator
    generator = ArticlesPDFGenerator()
    return generator.generate_articles_pdf(articles)


@login_required
def generate_weekly_summary_pdf(request, summary_id):
    """Generate PDF report for a specific weekly summary using WeasyPrint"""
    from .models import WeeklySummary
    from django.shortcuts import get_object_or_404

    try:
        # Get the specific summary using Django ORM
        summary = get_object_or_404(WeeklySummary, pk=summary_id)
        
        # Use the WeasyPrint PDF generator
        from .weasyprint_generators import WeeklySummaryPDFGenerator
        generator = WeeklySummaryPDFGenerator()
        return generator.generate_weekly_summary_pdf(summary)
        
    except Exception as e:
        error_message = f"❌ Error generating PDF: {str(e)}"
        return HttpResponse(error_message, status=500)
