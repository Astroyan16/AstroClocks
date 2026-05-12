# Roadmap AstroClocks

Cette feuille de route couvre la ligne de stabilisation entre `v3.3.3` et
`v3.3.9`, puis l'ouverture de `v3.4.0`.

## Strategie

- `v3.3.x` est reserve aux correctifs, a la robustesse, au packaging, aux
  tests et au polish UX.
- `v3.4.0` ouvre le cycle suivant avec du refactor structurel et des evolutions
  fonctionnelles plus visibles.
- `main` reste la branche stable publiee.
- `codex/v3.3-maintenance` peut servir aux correctifs de stabilisation.
- `codex/v3.4-next` peut servir aux chantiers plus larges prepares en avance.

## Principes de conduite

- Ne pas faire de changement "au cas ou" ou seulement parce qu'il semble
  techniquement interessant.
- Eviter les refactors larges tant qu'ils n'apportent pas un gain direct de
  maintenance ou la correction d'un probleme reel.
- Garder les releases `v3.3.x` petites, testables et faciles a valider
  manuellement.
- Ne pas modifier un comportement utilisateur etabli sans besoin d'usage clair.
- Pour la monture, privilegier l'affichage fiable et la robustesse avant toute
  evolution d'ergonomie plus ambitieuse.

## Vue d'ensemble

| Version | Axe principal | Resultat attendu |
| --- | --- | --- |
| `v3.3.4` | ASCOM et updater | Connexions plus fiables, erreurs mieux gerees |
| `v3.3.5` | Carte du ciel et settings | UX plus propre, meilleur rendu et statut |
| `v3.3.6` | Recherches et catalogues | Flux offline/online plus solides |
| `v3.3.7` | Packaging Windows | Build et installeur plus reproductibles |
| `v3.3.8` | Tests et diagnostics | Couverture critique et logs utiles |
| `v3.3.9` | Consolidation finale | Base stable avant `v3.4.0` |
| `v3.4.0` | Refactor coeur + monture | Architecture plus saine et flux monture enrichi |

## v3.3.4

### Objectif

Fiabiliser l'integration ASCOM et le mecanisme de mise a jour en ligne.

### Taches

- Mieux gerer les etats `driver non choisi`, `driver choisi`, `connexion en cours`,
  `connecte`, `coordonnees indisponibles`, `deconnecte`.
- Gerer proprement les deconnexions de monture et les erreurs de polling.
- Ajouter une logique de reconnexion manuelle sans redemarrage complet de l'app.
- Durcir l'updater en cas de release GitHub absente, asset manquant, timeout,
  repo inaccessible, JSON invalide ou version incoherente.
- Uniformiser les messages d'erreur affiches a l'utilisateur.

### Risques

- Variabilite des drivers ASCOM selon les montures.
- Etats transitoires difficiles a reproduire sans materiel.

### Critere de sortie

- Aucun crash connu sur les flux updater et ASCOM.
- Messages d'erreur lisibles dans tous les cas principaux.
- Tests unitaires complementaires sur les branches d'erreur critiques.

## v3.3.5

### Objectif

Polir l'experience visuelle de la carte du ciel et des parametres.

### Taches

- Finaliser la lisibilite des labels pres des bords de la carte.
- Verifier le rendu du reticule `Telescope` sur plusieurs tailles de fenetre.
- Stabiliser la zone de statut sous la carte du ciel.
- Polir l'onglet `Mount` de la fenetre de parametres.
- Corriger les derniers details de coherence visuelle entre `General`, `Sky` et
  `Mount`.

### Risques

- Regression sur le layout Tkinter selon la resolution ecran.

### Critere de sortie

- Carte lisible sur plusieurs tailles de fenetre.
- Aucun texte coupe connu dans les zones critiques.
- Onglets de parametres homogenes visuellement.

## v3.3.6

### Objectif

Rendre les recherches plus robustes, surtout dans les bascules offline/online.

