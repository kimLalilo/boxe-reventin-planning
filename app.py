import streamlit as st
from supabase import create_client, Client
import hashlib
import pandas as pd
import datetime
import pendulum

# Définir le fuseau horaire
tz = pendulum.timezone("Europe/Paris")
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
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["key"]
supabase = create_client(supabase_url, supabase_key)

# -------------------------
# Helpers
# -------------------------
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_password(pw, hashed):
    return hash_password(pw) == hashed

def get_weekdays():
    return ["Lundi","Mardi","Mercredi","Jeudi","Vendredi"]

def is_bank_holiday_fr(date):
    """
    Return True if the given date (datetime.date or datetime.datetime) is a French bank holiday.
    """
    if isinstance(date, datetime.datetime):
        date = date.date()
    year = date.year

    # Fixed-date holidays
    fixed = [
        (1, 1),    # New Year's Day
        (5, 1),    # Labour Day
        (5, 8),    # Victory in Europe Day
        (7, 14),   # Bastille Day
        (8, 15),   # Assumption of Mary
        (11, 1),   # All Saints' Day
        (11, 11),  # Armistice Day
        (12, 25),  # Christmas
    ]
    if (date.month, date.day) in fixed:
        return True

    # Compute Easter Monday, Ascension, Pentecost Monday
    def easter_date(y):
        "Returns Easter as a date object."
        a = y // 100
        b = y % 100
        c = (3 * (a + 25)) // 4
        d = (3 * (a + 25)) % 4
        e = (8 * (a + 11)) // 25
        f = (5 * a + b) % 19
        g = (19 * f + c - e) % 30
        h = (f + 11 * g) // 319
        j = (60 * (5 - d) + b) // 4
        k = (60 * (5 - d) + b) % 4
        m = (g - h + j + k) % 7
        n = (g - h + j + k + 114) // 31
        p = (g - h + j + k + 114) % 31
        return datetime.date(y, n, p + 1)

    easter = easter_date(year)
    holidays = [
        easter + datetime.timedelta(days=1),   # Easter Monday
        easter + datetime.timedelta(days=39),  # Ascension
        easter + datetime.timedelta(days=50),  # Pentecost Monday
    ]


def get_current_week_and_year():
    now = pendulum.now(tz)

    # If today is Saturday or Sunday, shift to next Monday
    if now.weekday() in [5, 6]:
        days_until_monday = 7 - now.weekday()
        next_monday = now + datetime.timedelta(days=days_until_monday)
        iso_info = next_monday.isocalendar()
    else:
        iso_info = now.isocalendar()

    # iso_info = (ISO_year, ISO_week, ISO_weekday)
    return iso_info[1], iso_info[0]

# -------------------------
# Users
# -------------------------
def get_user_by_email(email):
    resp = supabase.table("users").select("*").eq("email", email).execute()
    return resp.data[0] if resp.data else None

def get_current_user():
    if "user_id" in st.session_state:
        resp = supabase.table("users").select("*").eq("id", st.session_state["user_id"]).execute()
        return resp.data[0] if resp.data else None
    return None

def login_user(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user["password"]):
        st.session_state["user_id"] = user["id"]
        st.session_state["role"] = user["role"]
        return True
    return False

def is_reservation_allowed(weekday, start_time):
    now = pendulum.now(tz)
    current_weekday = now.weekday()  # 0 = Monday, 6 = Sunday

    # print(f"DEBUG: weekday = {weekday}, current_weekday = {current_weekday}")

    # --- NEXT WEEK SAT & SUN RULE ---
    # If user selects Saturday (5) or Sunday (6), allow booking for *next* week
    if current_weekday in [5, 6]:
        return True

    # --- SAME WEEK RULES ---
    # If course is on a future day (Mon–Fri), reservation is allowed
    if weekday > current_weekday:
        return True

    # If course is on a past day of the week, reservation is not allowed
    if weekday < current_weekday:
        return False

    # If course is today, check if it's at least 2 hours away
    course_time_parts = start_time.split(':')
    course_hour = int(course_time_parts[0])
    course_minute = int(course_time_parts[1]) if len(course_time_parts) > 1 else 0

    course_datetime = now.replace(hour=course_hour, minute=course_minute, second=0, microsecond=0)
    time_difference = (course_datetime - now).total_seconds() / 3600  # difference in hours

    # Allow booking/cancellation only if course is at least 2 hours away and hasn't started yet
    # print(f"DEBUG: now = {now}, course_datetime = {course_datetime}, time_difference = {time_difference}")
    if now < course_datetime:
        return time_difference >= 2
    else:
        return False

