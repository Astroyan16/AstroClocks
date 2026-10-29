# Manuel d’utilisation — AstroClocks 3.4.8

Version française • 29 octobre 2026 • Windows

Ce manuel décrit l’utilisation de la version 3.4.8. Les noms des boutons sont ceux de l’interface française. AstroClocks permet de préparer une observation, de suivre une cible et de commander une monture compatible ASCOM.

## Sommaire

1. [Installation et première utilisation](#1-installation-et-première-utilisation)
2. [Configurer le site d’observation](#2-configurer-le-site-dobservation)
3. [Lire les heures et les coordonnées](#3-lire-les-heures-et-les-coordonnées)
4. [Sélectionner une cible et utiliser la carte](#4-sélectionner-une-cible-et-utiliser-la-carte)
5. [Préparer une observation avec Visibilité](#5-préparer-une-observation-avec-visibilité)
6. [Rechercher dans les catalogues](#6-rechercher-dans-les-catalogues)
7. [Régler la réfraction atmosphérique](#7-régler-la-réfraction-atmosphérique)
8. [Récupérer les données météo](#8-récupérer-les-données-météo)
9. [Mises à jour et fonctionnement hors ligne](#9-mises-à-jour-et-fonctionnement-hors-ligne)
10. [Résoudre un problème](#10-résoudre-un-problème)
11. [Exemple de séance sans connexion ASCOM](#11-exemple-de-séance-sans-connexion-ascom)
12. [Fonctions optionnelles : monture ASCOM](#12-fonctions-optionnelles--monture-ascom)

## 1. Installation et première utilisation

Téléchargez l’installeur Windows depuis les [releases officielles](https://github.com/Astroyan16/AstroClocks/releases). Pour cette version, le fichier se nomme `Install_AstroClocks3.4.8.exe`.

Lancez l’installeur et suivez ses étapes. La création d’un raccourci sur le Bureau et le lancement au démarrage de Windows sont facultatifs. Une installation existante peut être mise à jour avec le nouvel installeur.

L’exécutable installé conserve le nom `AstroClockV3.exe`. L’utilisation de l’installeur ne nécessite pas d’installer Python séparément.

Au premier lancement :

1. Ouvrez **Paramètres** — **Settings** si l’interface est en anglais.
2. Dans **Affichage**, choisissez la langue ; dans **Site et heure**, renseignez le lieu.
3. Vérifiez le fuseau horaire et les graduations des cercles dans **Affichage**.
4. Cliquez sur **Appliquer** pour enregistrer les réglages.
5. Sélectionnez une cible depuis la carte ou une recherche.

**Appliquer** doit fermer seulement la fenêtre des paramètres. Le changement de langue est prévu pour prendre effet sans redémarrer le logiciel.

Les paramètres comportent quatre onglets : **Site et heure**, **Affichage**, **Réfraction et météo**, puis **Monture ASCOM**. Les sections avancées et les graduations T1m s’ouvrent en cliquant sur leur titre à chevron. Le bouton **Défaut** rétablit les valeurs par défaut ; **Appliquer** les enregistre.

## 2. Configurer le site d’observation

Dans **Paramètres → Site et heure**, choisissez un **Lieu connu** ou saisissez les informations de votre site.

| Réglage | Valeur à saisir |
|---|---|
| Nom du site | Un nom permettant d’identifier le lieu |
| Pays | Le pays du site |
| Latitude | Degrés décimaux : positive au nord, négative au sud |
| Longitude | Degrés décimaux : positive à l’est, négative à l’ouest |
| Altitude du site | Altitude au-dessus du niveau de la mer, en mètres |
| Fuseau horaire | Automatique ou défini manuellement |

Utilisez un point comme séparateur décimal, par exemple `48.805` et `2.23006`. La latitude doit être comprise entre −90° et +90°, la longitude entre −180° et +180°.

Le **Fuseau horaire automatique** utilise le fuseau de Windows. Si le lieu d’observation se trouve dans un autre fuseau que celui du PC, définissez-le explicitement. Le logiciel accepte notamment un nom IANA comme `Europe/Paris` ou un décalage comme `UTC+02:00`. Vérifiez également le réglage d’heure d’été lorsqu’il est proposé.

La précision du pointage dépend de la date, de l’heure et du site. Vérifiez donc l’horloge de Windows avant une observation.

Les 152 lieux connus renseignent automatiquement leur altitude. Cette valeur est indicative : vérifiez-la pour votre point d’observation précis et modifiez-la si nécessaire. Les estimations proviennent de [Copernicus DEM via Open-Meteo](https://open-meteo.com/en/docs/elevation-api), avec des valeurs publiées par les observatoires pour certains sites. Aucun appel réseau n’est nécessaire lors de la sélection.

### Options des cercles du T1m

Dans **Paramètres → Affichage → Graduation des cercles (T1m)**, les options **Angle horaire T1m (+6h cercle Est)** et **Déclinaison T1m (+90°)** adaptent l’affichage aux graduations de cet instrument. Elles sont activées par défaut.

Pour lire les valeurs astronomiques usuelles, désactivez ces options si votre instrument n’utilise pas ces graduations. Le suffixe du titre indique le décalage appliqué. Ces réglages d’affichage ne correspondent pas à une correction de réfraction.

## 3. Lire les heures et les coordonnées

L’onglet principal présente plusieurs informations complémentaires.

Sous le site d’observation se trouvent UTC et, si activé, le temps sidéral de Greenwich ; viennent ensuite Alpha/Delta, les temps local/sidéral local, puis les grandes valeurs de pointage encadrées en jaune. Le temps sidéral de Greenwich est masqué par défaut : la recherche rapide utilise alors cet espace. Activez **Afficher le temps sidéral de Greenwich** dans **Paramètres → Affichage** pour le faire apparaître.

| Affichage | Signification |
|---|---|
| Temps local | Heure civile dans le fuseau sélectionné |
| UTC | Temps universel coordonné |
| Temps sidéral de Greenwich | Temps sidéral au méridien de Greenwich |
| Temps sidéral local | Temps sidéral pour la longitude du site actif |
| Alpha ICRS/J2000 | Ascension droite de référence, en heures, minutes et secondes |
| Delta ICRS/J2000 | Déclinaison de référence, en degrés, minutes et secondes |
| Angle horaire | Valeur de pointage calculée pour l’heure et le site actifs |
| Déclinaison | Valeur de pointage, avec les corrections et décalages éventuellement actifs |

Les coordonnées **J2000** et **JNow** ne doivent pas être interchangées : elles utilisent des références temporelles différentes. Le repère déclaré par le driver ASCOM intervient dans la préparation des coordonnées envoyées à la monture.

Quand AstroClocks applique effectivement une correction locale de réfraction, les titres indiquent **Angle horaire (apparent)** et **Déclinaison (apparente)**. Un suffixe supplémentaire peut signaler les graduations T1m.

La carte et la courbe de visibilité utilisent les coordonnées de la cible pour décrire sa position dans le ciel. Les champs de pointage et la commande GoTo peuvent, eux, recevoir la correction atmosphérique choisie.

## 4. Sélectionner une cible et utiliser la carte

### Recherche par nom

Dans **Trouver les coordonnées d’un objet**, choisissez le type d’objet, saisissez son nom ou sa désignation et lancez la recherche. Les catégories comprennent les étoiles et objets du ciel profond ainsi que plusieurs types d’objets du système solaire.

Lisez le statut de recherche : il indique notamment les erreurs de service ou l’utilisation de données locales. Les objets du système solaire ont une position qui évolue avec le temps.

Le résultat présente la magnitude disponible, le type d’objet et la source des données. Les sources WDS, SIMBAD/CDS, CDS Sesame et IMCCE/Miriade sont cliquables : elles ouvrent le navigateur vers le catalogue, le formulaire ou les éphémérides de l’objet.

Pour le système solaire, la distance estimée à l’observateur est affichée en kilomètres pour la Lune et en unités astronomiques (UA) pour les autres astres. IMCCE fournit la magnitude visuelle lorsqu’elle est disponible. Hors ligne, le modèle local propose une magnitude V explicitement marquée « estimée » pour le Soleil, la Lune et les planètes prises en charge. Cette estimation simplifie les effets physiques : elle ne modélise ni les éclipses ni l’extinction atmosphérique et peut être indisponible hors du domaine des formules.

### Saisie de coordonnées

Les champs **Alpha ICRS/J2000 (h m s)** et **Delta ICRS/J2000 (d m s)** permettent de définir une cible manuellement. Renseignez les composantes, conservez le signe de la déclinaison et validez avec les boutons **Définir** correspondants. Vérifiez ensuite la cible et sa position sur la carte.

### Carte du ciel

La carte représente l’horizon local. Les directions cardinales et le zénith permettent de s’orienter. Le déplacement de la souris affiche des informations sur la position pointée ; un clic permet de définir une cible depuis la carte.

Le réticule **Cible** indique la cible active. Le réticule **Télescope**, lorsqu’il est activé et qu’une monture fournit ses coordonnées, indique la position de la monture. Sélectionner une cible ne déclenche pas à lui seul un mouvement du télescope.

Dans **Paramètres → Affichage**, vous pouvez régler :

- la magnitude limite de la carte, jusqu’à 6,2 ;
- l’affichage des grilles AltAz et équatoriale ;
- l’affichage des principaux objets du système solaire ;
- le champ de la vue Aladin.

Une magnitude limite plus élevée affiche des étoiles plus faibles. Cette limite concerne la carte, pas les limites des recherches dans les catalogues.

Par défaut, seule la grille équatoriale est affichée et les objets du système solaire sont visibles. La grille AltAz est masquée. Les préférences déjà enregistrées restent conservées après une mise à jour.

Le bouton **Aladin** ouvre une vue en ligne centrée sur la cible, avec le champ choisi. Une connexion Internet est nécessaire.

## 5. Préparer une observation avec Visibilité

Sélectionnez une cible puis ouvrez **Visibilité**. La courbe représente sa hauteur sur une période allant de midi à midi en temps local, afin de regrouper une nuit d’observation.

Les zones de fond distinguent le jour et les crépuscules civil, nautique et astronomique. Le maximum d’altitude et son heure facilitent le choix d’un créneau.

Utilisez **−24 h**, **+24 h** ou **Date…** pour consulter une autre nuit. Le survol de la courbe donne l’heure et la hauteur correspondantes. Le marqueur de l’heure actuelle n’apparaît que si cette heure appartient à la période affichée.

Une cible au-dessus de l’horizon calculé peut être masquée par un bâtiment, un arbre ou le relief du site : la courbe ne remplace pas la connaissance de votre horizon réel.

## 6. Rechercher dans les catalogues

Les onglets **Étoiles doubles**, **Ciel profond** et **Étoiles** permettent de filtrer des objets puis de sélectionner une cible.

La procédure générale est la suivante :

1. Renseignez les filtres.
2. Cliquez sur **Appliquer les filtres** pour exploiter les données disponibles.
3. Utilisez **Recherche en ligne** pour compléter les données si nécessaire.
4. Sélectionnez une ligne puis cliquez sur **Définir comme cible**.
5. Vérifiez la position dans l’onglet principal et la courbe de visibilité.

Dans **Étoiles** et **Ciel profond**, la recherche SIMBAD reçoit les objets par lots de 5 000 lignes, classées par magnitude croissante dans la bande choisie, puis par identifiant en cas d’égalité. Le statut indique si la recherche est incomplète ; utilisez **Charger les 5 000 suivants** pour poursuivre sans recommencer. Les filtres de visibilité s’appliquent ensuite : un lot peut donc ajouter moins de 5 000 objets affichés. Les objets locaux et les données déjà en cache restent également présents dans le tableau.

Les lots reçus et leur point de reprise sont conservés après fermeture. Une nouvelle **Recherche en ligne** recommence au premier lot ; modifier le type d’objet, la bande ou les limites de magnitude invalide la reprise précédente. **Vider le cache** supprime aussi ce point de reprise. Pour les objets sans filtre de magnitude, notamment les nébuleuses obscures, les lots sont ordonnés par identifiant.

### Étoiles doubles

Les filtres portent notamment sur les magnitudes des composantes, la séparation, la hauteur maximale, la visibilité nocturne et la nature de la paire. Des filtres avancés permettent d’affiner la sélection.

Les résultats distinguent les mesures **WDS** des valeurs calculées **ORB6**, lorsqu’une orbite est disponible. La séparation ρ est exprimée en secondes d’arc et l’angle de position θ en degrés. **Obs2** désigne l’année de dernière observation du catalogue ; ce n’est pas la date du calcul ORB6.

Vous pouvez consulter les notes WDS, recalculer les orbites disponibles et afficher leur représentation. Toutes les paires ne disposent pas d’une orbite calculable. Une barre indique la progression réelle du recalcul. Les calculs des orbites et les recherches d’étoiles ou de ciel profond sont isolés pour conserver une interface réactive.

### Ciel profond

Choisissez le type d’objet : galaxie, amas, nébuleuse ou autre catégorie proposée. Ajustez la bande de magnitude préférée, les limites de magnitude et les conditions de visibilité.

**Alt max** et **Alt nuit** distinguent la hauteur maximale et la hauteur maximale nocturne. Les magnitudes de bandes différentes ne sont pas directement équivalentes. Certaines entrées sans magnitude exploitable peuvent être écartées ; le statut de recherche le signale.

La recherche en ligne enrichit également les objets locaux correspondant aux filtres, sans dépendre uniquement des premiers résultats du serveur. Les valeurs SIMBAD disponibles sont reprises, et OpenNGC complète les informations absentes. La source conserve la mention SIMBAD et son lien.

### Étoiles

Choisissez un type spectral, une bande de magnitude et une plage de magnitudes. Les conditions de hauteur et de visibilité permettent d’adapter la liste à votre séance.

Les classes proposées sont O, B, A, F, G, K et M, ainsi que L/T/Y (classes L, T et Y regroupées), WR (Wolf-Rayet : WN, WC, WO et types apparentés), D (naines blanches), C (étoiles carbonées, y compris les anciennes classes R/N) et S (y compris MS et SC). Les sous-naines de préfixe sd, esd ou usd sont incluses dans leur classe spectrale respective : sdB dans B, sdO dans O, etc. Les spectres composites sont classés selon leur composante principale, placée en premier.

Les recherches en ligne utilisent SIMBAD/CDS. Les données enrichies peuvent être conservées en cache puis réutilisées hors ligne. Les commandes de vidage de cache suppriment ces données réutilisables.

## 7. Régler la réfraction atmosphérique

La réfraction atmosphérique modifie la direction apparente d’une cible, particulièrement près de l’horizon. Dans **Paramètres → Réfraction et météo**, choisissez un **Modèle de réfraction atmosphérique**.

| Modèle | Paramètres utilisés et comportement |
|---|---|
| Désactivée | Aucune correction locale de réfraction |
| Bennett 1982 | Pression, température et altitude du site |
| Saemundsson 1986 | Pression, température et altitude du site |
| ERFA/SOFA + Saemundsson 1986 | Prend aussi en compte humidité et longueur d’onde ; transition lissée entre les deux calculs autour de 15° de hauteur |
| Hohenkerk–Sinclair | Calcul avec un profil atmosphérique vertical moyen, incluant humidité et longueur d’onde |

Les champs utilisables dépendent du modèle et du responsable de correction choisis.

### Utilisation sans monture connectée

La réfraction peut corriger les valeurs d’angle horaire et de déclinaison affichées même sans connexion ASCOM. Choisissez un modèle actif et laissez **Correction de réfraction assurée par**, dans **Monture ASCOM → Paramètres avancés**, sur **Automatique (état ASCOM)** : sans monture connectée, AstroClocks effectue la correction locale.

Le choix **Forcer driver ASCOM / monture** désactive la correction locale. Les réglages spécifiques à une monture connectée sont détaillés dans la dernière partie du manuel.

### Renseigner les paramètres

**Pression au niveau de la mer** : saisissez une pression réduite au niveau de la mer, en hPa, telle que le QNH utilisé par les rapports METAR. La valeur `0` demande la valeur standard de 1013,25 hPa. AstroClocks estime ensuite la pression locale à partir de l’altitude du site. N’inscrivez pas une pression déjà corrigée pour l’altitude dans ce champ.

**Température** : température de l’air en °C. **Altitude du site**, dans **Site et heure** : altitude du lieu d’observation au-dessus du niveau de la mer, en mètres ; ce n’est pas la hauteur angulaire de la cible.

Dans les **Paramètres avancés** de **Réfraction et météo**, **Humidité relative** est une valeur en pourcentage et **Longueur d’onde** une valeur en nm, avec 550 nm par défaut pour le visuel. Ces deux paramètres interviennent dans les modèles qui les prennent en compte.

Après **Appliquer**, consultez les champs d’angle horaire et de déclinaison. Le suffixe « apparent(e) » signale une correction locale effective. La différence peut être faible pour une cible haute ou entre deux modèles proches. Les modèles moyens restent limités près de l’horizon, où l’atmosphère locale peut varier fortement.

## 8. Récupérer les données météo

Les données météo servent à renseigner les paramètres de réfraction. La recherche se fait autour des coordonnées saisies dans les paramètres du site.

1. Vérifiez latitude, longitude et altitude dans **Site et heure**.
2. Dans **Réfraction et météo**, activez un modèle puis choisissez le **Rayon de recherche** : 5, 10, 15, 20, 50, 100 ou 150 km. La valeur par défaut est 50 km.
3. Cliquez sur **Trouver les stations météo proches avec pression**.
4. Sélectionnez une station dans la liste : jusqu’à cinq résultats sont proposés avec leur distance, pression et horodatage.
5. Cliquez sur **Récupérer les données de la station**.
6. Vérifiez les valeurs remplies, ajustez-les si nécessaire puis cliquez sur **Appliquer**.

Seules les stations ayant une pression exploitable et suffisamment récente sont retenues. Il peut donc y avoir moins de cinq résultats. Si aucune observation n’est trouvée dans le rayon choisi, la recherche peut s’étendre à 150 km ; le message de statut indique cette extension.

La température et l’humidité sont récupérées lorsqu’elles sont disponibles. L’altitude du site reste celle de votre lieu d’observation. Une mesure de station distante ne représente pas nécessairement les conditions exactes au télescope.

### Configurer Météo-France

Les rapports METAR sont utilisés par défaut, sans clé API. Météo-France est un complément facultatif pour inclure davantage de stations. Dans **Paramètres → Réfraction et météo → Paramètres avancés**, cliquez sur **Configurer l’API Météo-France**, collez votre clé API autorisée pour **DPObs**, puis utilisez **Tester** et **Enregistrer**.

Sans clé, Météo-France apparaît comme **Non configuré** dans la liste des services en ligne ; aucun contrôle de ce service ni aucune alerte orange ne sont déclenchés.

Une clé pour les seules données climatologiques ne donne pas accès aux observations actuelles de DPObs. Le test distingue ce cas. Le dialogue permet aussi de supprimer la clé enregistrée.

La clé est stockée chiffrée pour l’utilisateur Windows courant. Sur un autre PC ou avec un autre compte, configurez-la à nouveau. Ne l’insérez pas dans un fichier destiné à être partagé avec votre manuel ou vos captures.

### Horodatage et cache

Regardez l’heure de mesure, pas seulement la pression. Le filtre de fraîcheur accepte des observations datant de six heures au maximum ; une observation acceptée n’est donc pas nécessairement celle des dernières minutes.

La liste Météo-France est mise en cache pendant une heure et les observations pendant cinq minutes. Les résultats de recherche sont également conservés en mémoire pendant la session. **Actualiser** permet de relancer la recherche ; les caches de données peuvent encore s’appliquer.

Ces caches et les limites de recherche réduisent les appels API. Pour votre abonnement limité à 100 requêtes par minute, évitez les tests et recherches répétés à quelques secondes d’intervalle. La récupération n’est pas une actualisation météo automatique permanente.

## 9. Mises à jour et fonctionnement hors ligne

La fenêtre **À propos** permet de vérifier les mises à jour GitHub et d’obtenir l’installeur correspondant. Une vérification automatique silencieuse est aussi effectuée au démarrage.

Sans Internet, les calculs locaux et les données déjà disponibles restent utilisables. Les recherches en ligne, Aladin, la récupération météo et les mises à jour dépendent du réseau. Les boutons et statuts indiquent les fonctions indisponibles ou l’utilisation du cache.

L’indicateur réseau est vert lorsque les services surveillés sont joignables, orange clair lorsque certains sont indisponibles et rouge lorsqu’aucune connexion Internet n’est détectée. Cliquez dessus pour consulter le détail par service. Le premier résultat est affiché dès la fin du contrôle au démarrage ; les vérifications suivantes sont effectuées toutes les 30 secondes et les pannes sont confirmées sur deux cycles. Le contrôle HTTPS ne valide pas les droits d’accès d’une clé API.

Les réglages sont conservés pour votre compte Windows dans `%APPDATA%\AstroClocks\AstroClocks.ini`.

## 10. Résoudre un problème

| Symptôme | Vérifications |
|---|---|
| Heure locale incorrecte | Heure Windows, fuseau du site et heure d’été |
| Angle horaire ou déclinaison décalés | Options T1m, site actif et réglages de réfraction |
| Réfraction sans effet visible | Modèle actif, responsable de correction, état ASCOM et hauteur de la cible |
| Peu de stations météo | Rayon, coordonnées, clé DPObs et disponibilité de pressions récentes |
| Clé API refusée | Autorisation pour DPObs, validité et copie complète de la clé |
| Pression différente d’un site météo | Station, heure de mesure, cache et type de pression comparés |
| Recherche indisponible | Connexion, service distant et données en cache |

En cas de fermeture inattendue, notez la version, l’action précise, les réglages concernés et l’heure du problème. Le journal se trouve à :

```text
%LOCALAPPDATA%\AstroClocks\logs\astroclocks.log
```

Collez ce chemin dans l’Explorateur Windows pour l’ouvrir. Le journal enregistre notamment les exceptions Python, les erreurs de callbacks de l’interface et certains incidents ASCOM. Une fermeture native peut ne pas laisser d’erreur dans ce fichier.

Si **Appliquer** ferme tout le logiciel lors d’un changement de langue, ce n’est pas le comportement attendu. Conservez le journal après reproduction pour le diagnostic.

## 11. Exemple de séance sans connexion ASCOM

1. Configurez le site et vérifiez l’heure du PC.
2. Désactivez les décalages T1m si votre instrument ne les utilise pas.
3. Recherchez un objet et définissez-le comme cible.
4. Consultez **Visibilité** pour choisir votre créneau.
5. Si vous souhaitez des valeurs de pointage corrigées de la réfraction, choisissez un modèle et récupérez les données météo.
6. Appliquez les réglages, vérifiez les valeurs de pointage et la position de la cible.
7. Utilisez ces valeurs avec les commandes habituelles de votre instrument, en tenant compte des graduations de ses cercles et d’une éventuelle correction déjà appliquée par son système de pointage.
8. En fin de séance, fermez AstroClocks.

## 12. Fonctions optionnelles : monture ASCOM

Cette partie concerne uniquement les utilisateurs souhaitant connecter et commander une monture depuis AstroClocks. Les fonctions présentées dans les parties précédentes sont utilisables sans cette connexion.

### Connecter la monture

La connexion nécessite la plateforme ASCOM et un driver compatible avec votre monture, installés sur Windows.

1. Ouvrez **Paramètres → Monture ASCOM**.
2. Cliquez sur **Choisir…** et sélectionnez le driver du télescope.
3. Configurez le driver selon votre matériel, puis cliquez sur **Connecter**.
4. Vérifiez le statut et les coordonnées retournées.
5. Activez **Afficher le réticule Télescope sur la carte du ciel** si souhaité.

### Source des coordonnées du site

Ouvrez **Paramètres avancés → Source du site d’observation** dans l’onglet **Monture ASCOM**.

**Paramètres AstroClocks** utilise le site saisi dans le logiciel. **Monture ASCOM** utilise les informations de localisation disponibles depuis la monture.

Ce choix concerne la base de site utilisée par l’application ; il ne sélectionne pas une nouvelle cible. Si la monture ne peut pas fournir le site, AstroClocks utilise ses paramètres de site en repli. Consultez le statut affiché pour connaître la source effective.

### Choisir le responsable de la réfraction

Le choix **Correction de réfraction assurée par** se trouve également dans les **Paramètres avancés** de **Monture ASCOM**.

- **Automatique (état ASCOM)** : avec une monture connectée, AstroClocks applique la correction locale seulement si le driver déclare explicitement `DoesRefraction = False`. Sans monture connectée, il peut corriger les valeurs affichées.
- **Forcer AstroClocks** : applique la correction locale du modèle sélectionné. À utiliser lorsque le driver ou la monture ne corrige pas déjà la réfraction.
- **Forcer driver ASCOM / monture** : confie cette correction au matériel ; les paramètres atmosphériques ne sont pas appliqués localement.

Si le driver ne renseigne pas son état de réfraction, le mode automatique ne suppose pas qu’il est désactivé. Vérifiez le comportement du driver avant de forcer une correction, pour éviter de la compter deux fois.

### Pointer et arrêter

Après avoir sélectionné une cible, utilisez **Pointer la cible** sous la carte. Cette commande nécessite une monture connectée et compatible GoTo. Une confirmation est demandée pour une cible sous l’horizon.

**Arrêter** demande au driver d’interrompre le mouvement. Vérifiez la réponse de votre matériel. Avant un GoTo, contrôlez les limites mécaniques, les obstacles et la configuration de la monture ; AstroClocks ne remplace pas les protections du driver.

Utilisez **Déconnecter** lorsque vous terminez la connexion ASCOM.

### Vérifications en cas de problème

Si ASCOM est indisponible, vérifiez la plateforme, le driver et la configuration de connexion. Si le pointage est impossible, vérifiez qu’une cible est active, que la monture est connectée et que le driver déclare une capacité GoTo.

