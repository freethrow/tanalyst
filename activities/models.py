from django.db import models
from django_mongodb_backend.managers import MongoManager
from django_mongodb_backend.fields import ObjectIdField


class Activity(models.Model):
    """
    Activity model for managing promotional initiatives in Italy and abroad.
    Compatible with MongoDB activities collection.
    """

    # MongoDB ObjectId
    id = ObjectIdField(primary_key=True, db_column="_id")

    # Tipo (Type of activity)
    tipo = models.CharField(
        max_length=500,
        db_column="tipo",
        help_text="Type of initiative (e.g., Promotional initiatives in Italy and abroad)",
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

    # Responsabile iniziativa (Initiative manager)
    responsabile_iniziativa = models.CharField(
        max_length=200,
        db_column="responsabile_iniziativa",
        help_text="Person responsible for the initiative",
        blank=True,
        null=True,
    )

    # Ufficio (Office)
    ufficio = models.CharField(
        max_length=200,
        db_column="ufficio",
        help_text="Office managing the initiative",
        blank=True,
        null=True,
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

    def get_period_display(self):
        """Return formatted date range."""
        if self.data_inizio and self.data_fine:
            return f"{self.data_inizio.strftime('%d/%m/%Y')} - {self.data_fine.strftime('%d/%m/%Y')}"
        elif self.data_inizio:
            return self.data_inizio.strftime('%d/%m/%Y')
        return "N/A"
