# Détail du Module Spécifique : Gestion des Flux (Entrées/Sorties)

Ce document détaille le fonctionnement du moteur de suivi des mouvements au sein du système **VMS (Uwazy)**, permettant une traçabilité en temps réel des visiteurs.

---

## 1. Concept de "Visite" et Cycle de Vie

Contrairement à une simple base de données de contacts, le système repose sur l'entité **Visite**, qui lie un visiteur à un service et une porte pour une durée déterminée.

### États d'une Visite
1.  **PRESENT (Sur place) :** Le visiteur est entré dans l'établissement. Il est enregistré avec sa **porte d'entrée**.
2.  **SORTI (Libéré) :** Le visiteur a quitté l'établissement. Sa **porte de sortie** et l'heure exacte sont enregistrées.

---

## 2. Architecture Multi-Portes

Le système est conçu pour des sites complexes possédant plusieurs points d'accès.

*   **Modèle Porte :** Chaque point d'entrée/sortie est référencé avec un numéro unique.
*   **Affectation des Agents :** Chaque agent de sécurité est "posté" à une porte spécifique.
*   **Visibilité Étendue :** Un agent voit sur son tableau de bord **tous les visiteurs actuellement présents** dans l'établissement, peu importe leur porte d'entrée. Cela lui permet d'enregistrer leur départ s'ils se présentent à son poste.
*   **Historique Local :** En plus des présents, l'agent voit l'historique complet des mouvements (entrées et sorties) ayant eu lieu à sa porte.

---

## 3. Logique de Contrôle d'Accès

Le module implémente des règles métier pour garantir l'intégrité des données :

### Prévention des Doublons
Avant de créer une nouvelle visite, le système vérifie si le visiteur n'est pas déjà marqué comme "PRESENT". Si c'est le cas, l'agent est alerté et redirigé vers la fiche de visite active au lieu d'en créer une nouvelle.

### Calcul de la Durée
Le modèle `Visite` utilise des propriétés Python (`@property`) pour calculer dynamiquement :
*   **La durée de séjour :** Différence entre `heure_sortie` (ou `now`) et `heure_entree`.
*   **Alerte de Séjour Prolongé :** Un indicateur visuel s'active si un visiteur dépasse un seuil (ex: 5 heures), signalant une anomalie potentielle à la sécurité.

---

## 4. Intégration Technique

La gestion des flux est orchestrée par les vues Django et le moteur de base de données.

# Extrait de la logique de sortie (simplifiée)
def visite_sortie(request, pk):
    # On récupère la visite en cours
    visite = get_object_or_404(Visite, pk=pk, statut='PRESENT')
    
    # L'agent enregistre la sortie à SA porte actuelle
    visite.porte_sortie = request.user.profile.porte_actuelle
    visite.heure_sortie = timezone.now()
    visite.statut = 'SORTI'
    visite.agent_sortie = request.user
    visite.save()
    
    # On garde une trace (Log) de qui a fait sortir le visiteur
    log_action(request.user, 'SORTIE_VISITE', f"Sortie de {visite.visiteur}", visite.id)

---

## 5. Bénéfices Opérationnels

*   **Comptage Instantané :** Connaissance exacte du nombre de personnes présentes sur le site en cas d'évacuation d'urgence.
*   **Analyse des Goulots d'Étranglement :** Identification des services les plus sollicités et des temps d'attente moyens.
*   **Responsabilisation :** Chaque entrée/sortie est signée numériquement par l'agent en poste.

---
*Ce module transforme une simple liste d'invités en un véritable outil de pilotage de la sécurité périmétrique.*
