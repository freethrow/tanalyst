from django import forms
from django.contrib.auth import get_user_model
from .models import Activity

User = get_user_model()


class ActivityForm(forms.ModelForm):
    """Form for creating and updating activities."""

    # Custom field for selecting multiple users as responsabili
    responsabili = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'responsabili-checkbox'}),
        label='Responsabili',
        help_text='Select users who are responsible for this activity',
    )

    class Meta:
        model = Activity
        fields = [
            'tipo',
            'mese',
            'anno',
            'nome_iniziativa',
            'citta',
            'data_inizio',
            'data_fine',
            'settore',
            'descrizione',
            'azione',
            'number_persons',
            'ufficio',
        ]
        widgets = {
            'tipo': forms.Select(
                choices=[('', '---------')] + Activity.TIPO_CHOICES,
                attrs={'class': 'form-control'}
            ),
            'mese': forms.Select(
                choices=[('', '---------')] + [(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
                attrs={'class': 'form-control'}
            ),
            'anno': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2024'}),
            'nome_iniziativa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome dell\'iniziativa'}),
            'citta': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Milano'}),
            'data_inizio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fine': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'settore': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Macchine agricole'}),
            'descrizione': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrizione dell\'iniziativa'}),
            'azione': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Azioni eseguite'}),
            'number_persons': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Numero di persone'}),
            'ufficio': forms.Select(
                choices=[('', '---------')] + Activity.OFFICE_CHOICES,
                attrs={'class': 'form-control'}
            ),
        }
        labels = {
            'tipo': 'Tipo',
            'mese': 'Mese',
            'anno': 'Anno',
            'nome_iniziativa': 'Nome Iniziativa',
            'citta': 'Citta',
            'data_inizio': 'Data Inizio',
            'data_fine': 'Data Fine',
            'settore': 'Settore',
            'descrizione': 'Descrizione',
            'azione': 'Azione',
            'number_persons': 'Numero Persone',
            'ufficio': 'Ufficio',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial value for responsabili based on the instance
        if self.instance and self.instance.pk and self.instance.responsabili:
            # Filter out empty strings to avoid MongoDB ObjectId validation errors
            valid_ids = [rid for rid in self.instance.responsabili if rid]
            if valid_ids:
                self.fields['responsabili'].initial = User.objects.filter(
                    pk__in=valid_ids
                )

    def save(self, commit=True):
        """Save method - only used for updating existing activities."""
        # Convert selected users to list of string IDs for MongoDB storage
        responsabili_users = self.cleaned_data.get('responsabili', [])
        responsabili_ids = [str(user.pk) for user in responsabili_users if user and user.pk] if responsabili_users else []

        instance = super().save(commit=False)
        instance.responsabili = responsabili_ids

        if commit:
            # Only save if this is an existing instance (has a valid pk)
            if instance.pk and instance.pk != '':
                instance.save()

        return instance
