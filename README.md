# AstroClocks

AstroClocks v3.3.6 est une application d'aide a l'observation astronomique
pour Windows. Elle affiche en temps reel l'heure civile, l'UTC, les temps
sideraux, les coordonnees JNow/J2000, l'angle horaire, une carte du ciel
locale, ainsi que plusieurs outils de recherche et de preparation
d'observations.

## Fonctionnalites

- Carte du ciel temps reel avec grille AltAz, grille equatoriale, magnitude
  limite reglable, etoiles nommees et objets principaux du systeme solaire.
- Onglet de visibilite de la cible avec suivi jour par jour.
- Recherche d'etoiles doubles avec catalogue local WDS, enrichissement en ligne
  et recalcul ORB6.
- Recherche d'objets du ciel profond avec catalogue embarque et enrichissement
  en ligne SIMBAD/CDS.
- Recherche d'etoiles avec filtres spectraux, photometriques et de visibilite.
- Integration ASCOM sur Windows pour connecter une monture, recuperer ses
  coordonnees et afficher un reticule `Telescope` sur la carte du ciel.
- Choix global entre les coordonnees du logiciel et celles de la monture ASCOM
  pour garder une base de site coherente dans toute l'application.
- Verification des mises a jour GitHub depuis la fenetre `A propos`, avec
  verification automatique silencieuse au demarrage.
- Fenetre de parametres organisee par onglets (`General`, `Sky`, `Mount`).

## Installation

Depuis ce dossier, creez un environnement Python puis installez les
dependances :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement en developpement

Pour lancer l'application depuis les sources, utilisez de preference le Python
du projet :

```powershell
.\.venv\Scripts\python.exe .\AstroClocks-v3.3.py
```

`tkinter` est fourni avec Python sous Windows. Le support ASCOM necessite
`pywin32`, installe automatiquement via `requirements.txt`.

## Build Windows

Pour generer l'executable PyInstaller et l'installeur Inno Setup :

```powershell
.\Build-Windows.ps1
```

Les artefacts sont produits dans :

- `output/AstroClockV3/`
- `installer/Install_AstroClocks<version>.exe`

## Fonctions en ligne

Une connexion internet est necessaire pour :

- la recherche en ligne d'objets et d'etoiles ;
- l'enrichissement des catalogues WDS, ORB6 et SIMBAD/CDS ;
- la vue Aladin Lite ;
- la verification des mises a jour GitHub.

Le mecanisme de mise a jour integree repose sur les GitHub Releases publiques du
depot.

## Historique stable

Les versions stables publiees sont reperees par des tags Git du type
`vX.Y.Z-stable`. La version `v3.0-stable` reste egalement conservee dans
l'historique.

## Roadmap

La feuille de route de maintenance et d'evolution est disponible dans
[ROADMAP.md](ROADMAP.md).

## Licence

AstroClocks est distribue sous la licence `GNU GPL v3.0 only`.
Le texte complet est disponible dans [LICENSE](LICENSE).
