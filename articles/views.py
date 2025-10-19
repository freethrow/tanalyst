
import os
from django.conf import settings

from .models import Article
from .utils import perform_vector_search, generate_query_embedding
from django.views.generic import ListView, DetailView, UpdateView, FormView
from django.db import models
from django import forms
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_POST






from analyst.emails.notifications import send_latest_articles_email
from analyst.agents.translator import translate_untranslated_articles
from .forms import EmailArticlesForm
from django.conf import settings
from .tasks import scrape_ekapija, scrape_biznisrs, create_all_embeddings
from analyst.agents.summarizer import get_latest_weekly_summary, get_weekly_summaries
from django.utils.translation import gettext as _
from django.utils.html import escape
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    BaseDocTemplate,
    PageTemplate,
    Frame,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont





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
        queryset = Article.objects.filter(
            title_it__isnull=False,
            content_it__isnull=False,
            status=Article.PENDING,
        ).exclude(
            title_it__exact="",
            content_it__exact="",
        )
        return queryset.order_by("-scraped_at")


class ApprovedArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"

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


class DiscardedArticleListView(LoginRequiredMixin, ListView):
    model = Article
    template_name = "index.html"
    context_object_name = "articles"
    login_url = "/login/"

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
                num_candidates=50,
                limit=18,
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
            count = (
                Article.objects.filter(sector=sector, content_it__isnull=False)
                .exclude(content_it__exact="")
                .count()
            )
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
    """Generate PDF report of approved articles using ReportLab"""
    # Get approved articles with Italian translations
    articles = (
        Article.objects.filter(
            status=Article.APPROVED, title_it__isnull=False, content_it__isnull=False
        )
        .exclude(title_it__exact="", content_it__exact="")
        .order_by("-scraped_at")[:50]
    )

    # Check if there are any approved articles
    if not articles.exists():
        messages.error(
            request,
            "❌ Nessun articolo approvato disponibile per generare il report PDF. "
            "Approva alcuni articoli prima di generare il report.",
        )
        return redirect("articles:approved")

    # Create PDF buffer with two-column layout
    buffer = io.BytesIO()

    # Define page dimensions
    page_width, page_height = A4
    left_margin = 2 * cm
    right_margin = 2 * cm
    top_margin = 2 * cm
    bottom_margin = 2 * cm

    # Calculate column dimensions
    column_width = (
        page_width - left_margin - right_margin - 0.5 * cm
    ) / 2  # 0.5cm gap between columns
    column_height = page_height - top_margin - bottom_margin

    # Create document with custom page template
    doc = BaseDocTemplate(buffer, pagesize=A4)

    # Container for PDF elements
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Register fonts for full Unicode support
    try:
        import os

        roboto_light_path = os.path.join(
            settings.BASE_DIR, "static", "fonts", "Roboto-Light.ttf"
        )
        manrope_bold_path = os.path.join(
            settings.BASE_DIR, "static", "fonts", "Manrope-Bold.ttf"
        )

        pdfmetrics.registerFont(TTFont("Roboto-Light", roboto_light_path))
        pdfmetrics.registerFont(TTFont("Manrope-Bold", manrope_bold_path))

        font_name = "Roboto-Light"
        title_font_name = "Manrope-Bold"
    except Exception as e:
        # Fallback to standard fonts if custom fonts not found
        print(f"Could not load custom fonts: {e}")
        font_name = "Times-Roman"
        title_font_name = "Times-Bold"

    # Custom styles with consistent color theme (#991b1b)
    brand_color = colors.HexColor("#991b1b")

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontName=title_font_name,
        fontSize=24,
        textColor=brand_color,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    article_title_style = ParagraphStyle(
        "ArticleTitle",
        parent=styles["Heading2"],
        fontName=title_font_name,
        fontSize=14,
        textColor=brand_color,
        spaceAfter=6,
    )

    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=10,
    )

    content_style = ParagraphStyle(
        "Content",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=20,
    )

    source_link_style = ParagraphStyle(
        "SourceLink",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=10,
    )

    # Add articles (no header here - it's drawn on canvas)
    for idx, article in enumerate(articles, 1):
        # Create article elements list
        article_elements = []

        # Article title - use raw Unicode text
        title_text = f"{idx}. {article.title_it or article.title_en or ''}"
        try:
            article_elements.append(Paragraph(title_text, article_title_style))
        except:
            # If Unicode fails, try with escaped version
            article_elements.append(Paragraph(escape(title_text), article_title_style))

        # Article metadata
        source_text = article.source or "N/A"
        sector_text = article.sector or "Generale"
        meta_text = f"""
        <b><font color='#991b1b'>Data:</font></b> {article.article_date.strftime("%d/%m/%Y") if article.article_date else "N/A"} | 
        <b><font color='#991b1b'>Fonte:</font></b> {source_text} | 
        <b><font color='#991b1b'>Settore:</font></b> {sector_text}
        """
        try:
            article_elements.append(Paragraph(meta_text, meta_style))
        except:
            article_elements.append(Paragraph(escape(meta_text), meta_style))

        # Article content - use raw Unicode
        content = article.content_it or article.content_en or ""
        # Clean HTML tags if any
        content = content.replace("<p>", "").replace("</p>", " ").replace("<br/>", " ")
        # content = content[:2000]  # Limit content length
        try:
            article_elements.append(Paragraph(content, content_style))
        except:
            article_elements.append(Paragraph(escape(content), content_style))

        # Add source link
        if article.url:
            source_link = (
                f'<i>Fonte: <a href="{article.url}" color="grey">{article.url}</a></i>'
            )
            try:
                article_elements.append(Paragraph(source_link, source_link_style))
            except:
                article_elements.append(
                    Paragraph(f"<i>Fonte: {article.url}</i>", source_link_style)
                )

        article_elements.append(Spacer(1, 0.5 * cm))

        # Keep article together to prevent ugly breaks
        elements.append(KeepTogether(article_elements))

    # Add final contact footer at the end
    elements.append(Spacer(1, 2 * cm))

    contact_footer_style = ParagraphStyle(
        "ContactFooter",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=5,
    )

    contact_info = """
    <b>TA - Trade AI Analyst</b><br/>
    Email: info@technicalanalyst.com | Tel: +39 123 456 7890<br/>
    Web: www.technicalanalyst.com | Via Example 123, Milano, Italia<br/>
    <i>© 2025 Technical Analyst. Tutti i diritti riservati.</i>
    """

    elements.append(Paragraph(contact_info, contact_footer_style))

    # Define header and footer function
    def add_header_footer(canvas, doc):
        canvas.saveState()
        # Draw header background
        canvas.setFillColor(colors.HexColor("#991b1b"))
        canvas.rect(
            0, page_height - 3 * cm, page_width, 3 * cm, fill=True, stroke=False
        )
        # Header text in white
        canvas.setFont("Helvetica-Bold", 20)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(
            page_width / 2, page_height - 1.5 * cm, "Business News Report"
        )
        # Metadata in white
        canvas.setFont("Helvetica", 9)
        metadata_text = f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Articoli: {articles.count()}"
        canvas.drawCentredString(page_width / 2, page_height - 2.2 * cm, metadata_text)

        # Draw footer background
        canvas.setFillColor(colors.HexColor("#991b1b"))
        canvas.rect(0, 0, page_width, 1 * cm, fill=True, stroke=False)
        # Footer text in white
        footer_text = f"TA - Technical Analyst | Report generato il {datetime.now().strftime('%d/%m/%Y')}"
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.white)
        canvas.drawCentredString(page_width / 2, 0.4 * cm, footer_text)
        # Page number in white
        page_num = f"Pagina {canvas.getPageNumber()}"
        canvas.drawRightString(page_width - right_margin, 0.4 * cm, page_num)
        canvas.restoreState()

    # Create single-column frame with space for header
    frame = Frame(
        left_margin,
        bottom_margin,
        page_width - left_margin - right_margin,
        page_height - top_margin - bottom_margin - 3 * cm,  # Subtract header height
        id="normal",
    )

    # Create page template with single column
    page_template = PageTemplate(
        id="OneColumn", frames=[frame], onPage=add_header_footer
    )
    doc.addPageTemplates([page_template])

    # Build PDF
    doc.build(elements)

    # Get PDF value and create response
    pdf_value = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_value, content_type="application/pdf")
    filename = f"report_articoli_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


