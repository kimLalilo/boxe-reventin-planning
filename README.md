# Club de Boxe Reventin – Gestion des Inscriptions

Application web pour gérer les inscriptions aux cours de boxe du **Club de Boxe Reventin**, développée avec **Streamlit**.  
La base de données est hébergée sur **Supabase (PostgreSQL)**.

---

## Fonctionnalités

### Pour les utilisateurs
- Connexion / déconnexion sécurisée  
- Consultation du planning de la semaine (Lundi → Vendredi)  
- Réservation de cours selon la formule choisie  
- Inscription sur liste d’attente si cours complet  
- Annulation de réservation  
- Gestion de son compte et changement de mot de passe  

### Pour les coachs
- Consultation du planning avec nombre de places réservées et liste d’attente  
- Consultation des participants aux cours  

### Pour les administrateurs
- Gestion complète des utilisateurs :
  - Création, modification, suppression  
  - Changement de rôle (user / coach / admin)  
  - Gestion du nombre de cours maximum (formule)  
- Gestion complète des cours :
  - Création, modification, suppression  
  - Capacité et horaire configurable  
- Visualisation du planning et des utilisateurs sous forme de tableau  

---

## Prérequis

- Python 3.10 ou supérieur  
- Streamlit   
- Pandas  
- psycopg2-binary (pour la connexion PostgreSQL / Supabase)

---

## Installation

1. Cloner le dépôt :

`git clone https://github.com/kimLalilo/boxe-reventin-planning.git`

2. Créer un environnement virtuel :

# Linux / macOS
`python3 -m venv venv`
`source venv/bin/activate`

# Windows
`python -m venv venv`
`venv\Scripts\activate`


3. Installer les dépendances :

`pip install -r requirements.txt`

## Configuration de la base de données

### Supabase

1. Créer un projet sur [Supabase](https://supabase.com/).  
2. Récupérer les informations suivantes :
   - **URL du projet**
   - **Mot de passe de la base PostgreSQL**
   - **Nom de la base** (par défaut `postgres`)  

3. Ajouter les secrets 
- en local dans le fichier `.streamlit/secrets.toml`

```
DATABASE_URL = st.secrets["database"]["url"]
engine = create_engine(DATABASE_URL, connect_args={"sslmode": "require"})
```

## Lancement en local

`streamlit run app.py`


## Auteur
Nom : Nguyen Kim
Projet : Club de Boxe Reventin – Gestion des inscriptions
Tech Stack : Python, Streamlit, Supabase