### Taches

- Revisiter les flux de recherche objets, etoiles, ciel profond et etoiles
  doubles.
- Uniformiser les etats `offline`, `cache local`, `fallback local`,
  `enrichissement en ligne`.
- Revoir les messages de resultat et d'echec dans les onglets de recherche.
- Ajouter des tests de non-regression sur les filtres les plus sensibles.

### Risques

- Duplication actuelle entre onglets pouvant faire reapparaitre des divergences.

### Critere de sortie

- Flux de recherche coherents entre tous les onglets.
- Cas offline verifies et predictibles.
- Boutons et messages dans un etat correct pendant les recherches asynchrones.

## v3.3.7

### Objectif

Durcir la chaine de build Windows et l'installeur.

### Taches

- Revoir les dependances PyInstaller trop larges si necessaire.
- Verifier que le build embarque bien les composants critiques `pywin32`.
- Verifier les upgrades depuis `v3.2`, `v3.3`, `v3.3.1`, `v3.3.2`.
- Formaliser une checklist de release reproductible.
- Documenter les commandes de build et de verification.

### Risques

- Temps de build long.
- Variations de packaging selon la machine de build.

### Critere de sortie

- Build Windows reproductible.
- Installeur valide en upgrade sur les versions recentes.
- Checklist de release testee en vrai au moins une fois.

## v3.3.8

### Objectif

Augmenter la confiance avant la fin du cycle `3.3.x`.

### Taches

- Ajouter des tests sur la logique de cible, de coordonnees et de recherche.
- Ajouter des tests pour les parcours critiques updater et ASCOM.
- Introduire une journalisation simple pour les erreurs runtime importantes.
- Definir une petite liste de smoke tests manuels a executer avant chaque
  release.

### Risques

- Les parcours Tkinter sont plus difficiles a couvrir completement.

### Critere de sortie

- Couverture renforcee sur les scenarios les plus fragiles.
- Logs exploitables en cas de bug utilisateur.
- Procedure de verification stable avant release.

## v3.3.9

### Objectif

Faire une release de consolidation finale avant d'ouvrir `v3.4.0`.

### Taches

- Corriger uniquement les regressions et points restants detectes en `3.3.4`
  a `3.3.8`.
- Geler les changements structurels.
- Verifier la coherence de la doc, du changelog, de la version et des artefacts.

### Risques

- Glissement de perimetre si de nouvelles fonctions s'y glissent.

### Critere de sortie

- Release de stabilisation sans nouveaute majeure.
- Base saine pour ouvrir un cycle `v3.4.0`.

## v3.4.0

### Objectif

Ouvrir le cycle suivant avec une architecture plus saine et une experience
monture plus riche.

### Taches

- Extraire le bloc `target / coordinates / activation` hors de `app.py`.
- Decouper `app_dialogs.py` en sous-modules thematiques.
- Mutualiser les patterns repetes des onglets de recherche.
- Evaluer seulement si justifie d'usage l'option `utiliser la monture comme
  cible active`.
- Poser la base d'une liste d'observation locale, uniquement si cela ne fragilise
  pas le socle `3.3.x`.

### Risques

- Refactor transverse touchant plusieurs modules deja extraits.
- Regression fonctionnelle si les flux cible/monture ne restent pas coherents.
- Glissement de perimetre vers des fonctions nouvelles avant d'avoir termine la
  consolidation.

### Critere de sortie

- `app.py` recentre sur l'assemblage de l'application.
- Aucun comportement historique casse sur les flux cible, monture et recherche.
- Architecture prete pour des evolutions fonctionnelles plus ambitieuses.

## Demarrage recommande

Si l'on commence tout de suite, l'ordre le plus rationnel est :

1. lancer `v3.3.4` avec les correctifs updater et ASCOM ;
2. ajouter les tests de non-regression associes ;
3. publier une premiere maintenance rapide avant de toucher a plus de structure.
