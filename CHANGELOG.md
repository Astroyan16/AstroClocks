# Changelog

## AstroClocks v3.3.7 stable - 2026-05-14

### Ajoute

- Bloc de controle `Monture ASCOM` sous la carte du ciel avec commandes `Pointer la cible` et `Arreter` pour les montures compatibles GoTo.
- Boite de confirmation thematisee avant un `GoTo` vers une cible situee sous l'horizon.
- Script `Verify-Release.ps1` et [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) pour verrouiller la coherence des publications Windows.

### Ameliore

- Recherche hors-ligne/en ligne plus robuste : les boutons de recherche en ligne se desactivent proprement hors-ligne ou pendant une requete, tandis que les actions locales restent disponibles.
- Les onglets `Etoiles doubles`, `Ciel profond` et `Etoiles` indiquent maintenant explicitement quand des donnees enrichies en cache sont reutilisees hors-ligne.
- Le statut monture distingue mieux les etats `Pointage en cours`, `Prete a pointer` et `Cible acquise`, avec affichage de la disponibilite GoTo dans `Parametres > Monture`.
- Les erreurs et avertissements lies au bloc de controle de monture utilisent maintenant des dialogues AstroClocks harmonises avec le theme sombre.

### Corrige

- Le bouton `Arreter` fonctionne maintenant aussi avec les drivers ASCOM qui exposent `AbortSlew()` sans declarer correctement `CanAbortSlew`.
- Le statut sous la carte reste coherent quand la cible active provient d'une recherche en ligne IMCCE plutot que d'un calcul local.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Compilation Python des modules modifies.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Verification de release via `Verify-Release.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.7.exe`.

## AstroClocks v3.3.6 stable - 2026-05-14

### Ameliore

- L'executable Windows distribue garde maintenant un nom fixe `AstroClockV3.exe`, ce qui evite de casser les raccourcis epingles a chaque release.
- La chaine de build et l'installeur ont ete re-alignes sur ce nom d'executable stable, tout en conservant des installeurs versionnes.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Compilation Python des modules modifies.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.6.exe`.

## AstroClocks v3.3.5 stable - 2026-05-14

### Ameliore

- Detection reseau plus tolerante : l'etat `Hors-ligne` n'est active qu'apres deux echecs consecutifs afin d'eviter les bascules intempestives.
- Carte du ciel polie sur les cas limites : meilleur placement des labels pres des bords, reticules cible et monture plus lisibles sur plusieurs tailles de carte, et zone de statut plus stable.
- Onglet `Mount` des parametres affine visuellement avec un comportement plus coherent des options et un meilleur verrouillage de la source de coordonnees tant qu'aucune monture n'est connectee.
- Affichage des recherches de coordonnees clarifie quand un resultat local est utilise en repli apres une tentative de recherche en ligne.

### Corrige

- Le rendu des petits dialogues et des lignes de statut a ete nettoye pour eviter plusieurs incoherences visuelles observees pendant les tests d'usage reel.
- Le choix entre coordonnees locales et coordonnees en ligne pour les objets du systeme solaire reste maintenant coherent entre la recherche rapide et l'affichage sous la carte.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Compilation Python des modules modifies.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.5.exe`.

## AstroClocks v3.3.4 stable - 2026-05-12

### Ajoute

- Choix global de la source des coordonnees (`Parametres AstroClocks` ou `Monture ASCOM`) pour que toute l'application utilise la meme base de site active.

### Ameliore

- Integration ASCOM davantage fiabilisee : etats de connexion plus explicites, statut `Mount` plus clair, meilleure gestion des erreurs SynScan et rafraichissement de la monture plus reactif.
- Mecanisme de mise a jour GitHub durci avec une meilleure gestion des cas `release` incoherente, JSON invalide, timeout, reseau indisponible et installeur vide.
- Zone de statut sous la carte du ciel reorganisee : compteur d'etoiles sur une ligne dediee, formatage harmonise en `JNow / RA / DEC / Alt / Az`, et meilleur rendu des cibles sous l'horizon.

### Corrige

