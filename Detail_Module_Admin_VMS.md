# Détail du Module Spécifique : Gestion des Utilisateurs et Administration

Ce document décrit le fonctionnement du module de gestion des accès et de configuration globale du système **VMS (Uwazy)**.

---

## 1. Hiérarchie des Utilisateurs (RBAC)

Le système implémente un contrôle d'accès basé sur les rôles (Role-Based Access Control) pour assurer la séparation des tâches.

### Les Profils d'Utilisateurs
1.  **Administrateur (Superutilisateur) :**
    *   Gestion complète des services, des portes et des utilisateurs.
    *   Accès aux logs d'audit et aux archives.
    *   Configuration des paramètres système.
2.  **Agent de Sécurité (Réceptionniste) :**
    *   Enregistre les arrivées (**Entrées**) à sa porte de poste.
    *   Enregistre les départs (**Sorties**) même si le visiteur est entré par une autre porte.
    *   Voit en temps réel qui est présent dans tout l'établissement.
    *   Ne peut pas supprimer de données importantes (sécurité des traces).

---

## 2. Affectation Dynamique aux Portes

L'innovation organisationnelle du système repose sur le lien entre un agent et un point d'accès physique.

*   **Mécanisme :** L'administrateur choisit à quelle porte l'agent travaille aujourd'hui.
*   **Impact Interface :** L'agent voit toutes les personnes présentes sur le site (peu importe par où elles sont entrées), ce qui lui permet de valider leur sortie s'ils passent par sa porte.
*   **Souplesse :** Le système permet désormais un flux "Entrée Porte A -> Sortie Porte B", ce qui est idéal pour les grands bâtiments.

---

## 3. Interface d'Administration (Back-Office)

Le système tire parti de l'interface d'administration native de Django, personnalisée pour les besoins du VMS.

### Fonctionnalités de Gestion
*   **Gestion des Services :** Création et modification des départements de l'institution.
*   **Gestion des Portes :** Ajout de nouveaux points d'accès.
*   **Audit Trail :** Visualisation centralisée de tous les `LogAction` pour détecter les comportements suspects ou les erreurs de saisie.

---

## 4. Sécurité des Comptes

*   **Gestion des Mots de Passe :** Utilisation de l'algorithme de hachage PBKDF2 (standard de sécurité élevé).
*   **Logs de Connexion :** Chaque tentative de connexion (réussie ou échouée) est tracée.
*   **Désactivation de Compte :** En cas de départ d'un agent, son compte peut être désactivé instantanément sans supprimer son historique d'actions (préservation de la trace d'audit).

---

## 5. Personnalisation et Maintenance

Le module d'administration permet également de maintenir la cohérence des données via :
*   **Les listes déroulantes :** Toutes les sélections (Services, Motifs de visite) sont pilotées par des tables gérées en admin.
*   **L'exportation :** Possibilité d'extraire des listes au format CSV/Excel pour des analyses externes approfondies.

---
*Ce module garantit que le système reste ordonné, sécurisé et adaptable à l'évolution de l'organisation.*
