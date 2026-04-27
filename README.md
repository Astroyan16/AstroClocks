# AstroClocks

AstroClocks v3.1 affiche les temps civil, UTC, sideral, les coordonnees JNow,
l'angle horaire et une carte du ciel en temps reel avec grille AltAz, grille
equatoriale, magnitude limite reglable et objets principaux du systeme solaire.

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
python AstroClocks-v3.1.py
```

`tkinter` est fourni avec Python sous Windows. Les recherches d'objets et la vue
Aladin Lite necessitent une connexion internet.

La version v3.0 stable reste conservee dans l'historique git avec le tag
`v3.0-stable`.
