# Dictionnaire de Données : VMS - UWAZY

Ce dictionnaire répertorie toutes les tables et champs de la base de données **PostgreSQL** utilisés par le système de gestion des visiteurs.

---

## 1. Table : `core_visiteur` (Visiteurs)
Stocke les informations d'identité des visiteurs extraites par OCR ou saisies manuellement.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto-increment | Identifiant unique du visiteur. |
| `nom` | Char(50) | Not Null | Nom de famille. |
| `prenom` | Char(100) | Not Null | Prénoms. |
| `numero_cni` | Char(50) | Unique, Not Null | Numéro de la CNIB (Clé d'identification). |
| `date_naissance`| Date | Not Null | Date de naissance du visiteur. |
| `sexe` | Char(10) | Choice (M/F) | Sexe du visiteur. |
| `telephone` | Char(20) | Nullable | Numéro de téléphone. |
| `scan_cni_recto` | ImagePath | Private Storage | Chemin vers le scan recto (sécurisé). |
| `date_enreg` | DateTime | Auto_now_add | Date de création du profil. |
| `is_archived` | Boolean | Default False | Indique si le visiteur est archivé. |

---

## 2. Table : `core_visite` (Sessions de visite)
Journalise chaque entrée et sortie d'un visiteur.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto-increment | Identifiant de la session. |
| `visiteur_id` | ForeignKey | FK -> Visiteur | Référence au visiteur. |
| `service_id` | ForeignKey | FK -> Service | Service de destination. |
| `porte_entree_id` | ForeignKey | FK -> Porte | Porte par laquelle le visiteur est entré. |
| `porte_sortie_id` | ForeignKey | FK -> Porte | Porte par laquelle le visiteur est sorti (Nullable). |
| `agent_entree_id`| ForeignKey | FK -> User | Agent ayant validé l'entrée. |
| `agent_sortie_id`| ForeignKey | FK -> User | Agent ayant validé la sortie (Nullable). |
| `heure_entree` | DateTime | Default Now | Horodatage d'arrivée. |
| `heure_sortie` | DateTime | Nullable | Horodatage de départ. |
| `statut` | Char(15) | Choice (PRESENT/SORTI) | État actuel du visiteur. |
| `motif` | Char(255) | Not Null | Raison de la visite. |

---

## 3. Table : `core_porte` (Points d'accès)
Configuration des différents points d'entrée du bâtiment.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto-increment | Identifiant de la porte. |
| `numero` | Char(20) | Unique | Numéro ou identifiant de la porte. |
| `description` | Text | Nullable | Précisions sur la localisation. |

---

## 4. Table : `core_service` (Départements)
Liste des services internes pouvant recevoir des visiteurs.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto-increment | Identifiant du service. |
| `nom` | Char(100) | Unique | Nom du service administratif. |

---

## 5. Table : `core_logaction` (Journaux d'audit)
Traçabilité de toutes les actions sensibles effectuées par les administrateurs et agents.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto-increment | Identifiant du log. |
| `action` | Char(50) | Not Null | Type d'action (ex: CONNEXION, ARCHIVAGE). |
| `date_heure` | DateTime | Auto_now_add | Moment de l'action. |
| `details` | Text | Not Null | Description textuelle de l'action effectuée. |
| `admin_id` | ForeignKey | FK -> User | L'utilisateur responsable de l'action. |

---

## 6. Table : `core_agentprofile` (Profils utilisateurs)
Extension de la table `User` de Django pour les besoins métiers.

| Champ | Type | Contraintes | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | OneToOne | FK -> User | Lien vers le compte utilisateur Django. |
| `porte_id` | ForeignKey | FK -> Porte | Porte actuelle d'affectation de l'agent. |

---
*Ce dictionnaire est la référence pour tout développement SQL ou évolution du schéma de données.*
