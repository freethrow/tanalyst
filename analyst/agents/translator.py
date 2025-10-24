# articles/translator.py
import asyncio
from datetime import datetime
import os
from time import sleep
from typing import Dict, Any
import logging

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai import Agent
from pymongo import MongoClient
from celery import shared_task
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = os.getenv("LLM_MODEL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
model = OpenAIChatModel(
    model_name=MODEL_NAME,  # or any other OpenRouter model
    provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
)

# Batch processing configuration
BATCH_SIZE = 5  # Process 5 articles at a time

# Italian business sectors
SECTORS = [
    "Abbigliamento e tessili",
    "Imprese edili per il restauro",
    "Piastrelle in ceramica",
    "Aerospazio",
    "Industria enologica",
    "Prodotti chimici",
    "Agro-alimentare",
    "Informatica",
    "Prodotti di gomma e plastica",
    "Apparecchiature e materiali per la sicurezza",
    "Infrastrutture",
    "Prodotti farmaceutici e relative materie prime",
    "Architettura e urbanistica",
    "Infrastrutture e sovrastrutture per strade ferrate",
    "Prodotti siderurgici",
    "Articoli decorativi e da regalo",
    "Intersettoriale",
    "Pulizia, disinfezione e disinfestazione",
    "Articoli per la casa e arredamento",
    "Istruzione e formazione",
    "Raccolta e smaltimento dei rifiuti",
    "Articoli per l'illuminazione",
    "Macchinari",
    "Restauro architettonico e strutturale",
    "Articoli sportivi e abbigliamento per lo sport",
    "Macchine agricole e per l'orticoltura",
    "Restauro artistico e storico",
    "Attrezzature aeronautiche ed aeroportuali",
    "Macchine confezionatrici",
    "Restauro monumentale museale e archeologico",
    "Attrezzature per alberghi, ristoranti e bar",
    "Macchine per la lavorazione del legno",
    "Ricerca e sviluppo",
    "Biotecnologie",
    "Macchine per la lavorazione della gomma e della plastica",
    "Riparazione e manutenzione",
    "Carta, tipografia, editoria e cartoleria",
    "Macchine per la produzione di gioielli",
    "Servizi commerciali",
    "Cinematografia",
    "Macchine per l'edilizia e per la produzione di materiali edili",
    "Servizi di sicurezza",
    "Consulenza e esperti",
    "Macchine per l'industria alimentare",
    "Servizi di telecomunicazione",
    "Cosmetici e prodotti per l'igiene personale",
    "Macchine per l'industria della carta e delle arti grafiche",
    "Servizi diversi",
    "E-commerce",
    "Macchine per l'industria delle calzature e della pelletteria",
    "Servizi finanziari",
    "Edilizia: Lavori e costruzioni",
    "Macchine per l'industria tessile",
    "Servizi informatici",
    "Elettrodomestici",
    "Macchine utensili per la lavorazione dei metalli",
    "Servizi tecnici",
    "Elettronica di consumo",
    "Materiali per l'edilizia",
    "Strumenti musicali",
    "Elettronica industriale e professionale",
    "Meccatronica",
    "Studi di architettura",
    "Energia",
    "Minerali e metalli",
    "Studi di ingegneria",
    "Energia elettrica",
    "Nanotecnologie",
    "Subfornitura",
    "Formazione",
    "Nautica",
    "Televisori e radio, audiovisivi",
    "Gas e energie alternative",
    "Non catalogabile merceologicamente",
    "Trasporti e logistica",
    "Gioielli e bigiotteria",
    "Ottica",
    "Turismo",
    "Impianti anti-inquinamento",
    "Pelli ed articoli di pelletteria",
    "Veicoli, industria meccanica, elettrotecnica ed elettronica",
    "Impianti di telecomunicazione",
    "Petrolio e derivati",
    "Vino e altre bevande",
    "Economia in generale",
]


class TranslatedArticle(BaseModel):
    """Structured output for translated business articles in Italian"""

    titolo: str = Field(description="Il titolo tradotto in italiano")
    contenuto: str = Field(
        description="Il contenuto dell'articolo tradotto in italiano"
    )
    settore: str = Field(description="Il settore più rilevante per l'articolo")

    @field_validator("settore")
    @classmethod
    def validate_settore(cls, v: str) -> str:
        if v not in SECTORS:
            raise ValueError("sector must be one of the predefined sectors")
        return v


def get_system_prompt(source: str = "the source") -> str:
    """Get the system prompt for translation."""
    sectors_list = "\n".join(f"- {sector}" for sector in SECTORS)

    return f"""You are an expert translator specializing in business and financial news.
    
Your task is to translate English or Serbian business articles into Italian with these requirements:

TRANSLATION GUIDELINES:
- Keep the title concise and short with the sector and the main takeaway present, shorten if needed
- Translate the title to Italian and make it informative, do not leave words in Serbian or English
- Maintain professional business terminology and accuracy of financial/economic terms
- Use formal Italian suitable for business publications
- Keep a clear and engaging style
- Remove all references to images, graphs, or tables from HTML content
- Preserve exact numbers, dates, names, and places from the original
- When the source mentions "our" or "ours" in Serbian context, clarify it refers to Serbia/Serbian
- Emphasize at the end what is the opportunity for italian companies if any but only as part of a general comment
- Do not attribute this opportunity comment to any specific company or person or institution
- If the article is about a specific company, do not mention the company name in the title unless it is crucial for understanding
- If the article is not in any way useful for Italian companies, or relates to Montenegro, just respond with "NON PERTINENT" as the title and leave the content empty
- For the sector field, choose the most relevant sector from the following list: {sectors_list}
- Make the title short and concise, ideally under 6 words: if the title is longer, shorten it while keeping the main point
- Example of a good title: "Crescita del 10% nel settore energetico", "Nuove opportunità per le imprese edili"
- Remove any references to links, like available HERE and so on since they won't be clickable in the italian version
- When referencing "us" remember that the source is {source}, so As we were told means according to {source} sources
- Do not use "fonte mediatica" or "fonte media" in the translation, but "come riportato da {source}"
- Cite the source only regarding the facts of the article, not the opportunity for Italy part
- Do not use "fonte mediatica" or "fonte media" in the translation, but "come riportato da {source}"
- Mark articles dealing with Montenegro as not pertinent and do not translate them
- Do not use markdown formatting in the translation, only plain text is allowed
- Feel free to shorten the article a bit and convey meaning using Italian business language, not necessarily doing a word per word translation
- Do not use any business jargon or business language that is not common in Italian business language
- Use a bit higher level of language
- Shorten long articles to about 2000 characters but keep the facts precise
- DO not add any additional information not present in the original article
- DO not add any additional comments not present in the original article
- Keep a serious and official style and insert "as stated by the source media - {source}" if needed


OUTPUT REQUIREMENTS:
- Provide clean, publication-ready Italian translations
- Ensure the translation maintains the tone and style appropriate for business news"""


def get_mongodb_connection():
    """Get MongoDB connection using settings from Django or environment variables."""
    mongo_uri = getattr(
        settings,
        "MONGODB_URI",
        os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true"),
    )
    mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))
    mongo_collection = getattr(
        settings, "MONGO_COLLECTION", os.getenv("MONGO_COLLECTION", "articles")
    )

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    collection = db[mongo_collection]

    return client, collection


