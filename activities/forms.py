from django import forms
from .models import Activity


class ActivityForm(forms.ModelForm):
    """Form for creating and updating activities."""

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
            'responsabile_iniziativa',
            'ufficio',
        ]
        widgets = {
            'tipo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Iniziative promozionali in Italia e all\'estero'}),
            'mese': forms.Select(
                choices=[(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)],
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
            'responsabile_iniziativa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome responsabile'}),
            'ufficio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Belgrado'}),
        }
        labels = {
            'tipo': 'Tipo',
            'mese': 'Mese',
            'anno': 'Anno',
            'nome_iniziativa': 'Nome Iniziativa',
            'citta': 'Città',
            'data_inizio': 'Data Inizio',
            'data_fine': 'Data Fine',
            'settore': 'Settore',
            'descrizione': 'Descrizione',
            'azione': 'Azione',
            'responsabile_iniziativa': 'Responsabile Iniziativa',
            'ufficio': 'Ufficio',
        }
