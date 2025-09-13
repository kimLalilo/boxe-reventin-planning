import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy import asc
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import hashlib
from datetime import datetime, timedelta
import pandas as pd

# -------------------------
# Config graphique
# -------------------------
st.set_page_config(page_title="Club de Boxe Reventin - Inscriptions",
                   page_icon="🥊", layout="wide")
st.markdown("""
<style>
.big-title {font-size: 2.5rem;color: #B22222;font-weight: bold;}
.subtitle {color: #555555;}
.stButton>button {background-color: #B22222;color: #FFFFFF;}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1,4])
with col1:
    try: st.image("assets/logo.png", width=100)
    except: st.write("🥊")
with col2:
    st.markdown("<h1 class='big-title'>Club de Boxe Reventin</h1>", unsafe_allow_html=True)
    st.caption("Application de gestion des inscriptions aux cours")

with st.sidebar:
    try: st.image("assets/logo.png", width=150)
    except: st.write("🥊")
    st.markdown("### Club de Boxe Reventin")


# -------------------------
# Config base de données
# -------------------------
DATABASE_URL = st.secrets["database"]["url"]
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# -------------------------
# Models
# -------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    nom = Column(String)
    password = Column(String)
    role = Column(String, default="user")
    formula = Column(Integer, default=1)
    reservations = relationship("Reservation", back_populates="user")

class CourseSlot(Base):
    __tablename__ = "courseslot"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    weekday = Column(Integer)  # 0=lundi ... 4=vendredi
    start_time = Column(String)
    end_time = Column(String)
    capacity = Column(Integer, default=10)
    reservations = relationship("Reservation", back_populates="course")

class Reservation(Base):
    __tablename__ = "reservation"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    course_id = Column(Integer, ForeignKey("courseslot.id"))
    cancelled = Column(Boolean, default=False)
    waitlist = Column(Boolean, default=False)

    user = relationship("User", back_populates="reservations")
    course = relationship("CourseSlot", back_populates="reservations")

Base.metadata.create_all(engine)

# -------------------------
# Helpers
# -------------------------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_password(pw, hashed):
    return hash_password(pw) == hashed

def get_weekdays():
    return ["Lundi","Mardi","Mercredi","Jeudi","Vendredi"]

def login_user(email, password):
    db = Session()
    user = db.query(User).filter_by(email=email).first()
    if user and verify_password(password, user.password):
        st.session_state["user_id"] = user.id
        st.session_state["role"] = user.role
        return True
    return False

def get_current_user():
    if "user_id" in st.session_state:
        db = Session()
        return db.query(User).get(st.session_state["user_id"])
    return None

# -------------------------
# UI Connexion
# -------------------------
def login_ui():
    with st.form("login_form"):
        email = st.text_input("Email")
        pw = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
        if submitted:
            if login_user(email, pw):
                st.success("Connexion réussie")
                st.rerun()
            else:
                st.error("Email ou mot de passe invalide")

# -------------------------
# UI Utilisateur
# -------------------------
def user_view(user: User):
    tabs = st.tabs(["Planning hebdo", "Mon compte"])
    db = Session()

    # Planning
    with tabs[0]:
        st.subheader("Planning de la semaine (Lundi - Vendredi)")
        weekdays = get_weekdays()
        cols = st.columns(len(weekdays))
        for idx, day in enumerate(weekdays):
            with cols[idx]:
                st.markdown(f"### {day}")
                # Exemple pour user_view
                slots = db.query(CourseSlot).filter_by(weekday=idx).order_by(asc(CourseSlot.start_time)).all()
                for slot in slots:
                    count_res = db.query(Reservation).filter(
                        Reservation.course_id==slot.id,
                        Reservation.cancelled==False,
                        Reservation.waitlist==False
                    ).count()
                    dispo = slot.capacity - count_res
                    st.markdown(f"**{slot.title} ({slot.start_time}-{slot.end_time})**")
                    st.write(f"Places restantes : {dispo}")
                    already = db.query(Reservation).filter_by(
                        user_id=user.id, course_id=slot.id, cancelled=False
                    ).first()
                    # Add green background for booked slots
                    
                    with st.form(f"res_{slot.id}"):
                        if already:
                            cancel = st.form_submit_button("Annuler", 
                                                          use_container_width=True,
                                                          type="primary")
                            st.markdown("""
                            <style>
                            div[data-testid="stForm"] button[kind="primary"] {
                                background-color: green;
                                color: white;
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            if cancel:
                                if not already.waitlist:
                                    already.cancelled = True
                                    db.commit()
                                    st.success("Réservation annulée")
                                    st.rerun()
                                else:
                                    db.delete(already)
                                    db.commit()
                                    st.success("Annulé de la liste d'attente")
                                    st.rerun()
                        else:
                            if dispo > 0:
                                reserve = st.form_submit_button("Réserver")
                                if reserve:
                                    week_res = db.query(Reservation).join(CourseSlot).filter(
                                        Reservation.user_id==user.id,
                                        Reservation.cancelled==False,
                                        Reservation.waitlist==False
                                    ).count()
                                    if week_res < user.formula:
                                        r = Reservation(user_id=user.id, course_id=slot.id)
                                        db.add(r)
                                        db.commit()
                                        st.success("Réservation confirmée")
                                        st.rerun()
                                    else:
                                        st.error("Limite de réservations atteinte pour votre formule.")
                            else:
                                wait = st.form_submit_button("Cours complet - Liste d'attente")
                                if wait:
                                    r = Reservation(user_id=user.id, course_id=slot.id, waitlist=True)
                                    db.add(r)
                                    db.commit()
                                    st.success("Inscrit sur liste d'attente")
                                    st.rerun()
                    

    # Mon compte
    with tabs[1]:
        st.subheader("Mon compte")
        with st.form("pw_change"):
            new_pw = st.text_input("Nouveau mot de passe", type="password")
            submit_pw = st.form_submit_button("Changer")
            if submit_pw and new_pw:
                user.password = hash_password(new_pw)
                db.commit()
                st.success("Mot de passe modifié")

# -------------------------
# UI Coach
# -------------------------
def coach_view():
    db = Session()
    st.subheader("Planning coach")
    weekdays = get_weekdays()
    cols = st.columns(len(weekdays))
    for idx, day in enumerate(weekdays):
        with cols[idx]:
            st.markdown(f"### {day}")
            slots = db.query(CourseSlot).filter_by(weekday=idx).order_by(asc(CourseSlot.start_time)).all()
            for slot in slots:
                count_res = db.query(Reservation).filter(
                    Reservation.course_id==slot.id,
                    Reservation.cancelled==False,
                    Reservation.waitlist==False
                ).count()
                wait_count = db.query(Reservation).filter(
                    Reservation.course_id==slot.id,
                    Reservation.cancelled==False,
                    Reservation.waitlist==True
                ).count()
                # Display title and time on first line
                st.markdown(f"**{slot.title}** ({slot.start_time}-{slot.end_time})")
                # Display capacity count on second line in red if zero reservations
                if count_res == 0:
                    st.markdown(f"<span style='color:red;'>{count_res}/{slot.capacity} réservés</span>", unsafe_allow_html=True)
                else:
                    st.write(f"{count_res}/{slot.capacity} réservés")
                if count_res + wait_count > 0:
                    if st.button(f"Voir utilisateurs ({slot.id})"):
                        res = db.query(Reservation).filter(
                            Reservation.course_id==slot.id,
                            Reservation.cancelled==False
                        ).all()
                        st.info("\n".join([f"{r.user.nom} ({r.user.email})" + (" - Liste d'attente" if r.waitlist else "") for r in res]))

# -------------------------
# UI Admin
# -------------------------
def admin_view():
    db = Session()
    st.subheader("Administration")

    tabs = st.tabs(["Utilisateurs", "Cours"])

    # -------------------------
    # Gestion Utilisateurs
    # -------------------------
    with tabs[0]:
        st.subheader("Gestion des utilisateurs")
        
        # Récupération et affichage sous forme de table
        def refresh_users():
            users = db.query(User).all()
            df_users = pd.DataFrame([{
                "Nom": u.nom,
                "Email": u.email,
                "Rôle": u.role,
                "Formule": u.formula
            } for u in users])
            st.dataframe(df_users)
            return users

        users = refresh_users()

        # Ajouter un utilisateur
        with st.expander("Ajouter un utilisateur"):
            with st.form("add_user"):
                nom = st.text_input("Nom")
                email = st.text_input("Email")
                pw = st.text_input("Mot de passe", type="password")
                role = st.selectbox("Rôle", ["user","coach","admin"])
                formula = st.number_input("Formule (nb cours)",1,5,1)
                if st.form_submit_button("Créer"):
                    if db.query(User).filter_by(email=email).first():
                        st.error("Email déjà utilisé")
                    else:
                        new = User(nom=nom,email=email,password=hash_password(pw),role=role,formula=formula)
                        db.add(new)
                        db.commit()
                        st.success("Utilisateur créé")
                        st.rerun()

        # Modifier / Supprimer un utilisateur
        with st.expander("Modifier / Supprimer un utilisateur"):
            if users:
                user_sel = st.selectbox("Sélectionner un utilisateur", users, format_func=lambda u: f"{u.nom} ({u.email})")
                if user_sel:
                    with st.form(f"edit_user_{user_sel.id}"):
                        nom = st.text_input("Nom", value=user_sel.nom)
                        role = st.selectbox("Rôle", ["user","coach","admin"], index=["user","coach","admin"].index(user_sel.role))
                        formula = st.number_input("Formule",1,5,user_sel.formula)
                        pw = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", type="password")
                        edit = st.form_submit_button("Modifier")
                        delete = st.form_submit_button("Supprimer")
                        
                        if edit:
                            user_sel.nom = nom
                            user_sel.role = role
                            user_sel.formula = formula
                            if pw:
                                user_sel.password = hash_password(pw)
                            db.commit()
                            st.success("Utilisateur modifié")
                            st.rerun()

                        if delete:
                            db.delete(user_sel)
                            db.commit()
                            st.success("Utilisateur supprimé")
                            st.rerun()
            else:
                st.info("Aucun utilisateur trouvé")

    # -------------------------
    # Gestion Cours
    # -------------------------
    with tabs[1]:
        st.subheader("Gestion des cours")
        
        # Récupération et affichage sous forme de table
        def refresh_courses():
            courses = db.query(CourseSlot).all()
            df_courses = pd.DataFrame([{
                "Titre": c.title,
                "Jour": get_weekdays()[c.weekday],
                "Début": c.start_time,
                "Fin": c.end_time,
                "Capacité": c.capacity
            } for c in courses])
            st.dataframe(df_courses)
            return courses

        courses = refresh_courses()

        # Ajouter un cours
        with st.expander("Ajouter un cours"):
            with st.form("add_course"):
                title = st.text_input("Titre")
                weekday = st.selectbox("Jour", list(range(5)), format_func=lambda x:get_weekdays()[x])
                start = st.text_input("Heure début (HH:MM)")
                end = st.text_input("Heure fin (HH:MM)")
                cap = st.number_input("Capacité",1,50,10)
                if st.form_submit_button("Créer le cours"):
                    newc = CourseSlot(title=title,weekday=weekday,start_time=start,end_time=end,capacity=cap)
                    db.add(newc)
                    db.commit()
                    st.success("Cours ajouté")
                    st.rerun()

        # Modifier / Supprimer un cours
        with st.expander("Modifier / Supprimer un cours"):
            if courses:
                course_sel = st.selectbox("Sélectionner un cours", courses, format_func=lambda c: f"{c.title} ({get_weekdays()[c.weekday]} {c.start_time}-{c.end_time})")
                if course_sel:
                    with st.form(f"edit_course_{course_sel.id}"):
                        title = st.text_input("Titre", value=course_sel.title)
                        weekday = st.selectbox("Jour", list(range(5)), index=course_sel.weekday, format_func=lambda x:get_weekdays()[x])
                        start = st.text_input("Heure début", value=course_sel.start_time)
                        end = st.text_input("Heure fin", value=course_sel.end_time)
                        cap = st.number_input("Capacité",1,50,course_sel.capacity)
                        edit = st.form_submit_button("Modifier")
                        delete = st.form_submit_button("Supprimer")
                        
                        if edit:
                            course_sel.title = title
                            course_sel.weekday = weekday
                            course_sel.start_time = start
                            course_sel.end_time = end
                            course_sel.capacity = cap
                            db.commit()
                            st.success("Cours modifié")
                            st.rerun()

                        if delete:
                            db.delete(course_sel)
                            db.commit()
                            st.success("Cours supprimé")
                            st.rerun()
            else:
                st.info("Aucun cours trouvé")

# -------------------------
# Main
# -------------------------
user = get_current_user()

tabs = st.tabs(["Connexion","Utilisateur","Coach","Admin"])

with tabs[0]:
    if not user:
        login_ui()
    else:
        st.info(f"Connecté en tant que {user.nom} ({user.email}) - rôle: {user.role}")
        if st.button("Se déconnecter"):
            st.session_state.clear()
            st.rerun()

with tabs[1]:
    if user and user.role in ["user","admin"]:
        user_view(user)
    else:
        st.warning("Accès réservé aux utilisateurs")

with tabs[2]:
    if user and user.role in ["coach","admin"]:
        coach_view()
    else:
        st.warning("Accès réservé aux coachs")

with tabs[3]:
    if user and user.role=="admin":
        admin_view()
    else:
        st.warning("Accès réservé aux admins")