# -------------------------
# UI Connexion
# -------------------------
def login_ui():
    with st.form("login_form"):
        email = (st.text_input("Email") or "").strip().lower()
        pw = (st.text_input("Mot de passe", type="password") or "").strip()
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
def user_view(user):
    tabs = st.tabs(["Planning hebdo", "Mon compte"])

    # Planning
    with tabs[0]:
        st.subheader("Planning de la semaine (Lundi - Vendredi)")
        weekdays = get_weekdays()
        cols = st.columns(len(weekdays))
        for idx, day in enumerate(weekdays):
            with cols[idx]:
                st.markdown(f"### {day}")
                slots = supabase.table("courseslot").select("*").eq("weekday", idx).order("start_time").execute().data
                target_week, current_year = get_current_week_and_year()
                if user.get("gym_douce_only", False):
                    slots = [s for s in slots if "gym douce" in s["title"].lower()]
                for slot in slots:
                    count_res = supabase.table("reservation").select("id", count="exact") \
                        .eq("course_id", slot["id"]).eq("cancelled", False).eq("waitlist", False).eq("week_num", target_week).eq("year", current_year).execute().count
                    dispo = slot["capacity"] - count_res
                    st.markdown(f"**{slot['title']} ({slot['start_time']}-{slot['end_time']})**")
                    st.write(f"Places restantes : {dispo}")

                    already = supabase.table("reservation").select("*") \
                        .eq("user_id", user["id"]) \
                        .eq("course_id", slot["id"]) \
                        .eq("cancelled", False) \
                        .eq("week_num", target_week) \
                        .eq("year", current_year) \
                        .execute().data

                    with st.form(f"res_{slot['id']}"):
                        if already:
                            current_weekday = pendulum.now(tz).weekday()
                            is_past_day = idx < current_weekday
                            # print(f"DEBUG Cancel: idx={idx}, current_weekday={current_weekday}, is_past_day={is_past_day}")

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
                                if is_reservation_allowed(idx, slot["start_time"]):
                                    supabase.table("reservation").update({"cancelled": True}).eq("id", already[0]["id"]).execute()
                                    st.success("Réservation annulée")
                                    st.rerun()
                                else:
                                    st.info("Cours déjà passé ou dans moins d'2h - Annulation impossible")
                            
                        else:
                            if dispo > 0:
                                reserve = st.form_submit_button("Réserver")
                                if reserve:
                                    week_num, year = get_current_week_and_year()
                                    week_res = supabase.table("reservation").select("id", count="exact") \
                                        .eq("user_id", user["id"]).eq("cancelled", False).eq("waitlist", False).eq("week_num", week_num).eq("year", year).execute().count

                                    if is_reservation_allowed(idx, slot["start_time"]):
                                        if week_res < user["formula"]:
                                            # Construire la date du cours
                                            slot_date = datetime.date.fromisocalendar(year, week_num, slot['weekday'] + 1)
                                            # Vérifier si c'est un jour férié
                                            if is_bank_holiday_fr(slot_date):
                                                st.error("Impossible de réserver : ce jour est un jour férié.")
                                                st.rerun()
                                            supabase.table("reservation").insert({
                                                "user_id": user["id"],
                                                "course_id": slot["id"],
                                                "waitlist": False,
                                                "cancelled": False,
                                                "week_num": week_num,
                                                "year": year
                                            }).execute()

                                            st.success("Réservation confirmée")
                                            st.rerun()
                                        else:
                                            st.error("Limite de réservations atteinte pour votre formule.")
                                    else:
                                        st.error("Réservations fermées pour ce cours (cours dans moins de 2h).")
                            else:
                                wait = st.form_submit_button("Cours complet - Liste d'attente")
                                if wait:
                                    week_num, year = get_current_week_and_year()
                                    supabase.table("reservation").insert({
                                        "user_id": user["id"],
                                        "course_id": slot["id"],
                                        "waitlist": True,
                                        "cancelled": False,
                                        "week_num": week_num,
                                        "year": year
                                    }).execute()
                                    st.success("Inscrit sur liste d'attente")
                                    st.rerun()

    # Mon compte
    with tabs[1]:
        st.subheader("Mon compte")
        with st.form("pw_change"):
            new_pw = st.text_input("Nouveau mot de passe", type="password")
            submit_pw = st.form_submit_button("Changer")
            if submit_pw and new_pw:
                supabase.table("users").update({"password": hash_password(new_pw)}).eq("id", user["id"]).execute()
                st.success("Mot de passe modifié")

