# Plan d'implémentation : Mises à jour en temps réel sans rechargement

Ce plan décrit les modifications à apporter pour que le tableau de bord et la galerie de captures caméra se mettent à jour automatiquement et en temps réel, avec des animations fluides de transition.

## Approche Technique

Pour éviter d'ajouter des dépendances lourdes (comme WebSockets avec Django Channels et Redis), nous utiliserons un mécanisme de **Polling AJAX optimisé**. Le client interrogera le serveur toutes les 4 secondes pour obtenir les nouvelles données au format JSON.

### Optimisations et Expérience Premium
*   **Mises à jour intelligentes du DOM** : Les listes de visiteurs et les grilles de captures ne seront pas reconstruites à zéro. Nous comparerons les identifiants pour ajouter les nouveaux éléments (fade-in), supprimer les éléments disparus (fade-out), et conserver les éléments inchangés.
*   **Animations d'incrémentation (Count-Up)** : Les compteurs de statistiques s'animeront de manière fluide d'une valeur à une autre.
*   **Mise à jour des graphiques en direct** : Les instances Chart.js existantes recevront les nouvelles données et s'animeront dynamiquement sans clignotement.

---

## Modifications Proposées

### 1. Backend (Django)

#### [MODIFY] [views.py](file:///c:/Users/ousmanek/Desktop/STAGE/vms1/core/views.py)

*   **Vue `dashboard`** :
    *   Si `request.GET.get('format') == 'json'` est détecté, sérialiser et renvoyer les statistiques, les listes `visites_sur_place` et `recent_visites`, ainsi que les données des graphiques dans un `JsonResponse`.
*   **Vue `captures_camera_view`** :
    *   Si `request.GET.get('format') == 'json'` est détecté, sérialiser et renvoyer la liste des fichiers de la page courante, ainsi que les informations de pagination (`total_count`, `has_next`, `has_previous`, etc.).

---

### 2. Frontend (HTML / JS)

#### [MODIFY] [dashboard.html](file:///c:/Users/ousmanek/Desktop/STAGE/vms1/templates/core/dashboard.html)

*   **Variables globales** : Conserver les instances `visitChart` et `serviceTrafficChart`.
*   **Polling de mise à jour** :
    *   Ajouter un `setInterval` toutes les 4 secondes.
    *   Effectuer un `fetch` sur `/?format=json`.
    *   Mettre à jour les indicateurs numériques avec une fonction d'animation de compteurs (`animateCount`).
    *   Faire une comparaison (diffing) des lignes de tableau pour ajouter/supprimer dynamiquement avec une transition CSS d'opacité et de transformation.
    *   Mettre à jour les données des graphiques et appeler `.update()` sur les instances Chart.js existantes.

#### [MODIFY] [captures_camera.html](file:///c:/Users/ousmanek/Desktop/STAGE/vms1/templates/core/captures_camera.html)

*   **Polling de mise à jour** :
    *   Ajouter un `setInterval` toutes les 4 secondes.
    *   Effectuer un `fetch` sur l'URL courante de la galerie en lui ajoutant `&format=json` pour respecter les filtres de recherche et la pagination courante.
    *   Mettre à jour dynamiquement la grille d'images (ajout progressif des nouvelles photos et suppression des anciennes).
    *   Mettre à jour la section de pagination.

---

## Plan de Vérification

### Tests Manuels
1.  **Vérification Dashboard** :
    *   Ouvrir le tableau de bord sur un navigateur.
    *   Dans un autre navigateur (ou via l'OCR/Scan), enregistrer une nouvelle entrée de visiteur.
    *   Vérifier que le compteur de visites et les tableaux se mettent à jour automatiquement sur le premier navigateur sous 4 secondes avec des animations fluides.
2.  **Vérification Galerie de Captures** :
    *   Ouvrir la galerie pour l'utilisateur `admin_secours`.
    *   Uploader ou générer une nouvelle image de test dans `media/captures_camera/`.
    *   Vérifier que l'image s'ajoute automatiquement à la grille.
