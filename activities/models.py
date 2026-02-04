from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django_mongodb_backend.managers import MongoManager
from django_mongodb_backend.fields import (
    ObjectIdAutoField,
    EmbeddedModelArrayField,
    ArrayField,
)
from django_mongodb_backend.models import EmbeddedModel


class Todo(EmbeddedModel):
    """
    Embedded Todo model for Activity tasks.
    Stored as an array of embedded documents within the Activity document.
    """

    name = models.CharField(
        max_length=200,
        help_text="Name/title of the todo item",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Detailed description of the todo item",
    )
    datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Due date/time for the todo item",
    )
    done = models.BooleanField(
        default=False,
        help_text="Whether the todo item is completed",
    )

    def __str__(self):
        status = "Done" if self.done else "Pending"
        return f"{self.name} ({status})"


class Activity(models.Model):
    """
    Activity model for managing promotional initiatives in Italy and abroad.
    Compatible with MongoDB activities collection.
    """

    # Office choices
    OFFICE_BELGRADO = "Belgrado"
    OFFICE_PODGORICA = "Podgorica"
    OFFICE_BOTH = "Both"

    OFFICE_CHOICES = [
        (OFFICE_BELGRADO, "Belgrado"),
        (OFFICE_PODGORICA, "Podgorica"),
        (OFFICE_BOTH, "Both"),
    ]

    # Tipo choices
    TIPO_PROMOZIONALI_LOCO = "Iniziative promozionali in loco"
    TIPO_PROMOZIONALI_ITALIA_ESTERO = "Iniziative promozionali in Italia e all'estero"
    TIPO_PRIVATISTICA = "Privatistica"

    TIPO_CHOICES = [
        (TIPO_PROMOZIONALI_LOCO, "Iniziative promozionali in loco"),
        (
            TIPO_PROMOZIONALI_ITALIA_ESTERO,
            "Iniziative promozionali in Italia e all'estero",
        ),
        (TIPO_PRIVATISTICA, "Privatistica"),
    ]

    # MongoDB ObjectId - use ObjectIdAutoField for auto-generation on insert
    id = ObjectIdAutoField(primary_key=True)

    # Tipo (Type of activity)
    tipo = models.CharField(
        max_length=500,
        db_column="tipo",
        choices=TIPO_CHOICES,
        help_text="Type of initiative",
        blank=True,
        null=True,
    )

    # Mese (Month)
    mese = models.CharField(
        max_length=2,
        db_column="mese",
        help_text="Month (01-12)",
        blank=True,
        null=True,
    )

    # Anno (Year)
    anno = models.IntegerField(
        db_column="anno",
        help_text="Year",
        blank=True,
        null=True,
    )

    # Nome iniziativa (Initiative name)
    nome_iniziativa = models.CharField(
        max_length=500,
        db_column="nome_iniziativa",
        help_text="Name of the initiative",
        blank=True,
        null=True,
    )

    # Città (City)
    citta = models.CharField(
        max_length=200,
        db_column="citta",
        help_text="City where the initiative takes place",
        blank=True,
        null=True,
    )

    # Data inizio (Start date)
    data_inizio = models.DateField(
        db_column="data_inizio",
        help_text="Start date of the initiative",
        blank=True,
        null=True,
    )

    # Data fine (End date)
    data_fine = models.DateField(
        db_column="data_fine",
        help_text="End date of the initiative",
        blank=True,
        null=True,
    )

    # Settore (Sector)
    settore = models.CharField(
        max_length=200,
        db_column="settore",
        help_text="Business sector",
        blank=True,
        null=True,
    )

    # Descrizione (Description)
    descrizione = models.TextField(
        db_column="descrizione",
        help_text="Description of the initiative",
        blank=True,
        null=True,
    )

    # Azione (Action)
    azione = models.TextField(
        db_column="azione",
        help_text="Action/activities performed",
        blank=True,
        null=True,
    )

    # Number of persons involved
    number_persons = models.IntegerField(
        db_column="number_persons",
        help_text="Number of persons involved in the initiative",
        blank=True,
        null=True,
    )

    # Ufficio (Office) - Limited to Belgrado, Podgorica, or Both
    ufficio = models.CharField(
        max_length=200,
        db_column="ufficio",
        choices=OFFICE_CHOICES,
        help_text="Office managing the initiative (Belgrado, Podgorica, or Both)",
        blank=True,
        null=True,
    )

    # Embedded todos array
    todos = EmbeddedModelArrayField(
        Todo,
        db_column="todos",
        blank=True,
        null=True,
        help_text="List of todo items for this activity",
    )

    # Responsabili (Users responsible for this activity)
    # Stored as array of user ID strings since MongoDB uses ObjectId for user PKs
    responsabili = ArrayField(
        models.CharField(max_length=24),  # ObjectId is 24 hex characters
        db_column="responsabili",
        blank=True,
        null=True,
        default=list,
        help_text="User IDs of people responsible for this activity",
    )

    # Slug - auto-generated from nome_iniziativa, ufficio, and anno
    slug = models.SlugField(
        max_length=300,
        db_column="slug",
        unique=True,
        blank=True,
        null=True,
        help_text="URL-friendly identifier auto-generated from nome_iniziativa, ufficio, and anno",
    )

    # Custom manager for MongoDB
    objects = MongoManager()

    class Meta:
        # MongoDB collection name
        db_table = "activities"

        # Set to False since we're managing the collection through MongoDB
        managed = False

        # Indexes for better query performance
        indexes = [
            models.Index(fields=["anno", "mese"]),
            models.Index(fields=["data_inizio"]),
            models.Index(fields=["settore"]),
            models.Index(fields=["ufficio"]),
        ]

        # Default ordering (newest first)
        ordering = ["-anno", "-mese", "-data_inizio"]

        # Verbose names for admin interface
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        """String representation of the Activity model."""
        return f"{self.nome_iniziativa} - {self.citta} ({self.mese}/{self.anno})"

    def generate_slug(self):
        """Generate a slug from nome_iniziativa, ufficio, and anno."""
        parts = []
        if self.nome_iniziativa:
            parts.append(self.nome_iniziativa)
        if self.ufficio:
            parts.append(self.ufficio)
        if self.anno:
            parts.append(str(self.anno))

        base_slug = slugify("-".join(parts))

        if not base_slug:
            base_slug = "activity"

        # Ensure uniqueness by appending a counter if needed
        slug = base_slug
        counter = 1
        # For new objects (no pk yet), just check if slug exists
        # For existing objects, exclude self from the check
        # Check for both None and empty string since MongoDB ObjectId can be ""
        if self.pk and self.pk != "":
            while Activity.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
        else:
            while Activity.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

        return slug

    def save(self, *args, **kwargs):
        """Override save to auto-generate slug if not provided."""
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)

    def get_period_display(self):
        """Return formatted date range."""
        if self.data_inizio and self.data_fine:
            return f"{self.data_inizio.strftime('%d/%m/%Y')} - {self.data_fine.strftime('%d/%m/%Y')}"
        elif self.data_inizio:
            return self.data_inizio.strftime("%d/%m/%Y")
        return "N/A"

    def get_responsabili_users(self):
        """Return queryset of User objects who are responsible for this activity."""
        User = get_user_model()
        if self.responsabili:
            # Filter out empty strings to avoid MongoDB ObjectId validation errors
            valid_ids = [rid for rid in self.responsabili if rid]
            if valid_ids:
                return User.objects.filter(pk__in=valid_ids)
        return User.objects.none()

    def is_user_responsabile(self, user):
        """Check if a user is a responsabile for this activity."""
        if not user or not user.is_authenticated:
            return False
        if not self.responsabili:
            return False
        # Convert user.pk to string for comparison since responsabili stores string IDs
        return str(user.pk) in self.responsabili

    def can_user_edit(self, user):
        """Check if a user can edit this activity (is responsabile or staff/admin)."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return self.is_user_responsabile(user)
