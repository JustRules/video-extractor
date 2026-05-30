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

## Version exécutable Windows

1. Activez l'environnement virtuel :

```powershell
.\.venv\Scripts\Activate.ps1
```

2. Exécutez le script de build :

```powershell
.\build-exe.ps1
```

- ou double-cliquez sur `build-exe.bat` si vous préférez lancer le build sans saisie manuelle.

3. L'exécutable se trouve ensuite dans le dossier `dist` :

- `dist\video-extractor.exe`

> Note : FFmpeg doit être installé et disponible dans le `PATH` pour que l'application fonctionne correctement.

## Fonctionnalités

- scanner un dossier de vidéos
- lister les fichiers vidéo
- lecture et prévisualisation dans l'application
- définir le début et la fin par simple clic
- exporter automatiquement un extrait
- les extraits sont enregistrés dans le dossier `clips`
