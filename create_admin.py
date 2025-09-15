from sqlalchemy.orm import sessionmaker
from app import engine, Base, User, hash_password

# Création de la session
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Vérifier si l'admin existe déjà
admin_email = "admin@example.com"
admin = db.query(User).filter(User.email == admin_email).first()

if not admin:
    a = User(
        email=admin_email,
        nom="Administrator",
        password=hash_password("admin1234"),
        role="admin",
        formula=5
    )
    db.add(a)
    db.commit()
    print("Admin créé !")
else:
    print("Admin existe déjà")

db.close()
