# Architecture

## Vue d'ensemble

```
SubtitleTranslator/
├── install.sh              # Crée les venvs et installe les dépendances
├── run.sh                  # Lance le serveur web local
├── README.md
├── docs/
│   ├── ARCHITECTURE.md     # Ce fichier
│   └── MODELS.md           # Détail des modèles de traduction
├── app/                    # Application principale (venv « app »)
│   ├── main.py             # Serveur FastAPI : API + interface web
│   ├── requirements.txt
│   ├── core/
│   │   ├── paths.py        # Chemins du projet (tout est relatif au dossier)
│   │   ├── languages.py    # Langues supportées (codes ISO 639-1)
│   │   ├── detect.py       # Détection automatique de la langue source
│   │   ├── subtitles.py    # Lecture/écriture des fichiers de sous-titres
│   │   ├── registry.py     # Catalogue des modèles + état installé/non installé
│   │   ├── workers.py      # Invocation des workers dans leurs venvs
│   │   └── jobs.py         # Gestion des jobs de traduction (threads, progression)
│   └── static/             # Interface web (HTML/CSS/JS vanilla)
├── backends/               # Workers de traduction, un par venv
│   ├── argos/
│   │   ├── worker.py       # Argos Translate (venv « argos »)
│   │   └── requirements.txt
│   ├── hf/
│   │   ├── worker.py       # Modèles Hugging Face : NLLB, M2M100 (venv « hf »)
│   │   └── requirements.txt
│   └── api/
│       ├── worker.py       # LibreTranslate — option EN LIGNE (venv « app »)
│       └── (pas de venv dédié : dépendances légères, incluses dans « app »)
├── venvs/                  # ⚠ généré par install.sh — jamais commité
│   ├── app/
│   ├── argos/
│   └── hf/
├── models/                 # ⚠ modèles téléchargés — jamais commité
│   ├── argos/packages/     # Paires de langues Argos (ARGOS_PACKAGES_DIR)
│   ├── hf/                 # Cache Hugging Face (HF_HOME)
│   └── cache/              # Caches divers (XDG_CACHE_HOME)
└── data/                   # ⚠ fichiers de travail — jamais commité
    ├── jobs/<id>/          # Fichier source + résultat de chaque job
    └── config.json         # Configuration (ex. URL LibreTranslate)
```

## Pourquoi plusieurs venvs ?

Les backends de traduction ont des dépendances lourdes et potentiellement incompatibles entre elles (versions de `torch`, `ctranslate2`, `sentencepiece`, `numpy`…). Chaque backend vit donc dans son propre venv :

| Venv | Contenu | Rôle |
|---|---|---|
| `venvs/app` | FastAPI, uvicorn, pysubs2, langdetect, requests | Serveur web, parsing des sous-titres, détection de langue, backend API |
| `venvs/argos` | argostranslate (ctranslate2, sentencepiece) | Traduction Argos Translate |
| `venvs/hf` | torch (CPU), transformers, sentencepiece | Traduction NLLB / M2M100 |

L'application principale ne importe **jamais** les bibliothèques de traduction : elle lance les workers en sous-processus avec l'interpréteur Python du venv concerné.

## Protocole worker

Chaque `backends/<b>/worker.py` est un CLI autonome :

```
worker.py translate --input in.json --output out.json --model <id> --source fr --target en
worker.py install   --model <id> | --pair en:fr        # nécessite internet
worker.py uninstall --model <id> | --pair en:fr
worker.py available                                     # (argos) paires installables
```

- `in.json` : `{"texts": ["ligne 1", "ligne 2", …]}`
- `out.json` : `{"texts": ["…traduit…", …]}`
- Progression : le worker écrit sur stdout des lignes JSON `{"type": "progress", "value": 0.42}` que l'application relaie vers l'interface.
- Pendant une traduction, l'application impose `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` : aucun accès réseau, même par accident.

## Confinement dans le dossier

Toutes les écritures passent par des variables d'environnement pointées vers `models/` :

- `HF_HOME` → `models/hf` (cache Hugging Face)
- `ARGOS_PACKAGES_DIR` → `models/argos/packages`
- `XDG_DATA_HOME` / `XDG_CACHE_HOME` → `models/xdg`, `models/cache`

Aucun fichier n'est écrit dans `~/.cache`, `~/.local` ni ailleurs sur le système.

## Flux d'un job de traduction

1. L'utilisateur téléverse le fichier → sauvegardé dans `data/jobs/<id>/`.
2. `subtitles.py` parse le fichier (pysubs2) et extrait le texte de chaque réplique.
3. Si langue source = « auto », `detect.py` (langdetect) l'identifie sur un échantillon.
4. `workers.py` lance le worker du backend choisi dans son venv ; la progression remonte par stdout.
5. Les textes traduits sont réinjectés dans les répliques (horodatages intacts) et le fichier de sortie est écrit dans le format demandé.
6. L'interface propose le téléchargement.

Les jobs tournent dans des threads ; l'interface les suit par polling sur `GET /api/jobs/<id>`.

## API HTTP

| Méthode & route | Rôle |
|---|---|
| `GET /` | Interface web |
| `GET /api/languages` | Langues supportées |
| `GET /api/models` | Catalogue + état (installé, en cours d'installation…) |
| `POST /api/models/install` | Installe un modèle (tâche de fond) |
| `POST /api/models/uninstall` | Désinstalle un modèle |
| `GET /api/models/argos/available` | Paires Argos installables (internet requis) |
| `GET/POST /api/config` | Configuration (URL LibreTranslate…) |
| `POST /api/jobs` | Crée un job (multipart : fichier + paramètres) |
| `GET /api/jobs/{id}` | État / progression du job |
| `GET /api/jobs/{id}/download` | Fichier traduit |