@login_required
def generate_weekly_summary_pdf(request, summary_id):
    """Generate PDF report for a specific weekly summary using ReportLab"""
    from .models import WeeklySummary
    from django.shortcuts import get_object_or_404

    try:
        # Get the specific summary using Django ORM
        summary = get_object_or_404(WeeklySummary, pk=summary_id)

        # Create PDF buffer
        buffer = io.BytesIO()

        # Define page dimensions
        page_width, page_height = A4
        left_margin = 2.5 * cm
        right_margin = 2.5 * cm
        top_margin = 2 * cm
        bottom_margin = 2 * cm

        # Create document
        doc = BaseDocTemplate(buffer, pagesize=A4)

        # Container for PDF elements
        elements = []

        # Define styles
        styles = getSampleStyleSheet()

        # Register fonts for full Unicode support
        try:
            roboto_light_path = os.path.join(
                settings.BASE_DIR, "static", "fonts", "Roboto-Light.ttf"
            )
            manrope_bold_path = os.path.join(
                settings.BASE_DIR, "static", "fonts", "Manrope-Bold.ttf"
            )

            pdfmetrics.registerFont(TTFont("Roboto-Light", roboto_light_path))
            pdfmetrics.registerFont(TTFont("Manrope-Bold", manrope_bold_path))

            font_name = "Roboto-Light"
            title_font_name = "Manrope-Bold"
        except Exception as e:
            # Fallback to standard fonts if custom fonts not found
            print(f"Could not load custom fonts: {e}")
            font_name = "Times-Roman"
            title_font_name = "Times-Bold"

        # Custom styles with consistent color theme (#991b1b)
        brand_color = colors.HexColor("#991b1b")

        main_title_style = ParagraphStyle(
            "MainTitle",
            parent=styles["Heading1"],
            fontName=title_font_name,
            fontSize=22,
            textColor=brand_color,
            alignment=TA_CENTER,
            spaceAfter=8,
        )

        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=20,
        )

        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontName=title_font_name,
            fontSize=16,
            textColor=brand_color,
            spaceAfter=10,
            spaceBefore=15,
        )

        subsection_title_style = ParagraphStyle(
            "SubsectionTitle",
            parent=styles["Heading3"],
            fontName=title_font_name,
            fontSize=13,
            textColor=brand_color,
            spaceAfter=8,
            spaceBefore=12,
        )

        content_style = ParagraphStyle(
            "Content",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=14,
        )

        bullet_style = ParagraphStyle(
            "Bullet",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leftIndent=20,
            spaceAfter=8,
            leading=13,
        )

        highlight_box_style = ParagraphStyle(
            "HighlightBox",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=15,
            leading=15,
            leftIndent=15,
            rightIndent=15,
        )

        # Add title
        title_text = summary.title or "Weekly Business Summary"
        elements.append(Paragraph(title_text, main_title_style))

        # Add metadata
        period_start = summary.period_start
        period_end = summary.period_end
        generated_at = summary.generated_at

        if period_start and period_end:
            period_text = f"Periodo: {period_start.strftime('%d %b')} - {period_end.strftime('%d %b %Y')}"
        else:
            period_text = "Periodo: N/A"

        metadata_text = f"{period_text} | Articoli analizzati: {summary.articles_analyzed or 0} | Generato: {generated_at.strftime('%d/%m/%Y') if generated_at else 'N/A'}"
        elements.append(Paragraph(metadata_text, subtitle_style))
        elements.append(Spacer(1, 0.3 * cm))

        # Executive Summary in a highlighted box
        elements.append(Paragraph("Sintesi Esecutiva", section_title_style))

        # Create a table for the highlighted box effect
        exec_summary_text = summary.executive_summary or ""
        exec_data = [[Paragraph(exec_summary_text, highlight_box_style)]]
        exec_table = Table(
            exec_data, colWidths=[page_width - left_margin - right_margin - 1 * cm]
        )
        exec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("BOX", (0, 0), (-1, -1), 1, brand_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 15),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                ]
            )
        )
        elements.append(exec_table)
        elements.append(Spacer(1, 0.5 * cm))

        # Main Trends
        main_trends = summary.main_trends or []
        if main_trends:
            elements.append(Paragraph("Tendenze Principali", section_title_style))
            for idx, trend in enumerate(main_trends, 1):
                bullet_text = f"<b>{idx}.</b> {trend}"
                elements.append(Paragraph(bullet_text, bullet_style))
            elements.append(Spacer(1, 0.3 * cm))

        # Featured Sectors
        featured_sectors = summary.featured_sectors or []
        if featured_sectors:
            elements.append(Paragraph("Settori in Evidenza", subsection_title_style))
            sectors_text = " • ".join(featured_sectors)
            elements.append(Paragraph(sectors_text, content_style))
            elements.append(Spacer(1, 0.3 * cm))

        # Opportunities for Italy
        opportunities = summary.opportunities_italy or ""
        if opportunities:
            elements.append(
                Paragraph("Opportunità per le Aziende Italiane", section_title_style)
            )

            # Create highlighted box for opportunities
            opp_data = [[Paragraph(opportunities, highlight_box_style)]]
            opp_table = Table(
                opp_data, colWidths=[page_width - left_margin - right_margin - 1 * cm]
            )
            opp_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#16A34A")),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("LEFTPADDING", (0, 0), (-1, -1), 15),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 15),
                    ]
                )
            )
            elements.append(opp_table)
            elements.append(Spacer(1, 0.5 * cm))

        # Full Content/Analysis
        full_content = summary.full_content or ""
        if full_content:
            elements.append(Paragraph("Analisi Completa", section_title_style))
            # Split content into paragraphs for better formatting
            paragraphs = full_content.split("\n")
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), content_style))

        # Add footer info
        elements.append(Spacer(1, 1 * cm))
        llm_model = summary.llm_model or "AI Assistant"
        footer_info = f"<i>Generato da {llm_model}</i>"
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(footer_info, footer_style))

        # Define header and footer function
        def add_header_footer(canvas, doc):
            canvas.saveState()
            # Draw header background
            canvas.setFillColor(brand_color)
            canvas.rect(
                0, page_height - 2.5 * cm, page_width, 2.5 * cm, fill=True, stroke=False
            )
            # Header text in white
            canvas.setFont("Helvetica-Bold", 18)
            canvas.setFillColor(colors.white)
            canvas.drawCentredString(
                page_width / 2, page_height - 1.3 * cm, "Weekly Business Summary"
            )

            # Draw footer background
            canvas.setFillColor(brand_color)
            canvas.rect(0, 0, page_width, 1 * cm, fill=True, stroke=False)
            # Footer text in white
            footer_text = f"TA - Technical Analyst | Generato il {datetime.now().strftime('%d/%m/%Y')}"
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.white)
            canvas.drawCentredString(page_width / 2, 0.4 * cm, footer_text)
            # Page number in white
            page_num = f"Pagina {canvas.getPageNumber()}"
            canvas.drawRightString(page_width - right_margin, 0.4 * cm, page_num)
            canvas.restoreState()

        # Create frame with space for header
        frame = Frame(
            left_margin,
            bottom_margin,
            page_width - left_margin - right_margin,
            page_height
            - top_margin
            - bottom_margin
            - 2.5 * cm,  # Subtract header height
            id="normal",
        )

        # Create page template
        page_template = PageTemplate(
            id="OneColumn", frames=[frame], onPage=add_header_footer
        )
        doc.addPageTemplates([page_template])

        # Build PDF
        doc.build(elements)

        # Get PDF value and create response
        pdf_value = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_value, content_type="application/pdf")
        filename = (
            f"weekly_summary_{summary_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        error_message = f"❌ Error generating PDF: {str(e)}"
        return HttpResponse(error_message, status=500)
