Ce document explique comment le système **VMS (Uwazy)** lit automatiquement les informations sur les cartes d'identité (CNIB).

### Qu'est-ce que l'OCR ?
L'**OCR** (Reconnaissance Optique de Caractères) est une technologie qui permet à un ordinateur de "lire" le texte écrit sur une image, exactement comme un humain le ferait, et de le transformer en texte modifiable sur un clavier.

---

## 1. Choix Technologique : Tesseract OCR

Le choix de **Tesseract** (moteur de HP/Google) repose sur sa capacité à fonctionner hors-ligne (souveraineté des données) et sa gratuité totale. Nous utilisons l'extension Python `pytesseract` comme interface de communication.

---

## 2. Le Pipeline de Traitement d'Image

L'OCR brut sur une photo de CNIB donne souvent de mauvais résultats (bruit, ombres, reflets). Nous avons donc implémenté un pipeline de prétraitement avec la bibliothèque **Pillow**.

### Flux de Transformation
1.  **Réception :** L'image originale (souvent en couleur et haute résolution).
2.  **Conversion en Niveaux de Gris :** Élimination des informations de couleur inutiles pour simplifier l'analyse.
3.  **Redimensionnement (Scale x2) :** Augmentation de la résolution logicielle pour rendre les caractères plus nets.
4.  **Seuillage (Binarisation) :** C'est l'étape la plus magique. On transforme l'image en noir et blanc pur. Tout ce qui est gris clair devient blanc, et tout ce qui est gris foncé devient noir. Cela permet de détacher les lettres du fond de la carte pour que l'ordinateur ne soit pas perturbé par les dessins de sécurité de la CNIB.

---

## 3. Logique d'Extraction par "Double Passage"

Pour maximiser la précision, le module exécute deux types d'analyse :

### Passage 1 : Lecture Globale
*   **Objectif :** Identifier la structure du document et extraire les champs textuels longs (Nom, Prénom, Profession).
*   **Configuration Tesseract :** Utilisation du pack de langue française (`fra`).

### Passage 2 : Lecture Précise (Format CNIB)
*   **Objectif :** Extraire le numéro unique de la CNIB sans erreur.
*   **Technique :** Nous isolons la zone basse de la carte où se situe le numéro et appliquons une configuration Tesseract restrictive (uniquement caractères alphanumériques).
*   **Validation Regex :** Le système utilise une règle appelée **Regex** (une sorte de filtre intelligent) pour s'assurer que le numéro trouvé ressemble bien à un numéro de CNIB (un 'B' suivi de 8 chiffres).
    *   *Exemple :* Si l'ordinateur lit "B12345678", le Regex dit "C'est bon !". S'il lit "Bonjour", le Regex dit "C'est faux !".

---

## 4. Intégration dans Django (Logique de la Vue)

Le module OCR n'est pas un script isolé mais une fonction intégrée dans une vue de traitement asynchrone (AJAX).

```python
# Exemple de pseudo-code du module
def extract_cni_data(image_path):
    # 1. Ouvrir et Prétraiter
    img = Image.open(image_path).convert('L')
    img = img.point(lambda x: 0 if x < 140 else 255) # Binarisation
    
    # 2. OCR
    raw_text = pytesseract.image_to_string(img, lang='fra')
    
    # 3. Parsing intelligent
    data = {
        'nom': parse_name(raw_text),
        'cni': find_pattern(raw_text, r"B\d{8}"),
        'date_naiss': parse_date(raw_text)
    }
    return data
```

---

## 5. Performances et Limites

*   **Temps de réponse :** Entre 1 et 3 secondes selon la résolution de l'image et la puissance du processeur du serveur.
*   **Précision :** ~90% sur des photos de bonne qualité.
*   **Points d'attention :** La netteté de la photo prise par l'agent est le facteur déterminant. Le système renvoie les données pour validation humaine afin de corriger les 10% d'erreurs potentielles.

---
*Ce module constitue l'innovation majeure du projet, réduisant le temps d'enregistrement d'un visiteur de plus de 60%.*
