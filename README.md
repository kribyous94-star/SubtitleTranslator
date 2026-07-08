# SubtitleTranslator

Logiciel de traduction de sous-titres **100 % local et hors ligne** (SRT, VTT, ASS/SSA, SUB, TMP).

On fournit un fichier de sous-titres, on précise la langue source (ou on laisse le logiciel la détecter), on choisit la langue cible et le modèle de traduction, puis on lance le job. Le fichier traduit conserve les horodatages d'origine.

## Principes

- **Tout est contenu dans ce dossier** : environnements Python (`venvs/`), modèles IA (`models/`), fichiers de travail (`data/`). Supprimer le dossier supprime tout — rien n'est installé ailleurs sur le système.
- **Hors ligne d'abord** : une fois l'installation et le téléchargement des modèles effectués, aucune connexion internet n'est nécessaire. Un backend en ligne (LibreTranslate) existe en option, mais ce n'est pas le cœur du projet.
- **Plusieurs venvs** : chaque famille de backends a son propre environnement virtuel pour éviter les conflits de dépendances (voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- **Modèles gérables depuis le logiciel** : installation et désinstallation des modèles directement depuis l'interface, dans le dossier du projet.

## Installation

```bash
./install.sh
```

Options :

| Option | Effet |
|---|---|
| `--no-hf` | Ne pas installer le backend Hugging Face (NLLB, M2M100) — le plus lourd (PyTorch) |
| `--no-argos` | Ne pas installer le backend Argos Translate |

L'installation crée les venvs et installe les bibliothèques. Les **modèles** se téléchargent ensuite depuis l'interface (onglet « Modèles »), une seule fois, puis tout fonctionne hors ligne.

## Lancement

```bash
./run.sh
```

Puis ouvrir <http://127.0.0.1:8765> dans un navigateur.

## Utilisation

1. **Traduire** : déposer le fichier de sous-titres, choisir la langue source (« Détection automatique » possible), la langue cible et le modèle, puis lancer. Une barre de progression suit le job ; le fichier traduit se télécharge à la fin.
2. **Modèles** : installer/désinstaller les modèles. Pour Argos Translate, on installe des paires de langues (ex. `en → fr`, ~100 Mo chacune). Pour NLLB/M2M100, un seul modèle couvre des dizaines de langues (~1,9 à 2,5 Go).

## Modèles disponibles

Voir [docs/MODELS.md](docs/MODELS.md) pour le détail (tailles, qualités, langues couvertes).

| Modèle | Backend | Hors ligne | Taille |
|---|---|---|---|
| Argos Translate (par paire de langues) | argos | ✅ | ~100 Mo / paire |
| NLLB-200 distilled 600M | hf | ✅ | ~2,5 Go |
| M2M100 418M | hf | ✅ | ~1,9 Go |
| LibreTranslate (API) | api | ❌ (option en ligne) | — |

## Formats supportés

SRT, WebVTT, ASS, SSA, SUB (MicroDVD), TMP — lecture et écriture via [pysubs2](https://pysubs2.readthedocs.io/). Le format de sortie est par défaut identique au format d'entrée.

## Désinstallation

```bash
rm -rf SubtitleTranslator/
```

C'est tout : venvs, modèles et données vivent dans le dossier.
