# Changelog

## AstroClocks v3.4.6 stable - 2026-10-15

### Ajouté

- Recherche d’étoiles : ajout des catégories WR, D, C, S et L/T/Y ; inclusion
  des sous-naines sd/esd/usd dans leur classe respective en ligne et hors ligne.
- Classement spectral fondé sur le préfixe principal, avec prise en charge
  des types MS/SC, R/N et des spectres composites ; reclassement des données
  du cache existant à partir de leur type spectral.

### Corrigé

- Requêtes SIMBAD S et L/T/Y accélérées par présélection des préfixes et
  validation spectrale compacte, pour éviter les dépassements du délai de réponse.
- Requêtes SIMBAD transmises en POST pour prendre en charge les filtres longs.
- Barre de défilement des listes déroulantes harmonisée avec le thème sombre,
  y compris au survol et au clic.

### Vérification

- 250 tests automatisés réussis.
- Recherches SIMBAD S et L/T/Y vérifiées en ligne, en bandes V et K.
- Exécutable Windows contrôlé : démarrage, carte du ciel, catalogue d’étoiles,
  nouvelles catégories, barre de défilement sombre et fenêtre À propos 3.4.6.
- Exécutable et installateur Windows reconstruits ; cohérence de version et
  présence du moteur HTTPS natif Windows vérifiées.
- Manuel français PDF 3.4.6 régénéré et mise en page contrôlée.

## AstroClocks v3.4.5 stable - 2026-10-14

### Corrigé

- Validation HTTPS native Windows via `truststore` pour les recherches SIMBAD/CDS,
  VizieR/WDS, ORB6, CDS Sesame, la météo et les mises à jour. Les certificats
  intermédiaires manquants peuvent être récupérés par Windows, y compris dans
  les processus de recherche. La vérification SSL reste active et aucun
  certificat n'est installé par le logiciel.
- Dépendance `truststore` incluse dans le build Windows.

### Vérification

- 244 tests réussis, dont validation obligatoire des certificats et des noms
  de serveur, et propagation des erreurs SSL sans nouvelle tentative non vérifiée.
- Accès HTTPS SIMBAD et VizieR vérifiés ; accès SIMBAD également vérifié dans
  un processus séparé utilisant la validation native Windows.
- Certificats autosignés et noms de serveur incorrects refusés en test réseau.
- Exécutable et installateur Windows reconstruits ; présence du moteur
  `truststore._windows` dans l'exécutable et cohérence de release vérifiées.

## AstroClocks v3.4.4 stable - 2026-10-14

### Ajouté

- Informations de cible : magnitude et bande photométrique, type d’objet, source des données et liens vers WDS, SIMBAD/CDS, CDS Sesame et les éphémérides IMCCE/Miriade.
- Magnitude visuelle et distance à l’observateur récupérées dans la réponse IMCCE, sans requête supplémentaire.
- Estimation locale de magnitude V et distance pour le Soleil, la Lune et les planètes prises en charge, utilisable hors ligne et explicitement indiquée comme estimée.
- Barre de progression réelle du recalcul ORB6 dans la colonne des étoiles doubles.

### Amélioré

- Recalcul ORB6 et recherches d’étoiles/ciel profond isolés dans des processus pour préserver la fluidité des horloges et des changements d’onglet.
- Extraction vectorisée des coordonnées des catalogues et démarrage des processus en arrière-plan.
- Recherche rapide : espacement fixe des contrôles, espace disponible attribué aux résultats, sources de catalogues clarifiées.
- Absence de cible clairement signalée en rouge orangé ; coordonnées vides sous la forme --h --m --s et --° --' --". Symbole réseau dans l’indicateur de connexion.
- Enrichissement SIMBAD ciblé des objets OpenNGC correspondant aux filtres ; reprise des données disponibles et conservation de la provenance et du lien.
- Manuel d’utilisation français mis à jour.

### Corrigé

- Résultats SIMBAD sans coordonnées écartés sans faire échouer toute la recherche.
- Métadonnées de cible correctement transmises au clic sur la carte du ciel.
- Source SIMBAD conservée dans l’affichage des objets enrichis, et indicateurs de qualité photométrique actualisés lors de la fusion.
- Conversion inutile vers une année UTC future supprimée du modèle photométrique local, évitant l’avertissement ERFA au démarrage sur les installations anciennes.

### Vérification

- 240 tests unitaires et graphiques réussis.
- Vérification des services en ligne et des liens de catalogues.
- Build Windows et cohérence des artefacts validés ; manuel PDF de 14 pages actualisé et rendu contrôlé.
- Exécutable packagé contrôlé : démarrage, recherches Étoiles/Ciel profond, recalcul ORB6, changements d’onglet et informations locales de la Lune.

