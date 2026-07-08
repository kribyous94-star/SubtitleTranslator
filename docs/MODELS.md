# Modèles de traduction

Tous les modèles s'installent et se désinstallent **depuis l'interface** (onglet « Modèles ») et sont stockés dans `models/`, à l'intérieur du dossier du projet. Le téléchargement nécessite internet une seule fois ; la traduction est ensuite entièrement hors ligne (sauf backend API).

## Argos Translate (backend `argos`) — hors ligne ✅

- **Fonctionnement** : un petit modèle (~100 Mo) par **paire de langues** (ex. `en → fr`). On n'installe que les paires dont on a besoin.
- **Qualité** : correcte, très rapide sur CPU (moteur CTranslate2).
- **Particularité** : certaines paires n'existent pas en direct ; Argos pivote alors par l'anglais automatiquement (ex. `fr → de` = `fr → en → de`) si les deux paires sont installées.
- **Recommandé pour** : machines modestes, besoins ciblés sur quelques paires de langues.

## NLLB-200 distilled 600M (backend `hf`) — hors ligne ✅

- **Modèle** : `facebook/nllb-200-distilled-600M` (~2,5 Go sur disque).
- **Qualité** : la meilleure du lot, couvre ~200 langues avec un seul modèle.
- **Vitesse** : plus lent qu'Argos sur CPU (PyTorch). Traduction par lots pour compenser.
- **Recommandé pour** : la meilleure qualité hors ligne, langues peu courantes.

## M2M100 418M (backend `hf`) — hors ligne ✅

- **Modèle** : `facebook/m2m100_418M` (~1,9 Go sur disque).
- **Qualité** : bonne, ~100 langues, traduction directe entre toutes les paires (sans pivot par l'anglais).
- **Recommandé pour** : alternative plus légère à NLLB, paires ne passant pas par l'anglais.

## LibreTranslate (backend `api`) — en ligne ❌

- **Fonctionnement** : appelle une instance LibreTranslate par HTTP (URL et clé API configurables dans l'interface). Peut pointer vers une instance auto-hébergée sur le réseau local.
- **Statut** : simple **option** — le cœur du projet reste hors ligne. Rien ne casse si ce backend n'est jamais utilisé.

## Langues supportées par l'interface

Une trentaine de langues courantes sont exposées dans l'interface (français, anglais, espagnol, allemand, italien, portugais, néerlandais, russe, chinois, japonais, coréen, arabe, turc, polonais, suédois, danois, finnois, norvégien, tchèque, grec, hébreu, hindi, indonésien, ukrainien, roumain, hongrois, bulgare, thaï, vietnamien, catalan). Les modèles NLLB/M2M100 en couvrent bien davantage ; la liste de l'interface peut être étendue dans `app/core/languages.py`.

## Détection de langue

La détection automatique de la langue source utilise `langdetect` (léger, hors ligne, dans le venv `app`) sur un échantillon des répliques du fichier.

## Ajouter un nouveau modèle

1. Si ses dépendances sont compatibles avec un backend existant, l'ajouter au catalogue dans `app/core/registry.py` et gérer son cas dans le `worker.py` du backend.
2. Sinon, créer `backends/<nouveau>/` (worker.py + requirements.txt), ajouter le venv dans `install.sh`, puis le déclarer dans le catalogue.
