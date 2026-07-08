"""Langues exposées dans l'interface (codes ISO 639-1).

Les workers font eux-mêmes la conversion vers leurs codes internes
(ex. NLLB utilise « fra_Latn »). Pour ajouter une langue ici, vérifier
qu'elle est couverte dans backends/hf/worker.py (table FLORES)."""

LANGUAGES = {
    "fr": "Français",
    "en": "Anglais",
    "es": "Espagnol",
    "de": "Allemand",
    "it": "Italien",
    "pt": "Portugais",
    "nl": "Néerlandais",
    "ru": "Russe",
    "zh": "Chinois",
    "ja": "Japonais",
    "ko": "Coréen",
    "ar": "Arabe",
    "tr": "Turc",
    "pl": "Polonais",
    "sv": "Suédois",
    "da": "Danois",
    "fi": "Finnois",
    "no": "Norvégien",
    "cs": "Tchèque",
    "el": "Grec",
    "he": "Hébreu",
    "hi": "Hindi",
    "id": "Indonésien",
    "uk": "Ukrainien",
    "ro": "Roumain",
    "hu": "Hongrois",
    "bg": "Bulgare",
    "th": "Thaï",
    "vi": "Vietnamien",
    "ca": "Catalan",
}