# -------------------------
# UI Coach
# -------------------------
def coach_view():
    st.subheader("Planning coach")
    weekdays = get_weekdays()
    cols = st.columns(len(weekdays))
    for idx, day in enumerate(weekdays):
        with cols[idx]:
            st.markdown(f"### {day}")
            target_week, target_year = get_current_week_and_year()
            slots = supabase.table("courseslot").select("*").eq("weekday", idx).order("start_time").execute().data
            for slot in slots:
                count_res = supabase.table("reservation").select("id", count="exact") \
                    .eq("course_id", slot["id"]).eq("cancelled", False).eq("waitlist", False).eq("week_num", target_week).eq("year", target_year).execute().count
                wait_count = supabase.table("reservation").select("id", count="exact") \
                    .eq("course_id", slot["id"]).eq("cancelled", False).eq("waitlist", True).eq("week_num", target_week).eq("year", target_year).execute().count
                st.markdown(f"**{slot['title']}** ({slot['start_time']}-{slot['end_time']})")
                if count_res == 0:
                    st.markdown(f"<span style='color:red'>{count_res}/{slot['capacity']} réservés</span>", unsafe_allow_html=True)
                else:
                    st.write(f"{count_res}/{slot['capacity']} réservés")
                if count_res + wait_count > 0:
                    with st.expander(f"Voir utilisateurs ({count_res})"):

                        res = supabase.table("reservation").select("*, users(*)") \
                            .eq("course_id", slot["id"]) \
                            .eq("cancelled", False) \
                            .eq("week_num", target_week) \
                            .eq("year", target_year) \
                            .execute().data
                        user_lines = []
                        for r in res:
                            user_name = r['users']['nom'] if 'users' in r and r['users'] else "Inconnu"
                            waitlist = " (liste d'attente)" if r.get('waitlist', False) else ""
                            st.markdown(f"- {user_name}{waitlist}")

