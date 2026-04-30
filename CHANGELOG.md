# Changelog

## AstroClocks v3.2 stable - 2026-04-30

### Ajoute

- Nouvelle version Windows v3.2 avec script de lancement, spec PyInstaller et script Inno Setup dédiés.
- Carte du ciel en temps réel enrichie avec grille AltAz, grille équatoriale, magnitude limite réglable, catalogue embarqué d'étoiles brillantes et objets principaux du système solaire.
- Catalogues locaux pour accélérer les recherches d'objets et améliorer le fonctionnement sans connexion.
- Rendu des étoiles par sprites pour une carte du ciel plus lisible et plus fluide.
- Tests unitaires couvrant les conversions de coordonnées, les catalogues locaux, les sprites stellaires et les calculs ORB6.

### Ameliore

- L'onglet de visibilité de la cible reste conservé pendant les recalculs de planètes.
- La fenêtre d'orbite des étoiles doubles affiche maintenant en permanence la position du jour, avec une ligne séparée pour les valeurs liées au curseur.
- Les années des points d'orbite et la mention "Maintenant" sont placées à l'extérieur de la courbe, près du point correspondant, avec un trait de liaison discret.
- L'installeur v3.2 conserve l'AppId stable pour mettre à jour AstroClocks proprement et propose l'option de lancement au démarrage de Windows.

### Corrige

- Correction du parseur ORB6 pour les périodes longues en jours, par exemple `43089 d` n'est plus lu comme `3089 d`.
- Correction du solveur de Kepler pour les orbites très excentriques proches du périastre.
- Conversion cohérente des rares axes orbitaux ORB6 exprimés en minutes d'arc vers les secondes d'arc affichées par l'interface.
- Synchronisation entre les valeurs ORB6 tabulées et les positions recalculées dans la fenêtre d'orbite.
- Pour `WDS J09285+0903`, la position du 30/04/2026 est maintenant cohérente avec ORB6 : environ `rho = 0.964"` et `theta = 120.4 deg`.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Audit ORB6 : 3 360 paires appariées et 16 800 prédictions comparées entre `orb6ephem.txt` et le recalcul depuis `orb6orbits.txt`.
- Smoke test du build Windows v3.2.
- Artefact Windows distribué : `installer/Install_AstroClocks3.2.exe`.

## AstroClocks v3.1 - 2026-04-27

- Ajout des outils de carte du ciel et de recherche d'étoiles doubles.
- Ajout du support initial des orbites ORB6.
- Ajout du build Windows PyInstaller et de l'installeur Inno Setup.

## AstroClocks v3.0 stable

- Version stable conservée avec le tag `v3.0-stable`.
