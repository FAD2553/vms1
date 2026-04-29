# Détail du Module Spécifique : Gestion du Stockage Sécurisé

Ce document décrit la stratégie de gestion des fichiers et la protection des documents d'identité au sein du système **VMS (Uwazy)**.

---

## 1. Dualité du Stockage (Public vs Privé)

Pour optimiser les performances tout en garantissant une sécurité maximale, le système sépare les ressources en deux catégories distinctes.

*   **Qu'est-ce que le stockage statique ?** Ce sont les éléments de décoration du site qui ne changent jamais (le logo, les couleurs, les boutons). Tout le monde peut les voir.

### 1.2 Stockage Privé (`/private_media/`)
*   **Qu'est-ce que le stockage privé ?** C'est le "coffre-fort" du système. On y cache les photos des cartes d'identité (CNIB).
*   **Sécurité :** Personne ne peut voir ces photos en tapant une adresse dans le navigateur. Il faut être un Administrateur connecté pour y avoir accès.

---

## 2. Le Workflow de Consultation Sécurisée

Lorsqu'un administrateur souhaite consulter un scan CNI, le processus suivant est déclenché :

1.  **Requête de l'Admin :** Clic sur "Voir le scan" dans l'interface.
2.  **Interception Django :** La vue `visiteur_cnib_view` vérifie immédiatement les droits (`request.user.is_superuser`).
3.  **Audit Flash :** Une ligne de log `CONSULTATION_CNIB` est injectée en base de données.
4.  **Streaming du Fichier :** Si autorisé, Django lit le fichier sur le disque et le renvoie comme une `HttpResponse` avec le `content_type` approprié.

---

## 3. Optimisation des Fichiers

Afin de ne pas saturer le serveur, le module de stockage applique des règles strictes :

*   **Validation de Taille :** Limitation à 5 Mo par scan via le `clean_method` du formulaire.
*   **Validation de Format :** Seuls les formats d'image standards (`.jpg`, `.jpeg`, `.png`) sont acceptés pour éviter l'exécution de scripts malveillants.
*   **Nommage Déterministe :** Les fichiers sont organisés dans des sous-dossiers horodatés pour faciliter les sauvegardes système.

---

## 4. Stratégie de Sauvegarde (Backup)

Le système est conçu pour faciliter les sauvegardes régulières par l'administrateur système :
*   **Base de Données :** Dump PostgreSQL régulier.
*   **Documents :** Synchronisation du dossier `private_media` vers un stockage externe sécurisé ou un NAS.

---

## 5. Intégrité et Souveraineté

En stockant les documents localement et de manière chiffrée (via les permissions système), le VMS garantit qu'aucune donnée d'identité ne transite par des serveurs tiers ou des solutions de Cloud public, respectant ainsi les directives nationales sur la protection des données personnelles.

---
*Ce module assure que le "registre numérique" est non seulement efficace, mais aussi inviolable.*
