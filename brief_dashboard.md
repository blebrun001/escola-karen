# Brief de cadrage — Dashboard de veille des offres enseignantes

## 1. Résumé du projet

Créer un rapport web public, hébergé gratuitement sur GitHub Pages, qui surveille
les offres de postes enseignants de difficile couverture publiées par cinq
services territoriaux de Catalogne.

Le dashboard doit être actualisé automatiquement chaque jour à 15 h 05, heure de
Paris, par une tâche GitHub Actions. Il remplace l'envoi quotidien par e-mail et
ne dépend pas d'un ordinateur personnel allumé.

## 2. Objectif principal

Permettre à l'utilisateur de répondre rapidement à deux questions :

1. Y a-t-il aujourd'hui une offre correspondant aux spécialités `GE` ou `CLA` ?
2. Quelle est la situation générale des offres publiées dans chaque territoire ?

Le dashboard doit privilégier la détection immédiate des offres intéressantes,
puis fournir une vue d'ensemble compréhensible sans devoir ouvrir chaque PDF.

## 3. Utilisateur cible

Une personne en recherche d'emploi comme professeur en Catalogne, qui consulte
le rapport une fois par jour depuis un ordinateur ou un téléphone.

L'utilisateur connaît les codes de spécialité, mais ne doit pas avoir besoin de
comprendre le fonctionnement de GitHub, du scraping ou de l'analyse des PDF.

## 4. Territoires surveillés

- Tarragona
- Penedès
- Baix Llobregat
- Barcelonès
- Terres de l'Ebre

Sources :

