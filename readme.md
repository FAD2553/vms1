# 🚀 UWaZy VMS - Guide d'exploitation et d'installation (A à Z)

Bienvenue dans le guide officiel d'exploitation et d'installation de **UWaZy VMS** (Visitor Management System). Ce système est conçu pour la gestion moderne, sécurisée et fluide des flux d'entrées et de sorties des visiteurs au sein d'un établissement. 

L'application intègre notamment la reconnaissance optique de caractères (**OCR**) pour la lecture automatique des Cartes Nationales d'Identité Burkinabè (**CNIB**), une authentification forte à double facteur (**2FA**), ainsi qu'un journal d'audit complet des actions administratives.

---

## 📋 Table des matières
1. [Prérequis Système](#-prérequis-système)
2. [Étape 1 : Téléchargement du projet depuis GitHub](#-étape-1--téléchargement-du-projet-depuis-github)
3. [Étape 2 : Configuration de la Base de Données (PostgreSQL)](#-étape-2--configuration-de-la-base-de-données-postgresql)
4. [Étape 3 : Installation des Dépendances Python](#-étape-3--installation-des-dépendances-python)
5. [Étape 4 : Installation et Configuration de Tesseract OCR](#-étape-4--installation-et-configuration-de-tesseract-ocr)
6. [Étape 5 : Initialisation et Migrations de l'application](#-étape-5--initialisation-et-migrations-de-lapplication)
7. [Étape 6 : Lancement du serveur et Accès](#-étape-6--lancement-du-serveur-et-accès)
8. [Étape 7 : Fonctionnement et Test de l'OCR (Scan CNIB)](#-étape-7--fonctionnement-et-test-de-locr-scan-cnib)
9. [Étape 8 : Fonctionnement et Gestion du Double Facteur (2FA)](#-étape-8--fonctionnement-et-gestion-du-double-facteur-2fa)
10. [🛠️ Dépannage et Résolution des Erreurs](#%EF%B8%8F-dépannage-et-résolution-des-erreurs)

---

## 📋 Prérequis Système

Pour faire fonctionner cette application sur votre PC sous Windows, vous devez installer au préalable :
- **Python 3.10 ou version supérieure** (assurez-vous de cocher l'option *"Add Python to PATH"* lors de l'installation).
- **PostgreSQL 14 ou version supérieure**.
- **Git** (pour cloner le projet depuis GitHub).
- Un navigateur web moderne (Google Chrome, Mozilla Firefox, Microsoft Edge, etc.).

---

## 📥 Étape 1 : Téléchargement du projet depuis GitHub

### Option A : En utilisant Git (Recommandé)
1. Ouvrez votre terminal (Invite de commandes `cmd` ou PowerShell).
2. Naviguez vers le dossier dans lequel vous souhaitez cloner le projet :
   ```bash
   cd C:\Chemin\Vers\Votre\Dossier
   ```
3. Exécutez la commande de clonage suivante :
   ```bash
   git clone https://github.com/uwazy-bf-dev/stage-wms.git
   ```
4. Accédez au dossier du projet nouvellement créé :
   ```bash
   cd stage-wms
   ```

### Option B : Téléchargement du fichier ZIP
1. Allez sur la page GitHub du projet.
2. Cliquez sur le bouton vert **Code**, puis sur **Download ZIP**.
3. Extrayez l'archive ZIP téléchargée dans un dossier de votre choix sur votre ordinateur.
4. Ouvrez un terminal dans ce dossier.

---

## 🐘 Étape 2 : Configuration de la Base de Données (PostgreSQL)

L'application utilise **PostgreSQL** pour stocker les informations de manière sécurisée. La configuration définie par défaut dans le projet (`gestions_entree_sortie/settings.py`) attend les paramètres suivants :

- **Nom de la base de données :** `gestion_db`
- **Utilisateur (User) :** `postgres`
- **Mot de passe (Password) :** `admin123`
- **Hôte (Host) :** `localhost`
- **Port :** `5432`

### Procédure de configuration sur PostgreSQL :
1. Lancez **pgAdmin** ou ouvrez le terminal PostgreSQL CLI (`psql`).
2. Connectez-vous avec l'utilisateur administrateur `postgres`.
3. Assurez-vous que le mot de passe de l'utilisateur `postgres` est bien `admin123`. Si ce n'est pas le cas, vous pouvez le modifier ou adapter la configuration dans `settings.py` au niveau du dictionnaire `DATABASES`.
4. Créez une nouvelle base de données appelée `gestion_db` en exécutant la requête SQL suivante :
   ```sql
   CREATE DATABASE gestion_db;
   ```

---

## 🐍 Étape 3 : Installation des Dépendances Python

Il est fortement recommandé d'utiliser un environnement virtuel Python pour ne pas interférer avec d'autres projets sur votre ordinateur.

1. **Créer l'environnement virtuel** :
   À la racine du projet `vms1`, ouvrez votre terminal et lancez la commande suivante :
   ```bash
   python -m venv venv
   ```

2. **Activer l'environnement virtuel** :
   - **Sous PowerShell** :
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
     *(Note : Si vous obtenez une erreur de restriction d'exécution de script, exécutez d'abord la commande `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` puis réactivez).*
   
   - **Sous l'invite de commande classique (CMD)** :
     ```cmd
     .\venv\Scripts\activate.bat
     ```

3. **Installer les packages requis** :
   Une fois l'environnement virtuel activé (vous devriez voir `(venv)` s'afficher au début de votre ligne de commande), installez les dépendances :
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   *(Note : `requirements.txt` contient déjà tous les modules essentiels tels que Django, Pillow, pytesseract, pyotp, qrcode, xhtml2pdf et psycopg2-binary pour PostgreSQL).*

---

## 👁️ Étape 4 : Installation et Configuration de Tesseract OCR

L'OCR de l'application utilise **Tesseract**, un moteur open-source puissant développé par Google, pour extraire les textes des images de cartes d'identité (CNIB).

### 1. Télécharger l'installateur Windows de Tesseract :
Téléchargez l'installateur exécutable pour Windows 64 bits (généralement fourni par UB Mannheim) via ce lien officiel :
👉 [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

### 2. Procéder à l'installation (Étape cruciale pour le français) :
1. Lancez le fichier `.exe` téléchargé.
2. Suivez les étapes de l'assistant d'installation.
3. **⚠️ Attention absolue lors du choix des composants** :
   - À l'étape *"Choose Components"*, déroulez la section **"Additional script data"** et **"Additional language data"**.
   - Cochez impérativement la case correspondant au **Français** (`French`) pour installer les fichiers de données d'apprentissage du français (`fra.traineddata`).
4. Installez Tesseract dans le répertoire par défaut :
   `C:\Program Files\Tesseract-OCR`

### 3. Vérification du chemin dans le code :
Le code de l'application (`core/ocr.py`) cible directement l'exécutable de Tesseract à cet emplacement précis :
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
Si vous avez installé Tesseract dans un dossier différent, vous devez modifier cette ligne pour refléter le chemin réel de votre installation de Tesseract.

---

## ⚙️ Étape 5 : Initialisation et Migrations de l'application

Maintenant que la base de données est créée et que les dépendances sont installées, il faut initialiser les tables et le compte administrateur.

1. **Appliquer les migrations de base de données** :
   Exécutez la commande suivante dans le terminal (avec l'environnement virtuel activé) :
   ```bash
   python manage.py migrate
   ```
   Cette commande crée toutes les tables nécessaires dans votre base de données PostgreSQL `gestion_db`.

2. **Créer le compte Super-Administrateur** :
   Créez un compte administrateur principal pour accéder au panneau de configuration :
   ```bash
   python manage.py createsuperuser
   ```
   Renseignez un nom d'utilisateur, une adresse email et un mot de passe robuste.

3. **Créer l'administrateur de secours (`admin_secours`)** :
   Pour garantir la continuité de l'accès au système en cas de perte de clé 2FA, le système propose un super-utilisateur spécial nommé `admin_secours`. 
   Vous pouvez le créer via la console Django ou directement par la commande ci-dessus en choisissant le nom d'utilisateur `admin_secours`.
   
   *Caractéristiques de `admin_secours` :*
   - Ne possède pas l'obligation d'avoir la double authentification (2FA).
   - Est masqué des listes d'utilisateurs et des statistiques globales pour des raisons de confidentialité et de sécurité.
   - Permet de désactiver la double authentification (2FA) des autres administrateurs bloqués ou de réinitialiser leurs mots de passe.

---

## ⚡ Étape 6 : Lancement du serveur et Accès

1. Dans votre terminal, démarrez le serveur Web Django :
   ```bash
   python manage.py runserver
   ```
2. Ouvrez votre navigateur internet et rendez-vous à l'adresse suivante :
   👉 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
3. Connectez-vous avec les identifiants de votre compte Super-Administrateur créé précédemment.

---

## 📸 Étape 7 : Fonctionnement et Test de l'OCR (Scan CNIB)

Le module d'OCR intégré permet d'éviter la saisie manuelle fastidieuse des informations du visiteur. 

### Comment l'OCR fonctionne-t-il techniquement ?
1. **Rognage précis au niveau du navigateur (Client-side Cropping)** : 
   Lorsque la photo est prise via la caméra de l'appareil (téléphone ou ordinateur), l'application calcule dynamiquement la zone délimitée par le guide en pointillés (`#camera-guide`). Seule cette partie cadrée de l'image est extraite et dessinée sur un canvas haute résolution avant d'être soumise à l'OCR. Cela élimine le bruit visuel périphérique (arrière-plan, doigts, surface de la table) pour une précision de détection accrue.
2. **Double passe d'analyse côté serveur** :
   - **Passe 1 (Standard)** : Analyse globale de la zone rognée de la CNIB pour en extraire le Nom, le Prénom et la Date de naissance grâce à des expressions régulières configurées pour les pièces burkinabè.
   - **Passe 2 (Ciblée pour le numéro CNIB)** : Afin d'assurer une fidélité maximale sur le numéro d'identité (format burkinabè `BXXXXXXXX`), le système extrait la région d'intérêt, effectue un prétraitement d'image (conversion en niveaux de gris, redimensionnement 2x, et application d'un seuillage binaire pour rendre le texte parfaitement noir sur fond blanc), puis lance Tesseract en mode lecture de texte clairsemé (PSM 11).

### Dossier de vérification des captures :
Pour vous permettre de valider l'efficacité du rognage de l'image, toutes les photos prises par les caméras (que ce soit pour l'OCR ou pour les scans de pièces d'identité joints) sont enregistrées de manière persistante sur le serveur dans le dossier :
📂 `media/captures_camera/`

Chaque fichier y est enregistré avec un horodatage unique (ex: `ocr_scan_20260519_214532_123456.jpg`). Vous pouvez y naviguer pour inspecter visuellement les images rognées envoyées à l'OCR.

### Étapes pour tester l'OCR :
1. Rendez-vous sur le **Tableau de Bord** principal.
2. Cliquez sur le raccourci **Scanner CNIB** (ou allez dans *Visiteurs* > *Ajouter un Visiteur*).
3. **Capture d'image** : Alignez le recto de la CNIB à l'intérieur du rectangle en pointillés, puis cliquez sur le déclencheur (bouton central).
4. La photo est capturée, automatiquement rognée à la taille du rectangle, puis un message s'affiche.
5. Cliquez sur **Scanner** pour lancer la détection. Les champs **Nom**, **Prénom**, **Numéro CNIB** et **Date de naissance** seront préremplis.
6. Rendez-vous dans le répertoire `media/captures_camera/` sur votre PC pour constater que l'image enregistrée est uniquement la portion cadrée/rognée de la carte d'identité !

---

## 🔐 Étape 8 : Fonctionnement et Gestion du Double Facteur (2FA)

Pour renforcer la sécurité de l'application, l'authentification à double facteur (2FA) est disponible pour tous les comptes utilisateurs (agents et administrateurs).

### 1. Activer le 2FA sur son compte :
1. Une fois connecté, cliquez sur l'onglet **Sécurité 2FA** dans la barre latérale.
2. Un code QR unique ainsi qu'une clé de secours s'affichent à l'écran.
3. Ouvrez une application d'authentification sur votre smartphone (comme **Google Authenticator**).
4. Scannez le code QR affiché sur l'écran.
5. Saisissez le code de validation à 6 chiffres généré par votre téléphone portable dans l'application, puis cliquez sur **Activer 2FA**.
6. À partir de ce moment, chaque connexion nécessitera de saisir votre nom d'utilisateur, votre mot de passe et le code OTP temporaire affiché sur votre application mobile.

### 2. Scénario de secours : Perte du téléphone ou de la clé 2FA
Si un agent perd son téléphone ou ne peut plus générer de code OTP :
1. Connectez-vous à l'application avec le compte de l'admin.
2. Accédez à l'onglet **Gestion des Agents**.
3. Dans la liste, trouvez l'utilisateur bloqué, cliquez sur le menu déroulant d'actions et sélectionnez **Désactiver 2FA**.
4. L'utilisateur pourra à nouveau se connecter normalement avec son mot de passe simple et réinitialiser sa configuration 2FA s'il le souhaite.

---

## 🛠️ Dépannage et Résolution des Erreurs

### 1. Erreur : `TesseractNotFoundError: tesseract is not installed or it's not in your PATH`
- **Cause :** Tesseract n'est pas installé sur votre PC, ou l'exécutable ne se trouve pas dans le chemin par défaut.
- **Solution :** Reprenez l'**Étape 4**. Vérifiez que l'exécutable existe bien au chemin `C:\Program Files\Tesseract-OCR\tesseract.exe`. Si vous l'avez installé ailleurs, ajustez la variable `tesseract_cmd` dans `core/ocr.py`.

### 2. Erreur : Le texte de la carte d'identité est mal lu (erreur de reconnaissance)
- **Cause :** L'image est floue, mal éclairée ou trop inclinée.
- **Solution :** Veillez à ce que la photo de la carte soit bien droite, nette, sans reflets de lumière directs et recadrée le plus possible sur le recto de la CNIB.

### 3. Erreur : `OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed`
- **Cause :** Le service PostgreSQL n'est pas démarré, ou les identifiants de connexion configurés dans `settings.py` sont incorrects.
- **Solution :** 
  - Ouvrez l'outil de gestion des services de Windows (`services.msc`), trouvez le service `postgresql` et cliquez sur **Démarrer**.
  - Vérifiez dans le fichier `gestions_entree_sortie/settings.py` que le nom d'utilisateur, le mot de passe et le port correspondent bien aux paramètres de votre installation PostgreSQL.

---

*UWaZy VMS - Développé par KONFE Patoin Ousmane Fad pour la performance et la sécurité des accès de votre établissement.*
