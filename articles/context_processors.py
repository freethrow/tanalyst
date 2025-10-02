def language_context(request):
    """Add language context to all templates."""
    
    # Get language from session, default to Italian
    current_language = request.session.get('language', 'it')
    
    # Translation dictionary for common terms
    translations = {
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
    
    def translate(text):
        """Simple translation function."""
        return translations.get(current_language, {}).get(text, text)
    
    return {
        'current_language': current_language,
        'available_languages': [
            ('it', 'Italiano'),
            ('en', 'English'),
        ],
        'translate': translate,
    }
