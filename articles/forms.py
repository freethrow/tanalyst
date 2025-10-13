from django import forms
from django.core.validators import EmailValidator


class EmailArticlesForm(forms.Form):
    """Form for sending latest articles via email."""

    email = forms.EmailField(
        label="Indirizzo Email",
        max_length=254,
        validators=[EmailValidator()],
        widget=forms.EmailInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "esempio@email.com",
                "required": True,
            }
        ),
        help_text="Inserisci l'indirizzo email dove inviare gli articoli",
        initial="aleksendric@gmail.com",
    )

    num_articles = forms.IntegerField(
        label="Numero di Articoli",
        min_value=1,
        max_value=50,
        initial=12,
        widget=forms.NumberInput(
            attrs={
                "class": "input input-bordered w-full",
                "min": "1",
                "max": "50",
                "required": True,
            }
        ),
        help_text="Numero di articoli più recenti da includere (1-50)",
    )

    subject = forms.CharField(
        label="Oggetto Email (Opzionale)",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "Ultimi articoli di business",
            }
        ),
        help_text="Oggetto personalizzato per l'email (opzionale)",
    )
