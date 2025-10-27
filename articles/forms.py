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
                "required": False,
            }
        ),
        help_text="Inserisci l'indirizzo email dove inviare gli articoli (ignorato se invii a tutti gli utenti)",
        initial="aleksendric@gmail.com",
        required=False,
    )

    send_to_all_users = forms.BooleanField(
        label="Invia a tutti gli utenti con email",
        required=False,
        initial=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "checkbox checkbox-primary",
            }
        ),
        help_text="Seleziona questa opzione per inviare l'email a tutti gli utenti registrati con indirizzo email",
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
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        send_to_all_users = cleaned_data.get("send_to_all_users")
        
        # Validate that either an email is provided or send_to_all_users is selected
        if not send_to_all_users and not email:
            self.add_error("email", "Devi inserire un indirizzo email o selezionare 'Invia a tutti gli utenti'")
        
        return cleaned_data
