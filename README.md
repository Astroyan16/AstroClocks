# AstroClocks

AstroClocks v3.0 affiche les temps civil, UTC, sideral, les coordonnees JNow,
l'angle horaire et une carte du ciel equatoriale en temps reel.

## Installation

Depuis ce dossier, creez un environnement Python puis installez les dependances :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Lancez ensuite l'application :

```powershell
python AstroClocks-v3.0.py
```

`tkinter` est fourni avec Python sous Windows. Les recherches d'objets et la vue
Aladin Lite necessitent une connexion internet.
