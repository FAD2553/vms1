# Détail du Module Spécifique : Statistiques et Reporting

Ce document décrit comment le système **VMS (Uwazy)** transforme les données brutes d'entrées/sorties en indicateurs décisionnels pour la direction.

---

## 1. Le Dashboard Interactif

Le tableau de bord utilise **Chart.js** pour offrir une visualisation dynamique et temps réel de l'activité du site.

### Indicateurs Clés (KPIs)
*   **Taux d'occupation :** C'est le nombre de personnes qui sont "sur place" en ce moment même. Si 50 personnes entrent et 30 sortent, le taux d'occupation est de 20.
*   **Activité par Porte :** Suivi séparé des **Entrées** et des **Sorties** pour chaque poste de garde. Cela permet de savoir quelles portes sont les plus utilisées pour entrer ou pour quitter le bâtiment.
*   **Top Services :** C'est le classement des bureaux les plus visités (ex: la Comptabilité reçoit plus de monde que les RH).

---

## 2. Analyses Temporelles

Le module traite les données selon plusieurs échelles de temps pour identifier les tendances :

*   **Analyse Horaire :** Graphique en barres montrant les pics d'affluence durant la journée (ex: forte affluence entre 10h et 11h).
*   **Analyse Hebdomadaire :** Suivi sur les 7 derniers jours pour identifier les jours de la semaine les plus chargés.
*   **Analyse Mensuelle/Annuelle :** Historique long terme pour les rapports d'activité globaux.

---

## 3. Moteur de Reporting PDF

Pour les besoins administratifs et de conformité, le système intègre un générateur de rapports professionnels basé sur la bibliothèque **xhtml2pdf**.

### Fonctionnement du Générateur
1.  **Filtrage Multi-Critères :** L'utilisateur sélectionne une plage de dates, un service, une porte ou même un agent spécifique.
2.  **Conversion HTML vers PDF :** Une template CSS dédiée (optimisée pour l'impression) est remplie avec les données filtrées.
3.  **Export Propre :** Un document PDF est généré. Il contient désormais le détail précis du trajet du visiteur : par quelle porte il est arrivé et par laquelle il est reparti.

---

## 4. Intelligence par Service

Chaque fiche de service possède son propre mini-dashboard permettant de :
*   Connaître le nombre de visiteurs reçus par mois.
*   Identifier les visiteurs récurrents (fidélisation ou anomalies).
*   Visualiser la durée moyenne d'attente/visite au sein de ce service spécifique.

---

## 5. Détails Techniques de l'Implémentation

Le module s'appuie sur les agrégations avancées de Django (`annotate`, `Count`, `TruncMonth`) pour minimiser la charge sur le serveur.

```python
# Exemple d'agrégation pour les statistiques par service
service_stats = Visite.objects.values('service_visite__nom').annotate(
    count=Count('id')
).order_by('-count')[:5]
```

Les données sont ensuite passées au frontend sous format JSON pour être injectées dans les graphiques Canvas.

---

## 6. Valeur Ajoutée

Ce module permet de :
*   **Optimiser les ressources :** Renforcer les effectifs de sécurité lors des pics d'affluence identifiés.
*   **Justifier l'activité :** Fournir des preuves chiffrées de l'accueil du public pour chaque département.
*   **Audit de performance :** Mesurer l'efficacité du traitement des visiteurs par les agents.

---
*Grâce à ce module, la donnée devient un levier de performance pour l'organisation.*
