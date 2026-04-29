# Détail du Module Spécifique : Sécurité et Traçabilité

La sécurité est le pilier central du système **VMS (Uwazy)**. Ce document explique les mécanismes mis en place pour garantir l'intégrité des données et l'auditabilité totale des actions.

---

## 1. Système de Logging (Piste d'Audit)

Chaque action critique effectuée sur la plateforme est enregistrée de manière indélébile dans le modèle `LogAction`.

### Données Capturées
*   **L'Acteur :** L'utilisateur (agent ou administrateur) ayant réalisé l'action.
*   **L'Action :** Type d'opération (Connexion, Création, Modification, Archivage, Consultation CNIB).
*   **L'Horodatage :** Date et heure précise à la seconde près.
*   **Les Détails :** Ce qui a été fait exactement (ex: "Le visiteur Jean est sorti par la Porte 2").

---

## 2. Protection des Données Sensibles (RGPD/Souveraineté)

Le système manipule des pièces d'identité (CNIB). Des mesures strictes sont appliquées :

*   **Stockage Privé :** Les scans CNI ne sont pas stockés dans le dossier public `media`. Ils utilisent un `FileSystemStorage` pointant vers un répertoire hors d'accès direct par URL (`PRIVATE_MEDIA_ROOT`).
*   **Accès Restreint :** Seul un utilisateur avec le statut **Superutilisateur** (Administrateur) peut visualiser les images des scans. Les agents de sécurité ne voient que les données textuelles extraites.
*   **Audit de Consultation :** Chaque clic sur "Voir le scan" génère un log spécifique `CONSULTATION_CNIB`, permettant de savoir qui a consulté quel document et quand.

---

## 3. Cloisonnement des Profils

La gestion des accès repose sur une hiérarchie claire :

| Rôle | Accès | Restrictions |
| :--- | :--- | :--- |
| **Administrateur** | Contrôle total (Logins, Archives, Statistiques de tout le site). | Aucune. |
| **Agent** | Accueil des visiteurs, enregistrement des départs. | Ne peut pas voir les photos des CNIB, ni modifier l'historique global. |

**Vérification de la Porte :** Pour travailler, un agent doit dire au système à quelle porte il se trouve. S'il n'est pas "posté" à une porte, il ne pourra pas enregistrer de nouvelles visites (car le système doit savoir par où le visiteur est entré).

---

## 4. Archivage et Réversibilité

Plutôt que la suppression pure et simple, le système utilise deux niveaux de retrait :
1.  **Soft-Delete (Is_archived) :** Le visiteur disparaît des listes actives mais reste en base pour l'historique.
2.  **Coffre-fort JSON :** Pour les suppressions définitives, les données essentielles sont exportées dans une table `Archive` au format JSON avant suppression de l'objet principal, garantissant une trace même après "destruction".

---

## 5. Sécurité Technique

*   **Validation des Fichiers :** Utilisation de `FileExtensionValidator` pour empêcher l'upload de scripts malveillants à la place des images.
*   **CSRF Protection :** Activation systématique sur tous les formulaires d'entrée de données.
*   **Déconnexion Automatique :** Gestion des sessions pour minimiser les risques en cas d'abandon de poste.

---
*L'objectif de ce module est de passer d'une "confiance aveugle" à une "confiance vérifiée" par la preuve numérique.*
