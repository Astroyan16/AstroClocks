# AstroClocks

AstroClocks v3.1 affiche les temps civil, UTC, sidéral, les coordonnées JNow,
l'angle horaire et une carte du ciel en temps réel avec grille AltAz, grille
équatoriale, magnitude limite réglable, catalogue embarqué de 6000 étoiles
brillantes et objets principaux du système solaire.
La version 3.1 ajoute aussi un onglet de visibilité de la cible et un outil de
recherche d'étoiles doubles/binaires avec catalogue WDS local et enrichissement
en ligne quand la connexion est disponible.

## Installation

Depuis ce dossier, créez un environnement Python puis installez les dépendances :

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

`tkinter` est fourni avec Python sous Windows. Les recherches d'objets, la vue
Aladin Lite et le rafraîchissement du catalogue WDS nécessitent une connexion
internet.

La version v3.0 stable reste conservée dans l'historique git avec le tag
`v3.0-stable`.