- La connexion ASCOM echoue maintenant proprement si le driver se declare connecte mais ne fournit pas encore de snapshot exploitable.
- La deconnexion de monture en cours de route ne fait plus planter l'application.
- Le reticule de monture et les coordonnees associees se rafraichissent correctement sur la carte du ciel.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Compilation Python des modules modifies.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.4.exe`.

## AstroClocks v3.3.3 stable - 2026-05-10

### Ajoute

- Support ASCOM sur Windows pour choisir une monture, se connecter a elle et lire ses coordonnees depuis AstroClocks.
- Affichage d'un reticule `Telescope` sur la carte du ciel quand une monture ASCOM est connectee.
- Nouvelle ligne d'etat dediee a la monture sous la carte du ciel.
- Documentation du projet remise a niveau avec licence GPL v3, build Windows, lancement en environnement virtuel et dependances ASCOM.

### Ameliore

- Fenetre de parametres reorganisee en onglets `General`, `Sky` et `Mount`.
- Zone de statut sous la carte du ciel agrandie pour afficher plus proprement les informations de cible et de monture.
- Libelles de la carte du ciel mieux positionnes pres des bords pour eviter les coupures.
- Refactorisation interne de `app.py` en sous-modules dedies (`app_visibility`, `app_double_stars`, `app_skymap`, `app_object_search`) pour faciliter la maintenance.

### Corrige

- Le packaging Windows embarque maintenant correctement `pywin32`, `win32com`, `pythoncom` et `pywintypes` pour que le support ASCOM fonctionne aussi dans l'executable package.
- Le bouton de champ Aladin se met a jour immediatement apres modification du parametre correspondant.
- Divers ajustements d'interface dans la fenetre `A propos`, l'onglet `Mount` et la carte du ciel.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Compilation Python des modules modifies.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.3.exe`.

## AstroClocks v3.3.2 stable - 2026-05-09

### Ajoute

- Vérification des mises à jour GitHub depuis la fenêtre "À propos", avec téléchargement direct de l'installateur Windows quand une nouvelle stable est disponible.
- Vérification automatique et silencieuse des mises à jour au démarrage, avec ouverture de la fenêtre "À propos" seulement si une nouvelle version est détectée.

### Corrige

- L'installeur Windows supprime maintenant aussi `AstroClocks-v3.3.1.exe` lors d'une mise a jour vers `v3.3.2`.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.2.exe`.

## AstroClocks v3.3.1 stable - 2026-05-09

### Corrige

- L'installeur Windows supprime maintenant correctement `AstroClocks-v3.2.exe` et `AstroClocks-v3.3.exe` lors d'une mise a jour vers `v3.3.1`.

### Verification

- Regeneration du build Windows via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.1.exe`.

## AstroClocks v3.3 stable - 2026-05-08

### Ajoute

- Nouvel onglet "Ciel profond" pour rechercher des objets par type, magnitude apparente, visibilité nocturne et hauteur maximale.
- Recherche en ligne SIMBAD/CDS pour enrichir les résultats ciel profond, avec cache local et repli hors-ligne.
- Ajout du type "Rémanent de supernova" dans la recherche ciel profond.
- Magnitudes apparentes OpenNGC embarquées pour filtrer hors ligne les objets NGC/IC/Messier et les entrées d'addendum.
- Liste complémentaire de quasars brillants pour proposer le type "Quasar" dans la recherche.
- Sélection de la bande photométrique préférée (`V`, `U`, `B`, `G`, `R`, `I`, `Z`, `Y`, `J`, `H`, `K`) pour la recherche ciel profond, avec `V` par défaut.
- Nouvel onglet "Étoiles" pour rechercher des étoiles SIMBAD par type spectral, bande photométrique, magnitude, visibilité nocturne et hauteur maximale.
- Recherche hors-ligne des étoiles basée sur le catalogue local de la carte du ciel, enrichi avec les types spectraux du Bright Star Catalogue.
- Bouton "Vider le cache" dans les onglets étoiles doubles, ciel profond et étoiles.
- Préchargement des onglets de recherche, du catalogue d'étoiles de la carte du ciel et des ajustements de police avant l'affichage de la fenêtre principale.

### Corrige

- Correction de la recherche SIMBAD/CDS des nébuleuses obscures, qui échouait avec une erreur HTTP 400.

### Verification

- Suite de tests : `python -m unittest discover -s tests`.
- Build Windows v3.3 via `Build-Windows.ps1`.
- Artefact Windows distribue : `installer/Install_AstroClocks3.3.exe`.

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