# -------------------------
# UI Admin
# -------------------------
def admin_view():
    st.subheader("Administration")
    tabs = st.tabs(["Utilisateurs", "Cours"])

    # Utilisateurs
    with tabs[0]:
        st.subheader("Gestion des utilisateurs")
        users = supabase.table("users").select("*").execute().data
        df_users = pd.DataFrame(users)
        # Drop the password column to avoid displaying sensitive information
        df_users = df_users.drop(columns=['password'], errors='ignore')
        st.dataframe(df_users)

        with st.expander("Ajouter un utilisateur"):
            with st.form("add_user"):
                nom = st.text_input("Nom")
                email = st.text_input("Email")
                pw = st.text_input("Mot de passe", type="password")
                role = st.selectbox("Rôle", ["user","coach","admin"])
                formula = st.number_input("Formule (nb cours)",1,5,1)
                gym_douce_only = st.checkbox("Accès uniquement Gym Douce", value=False)
                if st.form_submit_button("Créer"):
                    if get_user_by_email(email):
                        st.error("Email déjà utilisé")
                    else:
                        supabase.table("users").insert({
                            "nom": nom,
                            "email": email,
                            "password": hash_password(pw),
                            "role": role,
                            "formula": formula,
                            "gym_douce_only": gym_douce_only
                        }).execute()
                        st.success("Utilisateur créé")
                        st.rerun()

        # --- Modifier / Supprimer utilisateur ---
        with st.expander("✏️ Modifier / Supprimer un utilisateur"):
            user_ids = {u["nom"]: u["id"] for u in users}
            if user_ids:
                selected = st.selectbox("Choisir un utilisateur", list(user_ids.keys()))
                user_id = user_ids[selected]
                user_data = next(u for u in users if u["id"] == user_id)

                with st.form("edit_user"):
                    nom = st.text_input("Nom", user_data["nom"])
                    email = st.text_input("Email", user_data["email"])
                    role = st.selectbox("Rôle", ["user","coach","admin"], index=["user","coach","admin"].index(user_data["role"]))
                    formula = st.number_input("Formule (nb cours)", 1, 5, user_data["formula"])
                    gym_douce_only = st.checkbox("Accès uniquement Gym Douce", value=user_data.get("gym_douce_only", False))
                    update_btn = st.form_submit_button("💾 Sauvegarder")
                    delete_btn = st.form_submit_button("🗑️ Supprimer")

                    if update_btn:
                        supabase.table("users").update({
                            "nom": nom,
                            "email": email,
                            "role": role,
                            "formula": formula,
                            "gym_douce_only": gym_douce_only
                        }).eq("id", user_id).execute()
                        st.success("Utilisateur mis à jour")
                        st.rerun()

                    if delete_btn:
                        supabase.table("users").delete().eq("id", user_id).execute()
                        st.success("Utilisateur supprimé")
                        st.rerun()

    # Cours
    with tabs[1]:
        st.subheader("Gestion des cours")
        courses = supabase.table("courseslot").select("*").execute().data
        df_courses = pd.DataFrame(courses)
        st.dataframe(df_courses)

        with st.expander("Ajouter un cours"):
            with st.form("add_course"):
                title = st.text_input("Titre")
                weekday = st.selectbox("Jour", list(range(5)), format_func=lambda x:get_weekdays()[x])
                start = st.text_input("Heure début (HH:MM)")
                end = st.text_input("Heure fin (HH:MM)")
                cap = st.number_input("Capacité",1,50,10)
                if st.form_submit_button("Créer le cours"):
                    supabase.table("courseslot").insert({
                        "title": title,
                        "weekday": weekday,
                        "start_time": start,
                        "end_time": end,
                        "capacity": cap
                    }).execute()
                    st.success("Cours ajouté")
                    st.rerun()

        # --- Modifier / Supprimer un cours ---
        with st.expander("✏️ Modifier / Supprimer un cours"):
            course_ids = {c["title"]: c["id"] for c in courses}
            if course_ids:
                selected = st.selectbox("Choisir un cours", list(course_ids.keys()))
                course_id = course_ids[selected]
                course_data = next(c for c in courses if c["id"] == course_id)

                with st.form("edit_course"):
                    title = st.text_input("Titre", course_data["title"])
                    weekday = st.selectbox("Jour", list(range(5)), index=course_data["weekday"], format_func=lambda x:get_weekdays()[x])
                    start = st.text_input("Heure début (HH:MM)", course_data["start_time"])
                    end = st.text_input("Heure fin (HH:MM)", course_data["end_time"])
                    cap = st.number_input("Capacité",1,50,course_data["capacity"])
                    update_btn = st.form_submit_button("💾 Sauvegarder")
                    delete_btn = st.form_submit_button("🗑️ Supprimer")

                    if update_btn:
                        supabase.table("courseslot").update({
                            "title": title,
                            "weekday": weekday,
                            "start_time": start,
                            "end_time": end,
                            "capacity": cap
                        }).eq("id", course_id).execute()
                        st.success("Cours mis à jour")
                        st.rerun()

                    if delete_btn:
                        supabase.table("courseslot").delete().eq("id", course_id).execute()
                        st.success("Cours supprimé")
                        st.rerun()

# -------------------------
# Main
# -------------------------
user = get_current_user()

tabs = st.tabs(["Connexion","Utilisateur","Coach","Admin"])

with tabs[0]:
    if not user:
        login_ui()
    else:
        st.info(f"Connecté en tant que {user['nom']} ({user['email']}) - rôle: {user['role']}")
        if st.button("Se déconnecter"):
            st.session_state.clear()
            st.rerun()

with tabs[1]:
    if user and user["role"] in ["user","admin"]:
        user_view(user)
    else:
        st.warning("Accès réservé aux utilisateurs")

with tabs[2]:
    if user and user["role"] in ["coach","admin"]:
        coach_view()
    else:
        st.warning("Accès réservé aux coachs")

with tabs[3]:
    if user and user["role"]=="admin":
        admin_view()
    else:
        st.warning("Accès réservé aux admins")
