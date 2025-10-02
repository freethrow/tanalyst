#!/usr/bin/env python
"""
Script to fill empty Italian translations in django.po file.
"""

# Translation dictionary: English -> Italian
translations = {
    # Article Detail
    "Translated": "Tradotto",
    "Related Articles": "Articoli Correlati",
    "Back": "Indietro",
    "View Original": "Visualizza Originale",
    
    # Article Edit
    "Update article content and translation": "Aggiorna contenuto e traduzione dell'articolo",
    "View Article": "Visualizza Articolo",
    "Back to List": "Torna alla Lista",
    "Translation Editor": "Editor di Traduzione",
    "%(source_language)s Title": "Titolo %(source_language)s",
    "Italian Title": "Titolo Italiano",
    "%(source_language)s Content": "Contenuto %(source_language)s",
    "Italian Content": "Contenuto Italiano",
    "Save Changes": "Salva Modifiche",
    
    # Embedding Management
    "Embedding Management": "Gestione Embeddings",
    "Manage vector embeddings for semantic search": "Gestisci gli embeddings vettoriali per la ricerca semantica",
    "Total Articles": "Articoli Totali",
    "With Embeddings": "Con Embeddings",
    "%(embedding_percentage)s%% complete": "%(embedding_percentage)s%% completato",
    "Missing": "Mancanti",
    "With Errors": "Con Errori",
    "Embedding Models Used": "Modelli di Embedding Utilizzati",
    "Model": "Modello",
    "Articles Count": "Conteggio Articoli",
    "Percentage": "Percentuale",
    "Management Actions": "Azioni di Gestione",
    "Use these actions to manage your embeddings. Be careful as some actions cannot be undone.": "Usa queste azioni per gestire i tuoi embeddings. Attenzione, alcune azioni non possono essere annullate.",
    "This will remove all embedding data from articles. Use this before switching embedding models.": "Questo rimuoverà tutti i dati di embedding dagli articoli. Usa questo prima di cambiare modelli di embedding.",
    "Generate New Embeddings": "Genera Nuovi Embeddings",
    "Start generating embeddings for articles that don't have them using Nomic API.": "Inizia a generare embeddings per gli articoli che non li hanno usando l'API Nomic.",
    "Start Embedding Generation": "Avvia Generazione Embeddings",
    "Migration to Nomic Embeddings": "Migrazione agli Embeddings Nomic",
    "Your system is now configured to use Nomic embeddings (nomic-embed-text-v1.5) instead of VoyageAI. Remove old embeddings first, then generate new ones for better performance.": "Il tuo sistema è ora configurato per usare gli embeddings Nomic (nomic-embed-text-v1.5) invece di VoyageAI. Rimuovi prima i vecchi embeddings, poi genera quelli nuovi per prestazioni migliori.",
    "Confirm Removal": "Conferma Rimozione",
    "Yes, Remove All": "Sì, Rimuovi Tutto",
    
    # Index
    "Articles": "Articoli",
    "No articles found": "Nessun articolo trovato",
    "Start by adding some articles to get started.": "Inizia aggiungendo alcuni articoli per cominciare.",
    
    # Login
    "Login": "Accedi",
    "Welcome Back": "Bentornato",
    "Sign in to access your account": "Accedi per accedere al tuo account",
    "Invalid username or password": "Nome utente o password non validi",
    "Username": "Nome utente",
    "Enter your username": "Inserisci il tuo nome utente",
    "Password": "Password",
    "Enter your password": "Inserisci la tua password",
    "Remember me": "Ricordami",
    "Sign In": "Accedi",
    "Contact your administrator to create an account": "Contatta il tuo amministratore per creare un account",
    
    # Send Email
    "Send the latest translated articles to an email address": "Invia gli ultimi articoli tradotti a un indirizzo email",
    "Back to Home": "Torna alla Home",
    "Email Configuration": "Configurazione Email",
    "Sending Information": "Informazioni sull'Invio",
    "Only articles with APPROVED status will be sent": "Verranno inviati solo articoli con stato APPROVATO",
    "Articles will be sorted by translation date (most recent first)": "Gli articoli saranno ordinati per data di traduzione (più recenti per primi)",
    "After sending, the status of articles will become SENT": "Dopo l'invio, lo stato degli articoli diventerà INVIATO",
    "The email will be sent in the background and may take a few minutes": "L'email verrà inviata in background e potrebbe richiedere alcuni minuti",
    "Approved Articles": "Articoli Approvati",
    "Ready to send": "Pronti per l'invio",
    
    # Vector Search
    "Search articles using semantic similarity": "Cerca articoli usando la similarità semantica",
    "Enter your search query...": "Inserisci la tua ricerca...",
    "Search": "Cerca",
    "Searching...": "Ricerca in corso...",
    "No results found": "Nessun risultato trovato",
    "Try different search terms or check your spelling": "Prova termini di ricerca diversi o controlla l'ortografia",
    "Start searching": "Inizia a cercare",
    "Enter a query above to find relevant articles": "Inserisci una query sopra per trovare articoli rilevanti",
}

def fill_translations():
    """Read the PO file and fill in missing translations."""
    import re
    
    po_file = r"c:\Users\DELL\Desktop\TA\locale\it\LC_MESSAGES\django.po"
    
    with open(po_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # For each translation in our dictionary
    for english, italian in translations.items():
        # Escape special regex characters
        english_escaped = re.escape(english)
        
        # Pattern to find msgid with empty msgstr
        pattern = rf'(msgid "{english_escaped}"\nmsgstr ")("")'
        
        # Replace with Italian translation
        replacement = rf'\1{italian}\2'
        content = re.sub(pattern, replacement, content)
    
    # Remove fuzzy markers
    content = re.sub(r'#, fuzzy\n#\| msgid "[^"]*"\n', '', content)
    content = re.sub(r'#, fuzzy\n', '', content)
    
    # Write back
    with open(po_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Filled translations in {po_file}")
    print("Now run: python manage.py compilemessages --ignore=venv")

if __name__ == "__main__":
    fill_translations()
