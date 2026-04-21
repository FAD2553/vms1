# Description Détaillée du Diagramme des Composants Logiciels (VMS)

Ce document fournit une explication approfondie des différents composants logiciels qui constituent le **Système de Gestion des Visiteurs (VMS)**. L'architecture est conçue pour être modulaire, sécurisée et optimisée pour un déploiement en réseau local (LAN).

---

## 1. Vue d'Ensemble des Composants

Le système repose sur une architecture multicouche où chaque composant a une responsabilité spécifique, de l'interaction utilisateur au stockage persistant des données.

### 1.1 Couche de Présentation (Interface Utilisateur)
C'est le point d'entrée pour les agents et les administrateurs.

*   **Templates HTML & Bootstrap 5 :** Fournissent une interface web moderne, responsive et intuitive. Bootstrap est utilisé pour garantir que l'application est utilisable sur différents terminaux (PC, tablettes).
*   **Composant Chart.js :** Utilisé exclusivement dans le tableau de bord (Dashboard) pour transformer les données brutes de visites en statistiques visuelles (graphiques de fréquentation, pics d'affluence).
*   **Scripts JavaScript / jQuery :** Gèrent l'interactivité côté client. Notamment crucial pour l'envoi asynchrone (AJAX) des photos de CNIB au serveur sans recharger la page, améliorant ainsi la fluidité du processus d'accueil.

### 1.2 Couche Application (Cœur Django)
Le framework Django sert de chef d'orchestre pour toute la logique métier.

*   **Sytème de Routage (URL Router) :** Dirige les requêtes HTTP entrantes vers les fonctions ou classes de vues appropriées en fonction de l'URL demandée.
*   **Vues (Logiciel Métier) :** Le cerveau du système. Elles reçoivent les données, appliquent les règles de gestion (ex: vérifier si un visiteur est déjà présent), appellent les modules spécialisés et retournent les réponses à l'utilisateur.
*   **Gestionnaire d'Accès (Auth) :** Composant critique qui gère l'authentification des utilisateurs, la gestion des sessions et le contrôle des permissions basé sur les rôles (Agent vs Administrateur).

### 1.3 Modules Spécialisés (Services Internes)
Ces modules étendent les capacités de Django pour des tâches spécifiques au projet.

*   **Module OCR (Pytesseract) :** Reçoit les images prétraitées et les transmet au moteur Tesseract. Il analyse ensuite le texte brut pour extraire les informations structurées (Nom, Prénom, Numéro CNIB).
*   **Générateur PDF (ReportLab / xhtml2pdf) :** Transforme les données de visites et de statistiques en documents PDF officiels pour les rapports administratifs.
*   **Module de Prétraitement (Pillow) :** Travaille sur les images avant l'OCR. Il ajuste le contraste, la luminosité et convertit l'image en niveaux de gris pour maximiser le taux de réussite de la reconnaissance de texte.

### 1.4 Services Système et Stockage
Composants de bas niveau nécessaires au fonctionnement des modules spécialisés.

*   **Moteur Tesseract OCR :** Le moteur de reconnaissance optique de caractères installé sur le serveur. Il est invoqué par le module Python pour effectuer le travail de reconnaissance intensif.
*   **Système de Fichiers (Private Media) :** Un stockage sécurisé hors de la racine web publique (`PRIVATE_MEDIA_ROOT`). Il conserve les scans originaux des CNIB. L'accès à ces fichiers est strictement contrôlé par Django pour protéger la vie privée des visiteurs.

### 1.5 Couche de Persistance
La fondation où toutes les données sont stockées de manière permanente.

*   **Django ORM (Object-Relational Mapper) :** Sert d'interface entre le code Python et la base de données. Il permet de manipuler les données comme des objets Python, garantissant la sécurité contre les injections SQL.
*   **Base de Données PostgreSQL 16 :** Système de gestion de base de données relationnelle puissant qui stocke les profils des visiteurs, l'historique des visites, les logs de sécurité et les configurations du système.

---

## 2. Interactions entre les Composants

Le diagramme des composants met en évidence les flux suivants :

1.  **L'utilisateur** interagit avec les **Templates HTML**.
2.  Les requêtes sont transmises au **Router** puis aux **Views**.
3.  Pour un scan, la **View** appelle le **Module OCR**, qui utilise à son tour le moteur **Tesseract**.
4.  Les résultats sont stockés dans la **Base de Données** via l'**ORM**.
5.  Les documents sont générés via le **Module PDF** et les fichiers sensibles sont écrits dans le **Stockage Privé**.

---

> [!TIP]
> Cette architecture modulaire permet de mettre à jour le moteur OCR ou d'ajouter de nouveaux types de base de données sans impacter l'interface utilisateur.
