from django import template

register = template.Library()

# Simple translation dictionary
TRANSLATIONS = {
    'it': {
        'Home': 'Home',
        'Approved': 'Approvati',
        'Discarded': 'Scartati',
        'Sectors': 'Settori',
        'Send Email': 'Invia Email',
        'Vector Search': 'Ricerca Vettoriale',
        'About': 'Chi Siamo',
        'Navigation': 'Navigazione',
        'Company': 'Azienda',
        'About us': 'Chi Siamo',
        'Contact': 'Contatti',
        'Pending': 'In Attesa',
        'Sent': 'Inviato',
        'Approve': 'Approva',
        'Discard': 'Scarta',
        'Restore': 'Ripristina',
        'Edit': 'Modifica',
        'Edit article': 'Modifica articolo',
        'Read more': 'Leggi tutto',
        'Published': 'Pubblicato',
        'Source': 'Fonte',
        'Original Link': 'Link Originale',
    },
    'en': {
        'Home': 'Home',
        'Approved': 'Approved',
        'Discarded': 'Discarded',
        'Sectors': 'Sectors',
        'Send Email': 'Send Email',
        'Vector Search': 'Vector Search',
        'About': 'About',
        'Navigation': 'Navigation',
        'Company': 'Company',
        'About us': 'About us',
        'Contact': 'Contact',
        'Pending': 'Pending',
        'Sent': 'Sent',
        'Approve': 'Approve',
        'Discard': 'Discard',
        'Restore': 'Restore',
        'Edit': 'Edit',
        'Edit article': 'Edit article',
        'Read more': 'Read more',
        'Published': 'Published',
        'Source': 'Source',
        'Original Link': 'Original Link',
    }
}

@register.filter
def translate(text, language=None):
    """Template filter to translate text based on current language"""
    if not language:
        # Get language from context or default to Italian
        language = 'it'
    
    # Get the translation for the current language
    if language in TRANSLATIONS:
        return TRANSLATIONS[language].get(text, text)
    
    # Fallback to original text
    return text
