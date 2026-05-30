# Video Extractor

Application Windows légère en Python pour scanner un dossier vidéo, afficher les fichiers, prévisualiser chaque vidéo, choisir les points de début/fin et exporter les extraits.

## Prérequis

- Python 3.12+
- FFmpeg installé et disponible dans le `PATH`
- VS Code (optionnel)

## Installation

1. Créez un environnement virtuel :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Installez les dépendances :

```powershell
pip install -r requirements.txt
```

3. Vérifiez que FFmpeg fonctionne :

```powershell
ffmpeg -version
```

## Utilisation

```powershell
python main.py
```

## Fonctionnalités

- scanner un dossier de vidéos
- lister les fichiers vidéo
- lecture et prévisualisation dans l'application
- définir le début et la fin par simple clic
- exporter automatiquement un extrait
- les extraits sont enregistrés dans le dossier `clips`