async def translate_article_async(
    title: str,
    content: str,
    source: str = "Unknown",
    source_language: str = "en",
    wait_time: int = 10,
) -> Dict[str, Any]:
    """
    Translate a single article to Italian.

    Args:
        title: Article title in source language
        content: Article content in source language
        source_language: Source language code ("en" for English, "rs" for Serbian)
        wait_time: Seconds to wait before translation (rate limiting)

    Returns:
        Dict with translated content and metadata
    """
    # Create the agent
    agent = Agent(
        model=model,
        output_type=TranslatedArticle,
        system_prompt=get_system_prompt(source),
    )

    # Determine language label for prompt
    language_label = "English" if source_language == "en" else "Serbian"

    prompt = f"""Translate this business article from {language_label} to Italian.

Article to translate:
Titolo: {title}
Contenuto: {content}
Fonte: {source}

Provide a professional Italian translation suitable for business publications."""

    # Wait for rate limiting
    if wait_time > 0:
        logger.info(f"Waiting {wait_time} seconds to avoid rate limits...")
        sleep(wait_time)

    try:
        result = await agent.run(prompt)
        translated = result.output

        return {
            "title_it": translated.titolo,
            "content_it": translated.contenuto,
            "sector": translated.settore,
            "llm_model": MODEL_NAME,
            "time_translated": datetime.utcnow(),
            "translation_success": True,
            "status": "PENDING",
        }
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return {
            "title_it": None,
            "content_it": None,
            "sector": None,
            "llm_model": "chatgp40mini",
            "time_translated": datetime.utcnow(),
            "translation_success": False,
            "translation_error": str(e),
        }


