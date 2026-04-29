# Détail du Module Spécifique : Archivage et Conformité

Ce document présente la stratégie de conservation des données et les mécanismes de "nettoyage sécurisé" mis en place dans le système **VMS (Uwazy)**.

---

## 1. Philosophie de l'Archivage

Dans un système de gestion des identités, la suppression de données est une opération délicate qui peut rompre la piste d'audit. Le VMS privilégie une approche de **"Suppression Logique"** plutôt que physique.

---

## 2. Le Mécanisme de "Soft-Delete"

Lorsqu'un visiteur ou un service n'est plus nécessaire dans les listes actives, le système utilise l'attribut `is_archived`.

*   **Qu'est-ce que l'archivage simple (Soft-Delete) ?** C'est comme ranger un dossier dans un carton au lieu de le jeter à la poubelle. Le dossier n'est plus sur le bureau (les listes actives), mais on peut toujours aller le chercher si besoin.
*   **Réversibilité :** Si on s'est trompé, l'administrateur peut "sortir le dossier du carton" et le remettre sur le bureau en un clic.

---

## 3. Le Coffre-fort JSON (Table Archive)

Pour les éléments devant être définitivement retirés des tables principales (pour alléger la base de données), le système utilise un mécanisme de sauvegarde structurée.

### Processus d'Archivage Définitif
1.  **Extraction :** Les données de l'objet (ID, Nom, Prénom, CNI, Stats) sont extraites.
2.  **Sérialisation :** Les données sont transformées en format JSON.
3.  **Stockage :** Une entrée est créée dans le modèle `Archive` contenant les données au format **JSON**. 
    *   *Qu'est-ce que le JSON ?* C'est un format de texte très simple que les ordinateurs adorent pour stocker des informations de manière organisée. C'est comme une fiche bristol numérique.
4.  **Suppression :** L'objet original est alors supprimé pour libérer de la place, mais sa "fiche bristol" reste dans le coffre-fort.

---

## 4. Piste d'Audit et Responsabilité

L'archivage est une action "sensible" soumise à un contrôle strict :
*   **Privilèges :** Seul l'administrateur peut archiver ou supprimer.
*   **Traçabilité :** Chaque archivage génère un log `ARCHIVAGE_VISITEUR` ou `ARCHIVAGE_SERVICE` détaillant le motif et l'acteur.
*   **Preuve :** Le modèle `Archive` conserve le lien avec l'administrateur (`ForeignKey` vers `User`), assurant une responsabilité à long terme.

---

## 5. Conformité et Rétention des Données

Ce module permet à l'organisation de respecter les politiques de rétention des données :
*   **Nettoyage Périodique :** Possibilité de vider les listes de visiteurs n'ayant pas circulé depuis plusieurs années tout en gardant une trace consolidée.
*   **Optimisation :** Maintien d'une base de données "légère" et performante pour les opérations quotidiennes de la sécurité.

---
*L'archivage intelligent garantit que la mémoire du système reste intacte sans compromettre sa vélocité.*
