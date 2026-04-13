import os
import re
try:
    from PIL import Image, ImageOps
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


def extract_cnib_info(image_path):
    """
    Extract info from CNIB image.
    Strictly matching demo_ocr/test_ocr.py.
    """
    if not OCR_AVAILABLE:
        return {}

    try:
        img_original = Image.open(image_path)
        img_original = ImageOps.exif_transpose(img_original)
        lang = _get_ocr_lang()
        result = {}

        # PASSE 1: Extraction normale (Nom, Prenom, Date)
        text_pass1 = pytesseract.image_to_string(img_original, lang=lang)
        lines_pass1 = [l.strip() for l in text_pass1.split('\n') if l.strip()]

        for line in lines_pass1:
            line_upper = line.upper()
            
            # Extraction du Nom
            match_nom = re.search(r'NOM\s*[:;]?\s*(.+)', line_upper)
            if match_nom and 'nom' not in result:
                result['nom'] = match_nom.group(1).strip()
            
            # Extraction du Prénom
            match_prenom = re.search(r'PR[EÉ]NOM[S]?\s*[:;]?\s*(.+)', line_upper)
            if match_prenom and 'prenom' not in result:
                result['prenom'] = match_prenom.group(1).strip()
            
            # Extraction de la Date de naissance
            date_match = re.search(r'(\d{2}[/.-]\d{2}[/.-]\d{4})', line)
            if date_match and 'date_naissance' not in result:
                date_str = date_match.group()
                date_str = date_str.replace('.', '/').replace('-', '/')
                result['date_naissance'] = date_str

            # Extraction du Sexe (M ou F)
            match_sexe = re.search(r'SEXE\s*[:;]?\s*([MF])', line_upper)
            if match_sexe and 'sexe' not in result:
                result['sexe'] = match_sexe.group(1)

            # Extraction de la Profession
            match_prof = re.search(r'PROFESSION\s*[:;]?\s*(.+)', line_upper)
            if match_prof and 'profession' not in result:
                result['profession'] = match_prof.group(1).strip()

        # PASSE 2: Extraction ciblée pour le numéro CNI (BXXXXXXXX)
        # Preprocessing: Convert to grayscale, resize 2x, light threshold
        img_processed = img_original.convert('L')
        width, height = img_processed.size
        # Resize 2x (LANCZOS)
        img_processed = img_processed.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        # Threshold 120
        img_processed = img_processed.point(lambda p: 255 if p > 120 else 0)

        # Utilisation de PSM 11 (Sparse text)
        text_pass2 = pytesseract.image_to_string(img_processed, lang=lang, config='--psm 11')
        text_pass2_upper = text_pass2.upper()
        
        # Regex B + 8 digits (tolerating spaces)
        cni_match = re.search(r'B\s*(?:\d\s*){8}', text_pass2_upper)
        if cni_match:
            result['numero_cni'] = cni_match.group().replace(' ', '').strip()
        elif 'numero_cni' not in result:
            # Fallback regex pass 1
            for line in lines_pass1:
                cni_fallback = re.search(r'B\s*(?:\d\s*){8}', line.upper())
                if cni_fallback:
                    result['numero_cni'] = cni_fallback.group().replace(' ', '').strip()
                    break

        return result

    except Exception:
        return {}