- [Tarragona](https://educacio.gencat.cat/ca/departament/serveis-territorials/tarragona/personal-docent/nomenaments-telematics/dificil-cobertura/secundaria/)
- [Penedès](https://educacio.gencat.cat/ca/departament/serveis-territorials/penedes/personal-docent/nomenaments-telematics/dificil-cobertura/secundaria/)
- [Baix Llobregat](https://educacio.gencat.cat/ca/departament/serveis-territorials/baix-llobregat/personal-docent/nomenaments-telematics/dificil-cobertura/secundaria/)
- [Barcelonès](https://educacio.gencat.cat/ca/departament/serveis-territorials/barcelones/personal-docent/nomenaments-telematics/dificil-cobertura/secundaria/)
- [Terres de l'Ebre](https://educacio.gencat.cat/ca/departament/serveis-territorials/terres-ebre/personal-docent/nomenaments-telematics/dificil-cobertura/secundaria/)

## 5. Critères de veille prioritaires

Une offre est considérée comme intéressante lorsque son champ `Especialitat`
correspond exactement à l'un des codes suivants :

- `GE`
- `CLA`

La comparaison doit être insensible à la casse et ignorer les espaces inutiles,
mais ne doit pas considérer un code seulement partiellement similaire comme une
correspondance.

## 6. Contenu attendu du dashboard

### 6.1 En-tête

L'en-tête doit afficher :

- le titre « Veille des offres enseignantes » ;
- la date et l'heure de la dernière vérification ;
- l'état global de la collecte : à jour, partielle ou en erreur ;
- un lien vers la dernière exécution GitHub Actions, si pertinent.

### 6.2 Alerte prioritaire GE/CLA

Cette zone est l'information la plus importante de la page.

Si des offres sont trouvées :

- afficher clairement le nombre d'offres `GE` et `CLA` ;
- distinguer les deux spécialités ;
- indiquer le territoire, l'établissement, la commune, le nombre de postes et
  l'identifiant de l'offre lorsque ces données sont disponibles ;
- fournir un lien direct vers le PDF source.

Si aucune offre n'est trouvée :

- afficher « Aucune offre GE ou CLA détectée lors de la dernière vérification » ;
- ne pas présenter l'absence d'offre comme une erreur.

La couleur ne doit pas être le seul moyen de distinguer ces deux états. Une
icône et un texte explicite doivent également être utilisés.

### 6.3 Vue d'ensemble

Afficher une synthèse globale comprenant :

- le nombre total d'annonces détectées ;
- le volume total de postes lorsque cette donnée est disponible ;
- le nombre de territoires ayant publié au moins une offre ;
- le nombre de documents nouveaux, actualisés ou inchangés ;
- les trois spécialités les plus représentées sur l'ensemble des territoires.

Il faut distinguer :

- une **annonce**, c'est-à-dire une ligne ou une fiche publiée ;
- un **poste**, dont le volume peut être `0,5`, `1`, `2`, etc.

### 6.4 Résumé par territoire

Chaque territoire dispose d'une carte ou d'une section contenant :

- le nombre d'annonces ;
- le volume de postes, ou « non précisé » ;
- les trois spécialités dominantes ;
- la répartition complète des spécialités ;
- le nombre d'offres `GE` et `CLA` ;
- l'état des PDF : nouveau, actualisé ou inchangé ;
- les avertissements d'extraction éventuels ;
- les liens vers la page officielle et les PDF analysés.

Exemple de résumé :

> Tarragona — 24 annonces, 23 postes. Spécialités dominantes : PSI (7),
> UES (5), ALS (2). Aucune offre GE ou CLA.

### 6.5 Détail des offres

Un tableau doit permettre de consulter les offres extraites avec les colonnes
suivantes, lorsqu'elles sont disponibles :

- territoire ;
- spécialité ;
- identifiant ;
- établissement ;
- commune ;
- nombre de postes ou quotité ;
- date limite de candidature ;
- état du document ;
- lien vers le PDF.

Fonctions souhaitées :

- filtre par territoire ;
- filtre par spécialité ;
- filtre « GE et CLA uniquement » ;
- recherche textuelle ;
- tri par territoire, spécialité ou date ;
- affichage utilisable sur mobile.

Les fonctions de filtrage doivent être réalisées côté navigateur, sans serveur
applicatif ni base de données distante.

### 6.6 Historique

Conserver un historique quotidien permettant de consulter :

- la date de chaque analyse ;
- le nombre d'annonces et de postes ;
- les offres `GE` ou `CLA` détectées ce jour-là ;
- les changements par rapport au rapport précédent.

Pour une première version, l'historique peut être limité aux 90 derniers jours.
Les données plus anciennes pourront rester archivées sous forme de fichiers
JSON sans être toutes chargées au démarrage de la page.

## 7. Hiérarchie recommandée de la page

```text
En-tête et dernière mise à jour
└── État global de la collecte

Alerte GE / CLA
└── Offres prioritaires ou confirmation d'absence

Indicateurs généraux
├── Total des annonces
├── Volume de postes
├── Territoires actifs
└── Documents nouveaux ou actualisés

Résumé par territoire
├── Tarragona
├── Penedès
├── Baix Llobregat
├── Barcelonès
└── Terres de l'Ebre

Tableau détaillé et filtres

Historique

Sources, méthode et avertissements
```

## 8. États à prévoir

### État normal

Toutes les pages et tous les PDF ont été analysés correctement.

### Aucune offre

La source est accessible, mais elle ne contient aucune annonce structurée. Cet
état doit être distingué d'un échec d'analyse.

### Données partielles

Un ou plusieurs territoires ont pu être analysés, mais une source ou un PDF a
échoué. Le dashboard doit afficher les résultats disponibles et identifier
clairement la source concernée.

### Erreur complète

Aucune source n'a pu être analysée. Le dernier rapport valide doit rester
consultable, accompagné d'un message indiquant la date de l'échec.

### Première exécution

Aucun historique n'existe encore. La page doit expliquer que les tendances et
comparaisons apparaîtront après plusieurs collectes.

### Rapport ancien

Si la dernière mise à jour date de plus de 26 heures, afficher un avertissement
« Rapport potentiellement obsolète ».

## 9. Principes d'interface

- Mobile first : la consultation quotidienne doit être confortable sur téléphone.
- Information prioritaire visible sans défilement excessif.
- Vocabulaire métier simple : offre, spécialité, territoire, établissement.
- Pas de jargon technique dans l'interface principale.
- Contraste suffisant et navigation utilisable au clavier.
- Aucun résultat ne doit dépendre uniquement d'une couleur.
- Les dates doivent être affichées au format français `JJ/MM/AAAA`.
- Les codes de spécialité doivent conserver leur graphie officielle.
- Les liens externes doivent être clairement identifiés.
- Les tableaux larges doivent devenir des cartes ou rester horizontalement
  navigables sur petit écran.

## 10. Architecture technique proposée

### Hébergement

- GitHub Pages ;
- dépôt public pour rester compatible avec GitHub Free ;
- site statique HTML, CSS et JavaScript ;
- aucune authentification dans la première version.

Le rapport et son historique seront publics. Aucune donnée personnelle ni aucun
secret ne doit être publié dans le dépôt ou dans les fichiers générés.

### Collecte et génération

Un script Python doit :

1. charger la configuration des cinq territoires ;
2. récupérer les pages officielles ;
3. détecter les PDF d'offres ;
4. comparer leur empreinte avec les documents déjà analysés ;
5. extraire leur texte ;
6. structurer les annonces et les spécialités ;
7. produire les statistiques ;
8. générer les fichiers JSON et le site statique ;
9. conserver l'historique ;
10. signaler les erreurs sans supprimer le dernier rapport valide.

### Automatisation GitHub Actions

Le workflow doit être exécutable :

- automatiquement chaque jour à 15 h 05, heure de Paris ;
- manuellement avec `workflow_dispatch` ;
- lors d'une modification du code, afin de tester le déploiement.

Configuration indicative :

```yaml
on:
  schedule:
    - cron: "5 15 * * *"
      timezone: "Europe/Paris"
  workflow_dispatch:
```

Une légère variation de l'heure réelle d'exécution est acceptable, car les
tâches GitHub Actions peuvent démarrer avec quelques minutes de retard.

### Déploiement

Le workflow doit :

1. installer Python et les outils d'extraction PDF nécessaires ;
2. exécuter les tests ;
3. lancer la collecte ;
4. générer le site dans un dossier dédié ;
5. publier l'artefact avec les actions officielles GitHub Pages ;
6. échouer visiblement si la génération du site est impossible.

## 11. Données à conserver

Le format exact reste à définir, mais chaque rapport quotidien doit au minimum
contenir :

```json
{
  "generated_at": "2026-07-16T15:05:00+02:00",
  "status": "success",
  "regions": [
    {
      "name": "Tarragona",
      "page_url": "https://...",
      "offers_count": 24,
      "vacancies_total": 23,
      "specialties": {
        "PSI": 7,
        "UES": 5
      },
      "interesting_offers": [],
      "documents": [],
      "warnings": []
    }
  ]
}
```

Les empreintes SHA-256 des PDF doivent être conservées afin de distinguer un
document nouveau, actualisé ou inchangé, même lorsque son URL ne change pas.

## 12. Périmètre de la première version

### Inclus

- surveillance des cinq territoires ;
- extraction des PDF ;
- détection exacte de `GE` et `CLA` ;
- statistiques générales et par territoire ;
- page responsive ;
- liens vers les sources ;
- historique quotidien ;
- publication automatique à 15 h 05 ;
- déclenchement manuel ;
- affichage des erreurs et données partielles.

### Hors périmètre initial

- envoi d'e-mails ou de notifications ;
- authentification et espace privé ;
- candidature automatique ;
- analyse de territoires supplémentaires ;
- intelligence artificielle externe ou API payante ;
- modification des critères depuis le dashboard ;
- application mobile native.

## 13. Critères d'acceptation

La première version est considérée comme fonctionnelle si :

1. le site est accessible depuis une URL GitHub Pages ;
2. le workflow s'exécute quotidiennement à l'heure prévue ;
3. les cinq territoires apparaissent dans le rapport ;
4. les offres `GE` et `CLA` sont mises en évidence sans faux positif évident ;
5. le nombre d'annonces et les spécialités dominantes sont visibles par territoire ;
6. chaque résultat permet de revenir au PDF officiel ;
7. une source défaillante ne masque pas les résultats des autres territoires ;
8. la dernière date de mise à jour est toujours visible ;
9. le dashboard reste lisible sur un écran mobile de 320 px de large ;
10. aucun mot de passe, jeton ou secret n'est présent dans les fichiers publiés.

## 14. Points de vigilance

- Les structures des pages et PDF peuvent changer sans préavis.
- Certains PDF peuvent être vides, scannés ou difficiles à extraire.
- Une URL de PDF peut rester identique alors que son contenu est remplacé.
- « Zéro offre » ne doit pas être confondu avec « extraction impossible ».
- GitHub Actions peut exécuter une tâche planifiée avec quelques minutes de retard.
- Les workflows planifiés d'un dépôt public inactif peuvent être désactivés par
  GitHub après une longue période sans activité.
- Le site et son historique sont publics avec l'option gratuite retenue.

## 15. Évolutions possibles

- notification facultative uniquement lorsqu'une offre `GE` ou `CLA` apparaît ;
- ajout d'autres territoires ou niveaux d'enseignement ;
- graphiques d'évolution des spécialités ;
- comparaison avec la veille ;
- export CSV ;
- flux RSS ;
- filtre par commune ou établissement ;
- domaine personnalisé ;
- version multilingue français/catalan.

## 16. Décision proposée

Adopter GitHub Pages comme canal principal de consultation et GitHub Actions
comme moteur d'exécution quotidienne. La première version doit rester entièrement
statique, gratuite, publique et centrée sur la détection fiable des spécialités
`GE` et `CLA`, avec une synthèse générale des offres.
