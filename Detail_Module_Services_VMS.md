# Détail du Module Spécifique : Gestion des Services et Destinations

Ce document explique comment le système **VMS (Uwazy)** cartographie l'organisation interne de l'institution pour orienter les flux de visiteurs.

---

## 1. Modélisation de l'Organisation

Le module `Service` représente les différents bureaux ou départements de votre établissement.

*   **Qu'est-ce qu'un Service ?** C'est la destination du visiteur. Par exemple : "La Comptabilité", "Le Secrétariat" ou "Le Bureau du Directeur".
*   **Pourquoi est-ce important ?** Cela permet de savoir exactement où va le visiteur. Si un problème survient à la Comptabilité, on peut savoir tout de suite quels visiteurs y étaient à ce moment-là.

---

## 2. Intelligence Opérationnelle

Le module ne se contente pas de lister les services, il fournit des données analytiques pour chaque département :

### Statistiques par Service
*   **Volume de Visites :** Identification des services les plus sollicités sur une période donnée.
*   **Temps Moyen de Présence :** Calcul de la durée passée par les visiteurs dans chaque service, utile pour optimiser les processus d'accueil.
*   **Taux d'Occupation Temps Réel :** Savoir combien de visiteurs externes se trouvent actuellement dans un bureau spécifique.

---

## 3. Automatisation et UX

Pour accélérer la saisie par les agents de sécurité, le module intègre des mécanismes d'assistance :

*   **Service par Défaut :** Le système peut être configuré pour présélectionner automatiquement un service (ex: "Secrétariat" ou "Courrier") pour les flux standards.
*   **Filtres Intelligents :** Dans les tableaux de bord, les administrateurs peuvent filtrer l'historique complet pour un service donné en un clic.

---

## 4. Archivage des Services

Le système prévoit l'évolution de l'organisation. Si un service est supprimé ou renommé :
*   **Protection de l'Historique :** Le système empêche la suppression d'un service s'il possède des visites actives.
*   **Archivage JSON :** Lors de la suppression d'un service obsolète, ses métadonnées et ses statistiques globales sont sauvegardées dans la table `Archive` pour conserver une trace historique sans encombrer les listes actives.

---

## 5. Impact sur le Reporting

Le module `Service` est le critère de segmentation numéro 1 dans les rapports PDF. Il permet à la direction de :
1.  Justifier l'activité de chaque département auprès des autorités.
2.  Identifier les besoins en personnel d'accueil pour les services à forte affluence.
3.  Assurer une traçabilité précise en cas d'incident dans une zone spécifique.

---
*En structurant les destinations, ce module transforme un simple passage en une donnée stratégique pour la gestion de l'espace.*
