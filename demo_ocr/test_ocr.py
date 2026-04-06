import os
import re

try:
    from PIL import Image
    import pytesseract

    # Set Tesseract path on Windows
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _get_ocr_lang():
    """Return 'fra' if available, else 'eng'."""
    try:
        langs = pytesseract.get_languages()
        return 'fra' if 'fra' in langs else 'eng'
    except Exception:
        return 'eng'


def extract_cni_info_demo(image_path):
    """
    Extract information from a CNI image using Tesseract OCR.
    Version avec deux passes pour contourner les faiblesses de l'OCR.
    """
    if not OCR_AVAILABLE:
        print("Tesseract OCR is not available/installed.")
        return {}

    try:
        img_original = Image.open(image_path)
        lang = _get_ocr_lang()
        result = {}

        # PASSE 1: Extraction normale (pour Nom, Prénom, Date)
        text_pass1 = pytesseract.image_to_string(img_original, lang=lang)
        lines_pass1 = [l.strip() for l in text_pass1.split('\n') if l.strip()]

        for line in lines_pass1:
            line_upper = line.upper()

            # Extraction du Nom
            match_nom = re.search(r'NOM\s*[:;]\s*(.+)', line_upper)
            if match_nom and 'nom' not in result:
                result['nom'] = match_nom.group(1).strip()

            # Extraction du Prénom
            match_prenom = re.search(r'PR[EÉ]NOM[S]?\s*[:;]\s*(.+)', line_upper)
            if match_prenom and 'prenom' not in result:
                result['prenom'] = match_prenom.group(1).strip()

            # Extraction de la Date de naissance
            date_match = re.search(r'(\d{2}[/.-]\d{2}[/.-]\d{4})', line)
            if date_match and 'date_naissance' not in result:
                date_str = date_match.group()
                date_str = date_str.replace('.', '/').replace('-', '/')
                result['date_naissance'] = date_str


        # PASSE 2: Extraction ciblée pour le numéro CNI isolé (BXXXXXXXX)
        # Preprocessing: Convert to grayscale, resize 2x, light threshold
        img_processed = img_original.convert('L')
        width, height = img_processed.size
        img_processed = img_processed.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        img_processed = img_processed.point(lambda p: 255 if p > 120 else 0)

        # Utilisation du mode PSM 11 (Sparse text) qui lit très bien les blocs isolés
        text_pass2 = pytesseract.image_to_string(img_processed, lang=lang, config=r'--psm 11')
        
        # Le numéro CNI BXXXXXXXX peut se trouver n'importe où dans le texte de la passe 2
        # La regex tolère les espaces intrus que l'OCR pourrait rajouter, ex: "B 1 2 3 45678"
        cni_match = re.search(r'B\s*(?:\d\s*){8}', text_pass2.upper())
        if cni_match:
            result['numero_cni'] = cni_match.group().replace(' ', '').strip()
        elif 'numero_cni' not in result:
            # Fallback regex pour la passe 1 au cas où
            for line in lines_pass1:
                cni_fallback = re.search(r'B\s*(?:\d\s*){8}', line.upper())
                if cni_fallback:
                    result['numero_cni'] = cni_fallback.group().replace(' ', '').strip()
                    break

        return result

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return {}


if __name__ == '__main__':
    print("Script de démonstration d'extraction CNI OCR")
    print("============================================")
    print("Ce script permet de tester la nouvelle logique d'extraction")
    print("sans modifier le code source principal du projet Django.")
    print("--------------------------------------------")
    
    test_image = input("Entrez le chemin vers l'image de la CNI à tester : ")
    if os.path.exists(test_image):
        print(f"\nTraitement de l'image : {test_image} ...")
        result = extract_cni_info_demo(test_image)
        print("\nRésultat de l'extraction :")
        for key, value in result.items():
            print(f"- {key.capitalize()}: {value}")
        
        if not result:
            print("Aucune information n'a pu être extraite.")
    else:
        print(f"Le fichier {test_image} n'existe pas.")