def translate_article(
    title: str,
    content: str,
    source: str = "Unknown",
    source_language: str = "en",
    wait_time: int = 10,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for translate_article_async.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            translate_article_async(title, content, source, source_language, wait_time)
        )
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3, name="translate_untranslated_articles")
def translate_untranslated_articles(self, limit: int = None):
    """
    Translate all articles that don't have Italian translations.

    Args:
        limit: Maximum number of articles to translate (None for all)

    Returns:
        Dict with translation statistics
    """
    client = None

    try:
        # Get MongoDB connection
        client, collection = get_mongodb_connection()

        # Find untranslated articles (missing title_it OR content_it) AND exclude NON PERTINENT articles
        query = {
            "$and": [
                # Regular untranslated criteria
                {"$or": [
                    {"title_it": {"$exists": False}},
                    {"title_it": None},
                    {"title_it": ""},
                    {"content_it": {"$exists": False}},
                    {"content_it": None},
                    {"content_it": ""},
                ]},
                # Exclude articles already marked as NON PERTINENT
                {"title_it": {"$ne": "NON PERTINENT"}}
            ]
        }

        # Get count of untranslated articles
        total_untranslated = collection.count_documents(query)
        logger.info(f"Found {total_untranslated} untranslated articles")

        if total_untranslated == 0:
            return {
                "status": "success",
                "message": "No untranslated articles found",
                "translated": 0,
                "failed": 0,
                "total": 0,
            }

        # Determine number of articles to process
        articles_to_process = min(
            limit if limit else total_untranslated, total_untranslated
        )

        # Fetch untranslated articles
        cursor = collection.find(query).limit(articles_to_process)
        articles = list(cursor)

        translated_count = 0
        failed_count = 0
        errors = []

        # Process articles in batches
        for batch_start in range(0, len(articles), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(articles))
            batch = articles[batch_start:batch_end]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = ((len(articles) - 1) // BATCH_SIZE) + 1

            logger.info(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)"
            )

            for idx, article in enumerate(batch):
                article_num = batch_start + idx + 1

                try:
                    # Get content (handle both English and Serbian fields)
                    title_en = article.get("title_en")
                    content_en = article.get("content_en")
                    title_rs = article.get("title_rs")
                    content_rs = article.get("content_rs")

                    # Determine which language to use
                    if title_en and content_en:
                        title = title_en
                        content = content_en
                        source_language = "en"
                        language_label = "English"
                    elif title_rs and content_rs:
                        title = title_rs
                        content = content_rs
                        source_language = "rs"
                        language_label = "Serbian"
                    else:
                        logger.warning(
                            f"Article {article.get('_id')} missing title or content in both languages, skipping"
                        )
                        continue

                    logger.info(
                        f"[{article_num}/{articles_to_process}] Translating {language_label}: {title[:50]}..."
                    )

                    # Get source information
                    source = article.get("source", "Unknown")

                    # Translate the article (wait time is 0 for first article in batch, 10 for others)
                    wait_time = 0 if idx == 0 else 10
                    translation_result = translate_article(
                        title=title,
                        content=content,
                        source=source,
                        source_language=source_language,
                        wait_time=wait_time,
                    )

                    if translation_result["translation_success"]:
                        # Check if the article was marked as NON PERTINENT by the LLM
                        if translation_result["title_it"] == "NON PERTINENT":
                            logger.info(f"⏭️ Skipping NON PERTINENT article: {title[:50]}...")
                            
                            # Mark as NON PERTINENT and skip further processing
                            collection.update_one(
                                {"_id": article["_id"]},
                                {"$set": {
                                    "title_it": "NON PERTINENT",
                                    "content_it": "",  # Empty content as per instructions
                                    "time_translated": translation_result["time_translated"],
                                    "llm_model": translation_result["llm_model"],
                                    "status": "DISCARDED",  # Mark as discarded
                                }}
                            )
                            
                            translated_count += 1  # Count as processed
                            continue
                            
                        # Update MongoDB with translated content
                        update_data = {
                            "title_it": translation_result["title_it"],
                            "content_it": translation_result["content_it"],
                            "sector": translation_result["sector"],
                            "time_translated": translation_result["time_translated"],
                            "llm_model": translation_result["llm_model"],
                        }

                        collection.update_one(
                            {"_id": article["_id"]}, {"$set": update_data}
                        )

                        translated_count += 1
                        logger.info(
                            f"✅ Successfully translated: {translation_result['title_it'][:50] if translation_result['title_it'] else 'N/A'}..."
                        )
                    else:
                        # Handle translation failure
                        failed_count += 1
                        error_msg = translation_result.get(
                            "translation_error", "Unknown error"
                        )
                        errors.append(
                            {
                                "article_id": str(article["_id"]),
                                "title": title_en[:50],
                                "error": error_msg,
                            }
                        )

                        # Mark as failed in MongoDB
                        collection.update_one(
                            {"_id": article["_id"]},
                            {
                                "$set": {
                                    "translation_error": error_msg,
                                    "translation_attempted": datetime.utcnow(),
                                }
                            },
                        )
                        logger.error(f"❌ Failed to translate article: {error_msg}")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Unexpected error: {str(e)}"
                    errors.append(
                        {
                            "article_id": str(article.get("_id", "unknown")),
                            "error": error_msg,
                        }
                    )
                    logger.error(error_msg)

        # Final summary
        result = {
            "status": "success",
            "message": "Translation batch completed",
            "total": articles_to_process,
            "translated": translated_count,
            "failed": failed_count,
            "errors": errors[:5],  # Return only first 5 errors
        }

        logger.info(
            f"📊 Translation Summary: {translated_count}/{articles_to_process} succeeded, {failed_count} failed"
        )
        return result

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    finally:
        if client:
            client.close()
