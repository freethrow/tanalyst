from django.contrib import admin
from .models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """
    Admin interface for Activity model with comprehensive filtering and display options.
    """

    # List display configuration
    list_display = (
        'nome_iniziativa',
        'citta',
        'settore',
        'ufficio',
        'mese',
        'anno',
        'data_inizio',
        'data_fine',
    )

    # Filters in the right sidebar
    list_filter = (
        'anno',
        'mese',
        'settore',
        'ufficio',
        'data_inizio',
    )

    # Search fields
    search_fields = (
        'nome_iniziativa',
        'citta',
        'settore',
        'ufficio',
        'descrizione',
        'azione',
        'responsabile_iniziativa',
    )

    # Default ordering (newest first)
    ordering = ('-anno', '-mese', '-data_inizio')

    # Number of items per page
    list_per_page = 25

    # Read-only fields (ObjectId should not be edited)
    readonly_fields = ('id',)

    # Fieldsets for the detail/edit page
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'nome_iniziativa', 'tipo'),
            'description': 'Core information about the initiative'
        }),
        ('Location & Time', {
            'fields': ('citta', 'mese', 'anno', 'data_inizio', 'data_fine'),
            'description': 'When and where the initiative takes place'
        }),
        ('Classification', {
            'fields': ('settore', 'ufficio'),
            'description': 'Business sector and managing office'
        }),
        ('Details', {
            'fields': ('descrizione', 'azione', 'responsabile_iniziativa'),
            'description': 'Detailed description and responsibilities',
            'classes': ('wide',)
        }),
    )

    # Enable date hierarchy navigation
    date_hierarchy = 'data_inizio'

    # Custom admin actions
    actions = ['export_selected_activities']

    def export_selected_activities(self, request, queryset):
        """Custom admin action to export selected activities (placeholder)."""
        count = queryset.count()
        self.message_user(request, f'{count} activities selected for export.')

    export_selected_activities.short_description = "Export selected activities"