## AstroClocks v3.4.3 stable - 2026-10-12

### Ajouté

- Manuel d'utilisation en français, avec PDF navigable et fonctions ASCOM en dernière partie.
- Option d'affichage du temps sidéral de Greenwich, masqué par défaut pour agrandir la recherche rapide.
- Altitudes indicatives pour les 152 lieux connus, renseignées automatiquement à la sélection et toujours modifiables.

### Amélioré

- Calcul et préparation graphique de la carte du ciel dans un thread dédié, sans appels Tk, avec files bornées et rejet des résultats obsolètes.
- Rendu opaque de la carte préparé en arrière-plan pour réduire le coût de transfert vers l'interface.
- Nouvelle disposition : UTC sous le site, coordonnées Alpha/Delta, heures locale/sidérale locale, puis angle horaire et déclinaison plus grands et encadrés en jaune.
- Plus de place pour le site d'observation et taille réduite des horloges secondaires.
- Paramètres regroupés dans quatre onglets : Site et heure, Affichage, Réfraction et météo, Monture ASCOM.
- Paramètres avancés et graduations T1m repliables avec chevrons ; libellés clarifiés et altitude dans le site.
- Par défaut : grille équatoriale et objets du système solaire affichés, grille AltAz masquée. Les préférences déjà enregistrées sont conservées.

### Corrigé

- Restauration du thème de fenêtre différée après destruction d'un dialogue, pour éviter une réentrée Tk pouvant fermer l'application lors de l'application des paramètres ou d'un changement de langue.

### Vérification

- 198 tests unitaires et graphiques réussis : paramètres, valeurs par défaut, altitudes, disposition et préparation asynchrone de la carte.
- Build Windows et contrôles de cohérence via Build-Windows.ps1 et Verify-Release.ps1.
- Démarrage de l'exécutable packagé contrôlé ; manuel PDF de 14 pages rendu et vérifié.

## AstroClocks v3.4.2 stable - 2026-10-05

### Corrige

- L'installeur Windows decode correctement les accents francais des options de demarrage grace a l'encodage UTF-8 avec BOM du script Inno Setup.
- Le resultat du controle de connexion au premier demarrage est maintenant transmis a l'interface par une file de messages, afin d'eviter les appels Tk depuis le thread reseau avant le lancement de la boucle graphique.

### Ameliore

- Les fichiers sources et scripts de packaging portent des noms independants de la version, afin de fiabiliser les builds suivants. L'executable reste `AstroClockV3.exe` et l'installeur reste versionne.

## AstroClocks v3.4.1 stable - 2026-07-10

### Ajoute

- Journal runtime rotatif dans `%LOCALAPPDATA%\AstroClocks\logs\astroclocks.log`, avec possibilite de rediriger le dossier via `ASTROCLOCKS_LOG_DIR`.
- Prise en charge ASCOM de `DoesRefraction`, avec statut lisible et choix de la responsabilite de correction : automatique, AstroClocks ou driver/monture.
- Modeles de refraction Bennett 1982, Saemundsson 1986, ERFA/SOFA + Saemundsson et Hohenkerk–Sinclair a profil vertical moyen. Les deux derniers utilisent pression, temperature, humidite et longueur d’onde.
- Recherche de stations meteo avec humidite lorsqu’elle est disponible, cache de session horodate et actualisation explicite.

### Ameliore

- Les exceptions non gerees Python, threads et callbacks Tk laissent maintenant une trace exploitable pour le diagnostic.
- Les echecs de connexion et de polling ASCOM absorbés par l'interface sont journalises au lieu de disparaitre silencieusement.
- La couverture de tests cible maintenant aussi les bascules de contexte de site, le cache JNow des coordonnees et les cibles dynamiques du systeme solaire.
- Les recherches asynchrones `Etoiles`, `Ciel profond` et `Etoiles doubles` journalisent mieux leurs echecs critiques et sont couvertes sur l'application des resultats obsoletes ou valides.
- Le modele hybride utilise Saemundsson sous 15° puis ERFA/SOFA au-dessus, avec une transition lissée. La boite Parametres ajuste maintenant les champs utilisables au modele et a la responsabilite de refraction choisis.
- Les champs d’angle horaire et de déclinaison indiquent explicitement « apparent(e) » uniquement lorsqu’AstroClocks leur applique une correction locale de réfraction.
- La recherche de stations météo propose désormais un rayon jusqu’à 150 km (50 km par défaut), afin de couvrir les sites isolés comme l’Observatoire de Haute-Provence.
- La recherche affiche jusqu’à cinq stations météo les plus proches, au lieu de trois.
- Les résultats de stations déjà trouvés sont restaurés à la réouverture des paramètres, même si le rayon avait été modifié pour la recherche.

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
