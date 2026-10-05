# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Single-page Streamlit app ("Club de Boxe Reventin") for managing boxing class bookings: weekly schedule, reservations, and admin management of users and course slots. All application code lives in `app.py`; there is no separate frontend/backend split. UI text and user-facing strings are in French.

Data is stored in Supabase (Postgres), accessed via the `supabase` Python client (`supabase.table(...)`) — not an ORM. There are two tables used throughout: `users` and `courseslot`, plus a `reservation` table linking them.

## Commands

```bash
# Install deps (use a venv; one already exists at ./venv)
pip install -r requirements.txt

# Run the app locally
streamlit run app.py

# Create the initial admin user (admin@example.com / admin1234)
python create_admin.py
```

There is no test suite, linter, or build step configured in this repo.

Note: `create_admin.py` imports `engine, Base, User` from `app`, but `app.py` no longer defines these — it was written against an older SQLAlchemy ORM version of the app and is now broken against the current Supabase-client implementation. `requirements.txt` still lists `sqlalchemy` and `passlib[bcrypt]` for the same reason, even though `app.py` hashes passwords with plain `hashlib.sha256`, not passlib/bcrypt. Fix `create_admin.py` to use the `supabase` client (mirroring the insert pattern in `admin_view()`'s "Ajouter un utilisateur" form) rather than assuming these still work.

## Configuration / secrets

Local secrets go in `.streamlit/secrets.toml` (gitignored, not committed). `app.py` reads:
- `st.secrets["supabase"]["url"]` / `["key"]` — required, used to construct the Supabase client at import time.
- `st.secrets["banner"]["message"]` (or flat `LANDING_BANNER_MESSAGE`) — optional login-page banner text, falls back to the `LANDING_BANNER_MESSAGE` env var, then the empty-string constant near the top of `app.py`.
- `st.secrets["disabled_weekdays"]["days"]` (or flat `DISABLED_WEEKDAYS`) — optional comma-separated list of French weekday names (e.g. `"Lundi,Mercredi"`) to mark closed for the current week, checked in `get_disabled_weekdays()`.

On Streamlit Cloud these are set via "Manage app" → Secrets instead of the local file.

A GitHub Actions workflow (`.github/workflows/reset.yml`) runs every Saturday at 00:00 UTC (and can be triggered manually) to POST to a Supabase Edge Function (`reset_my_table`) using `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_URL` repo secrets — this is the weekly reservation reset, external to `app.py`.

## Architecture of app.py

The whole file executes top-to-bottom on every Streamlit rerun (standard Streamlit model — there's no routing/session machinery beyond `st.session_state`). Structure, in order:

1. **Page config & CSS** — `st.set_page_config`, injected `<style>` block, logo/header.
2. **Supabase client init** — module-level `supabase` client built from secrets; every DB call in the file goes through this one object.
3. **Helpers** (roughly grouped by comment banners):
   - Auth: `hash_password`/`verify_password` (SHA-256), `login_user`, `get_current_user` (reads `st.session_state["user_id"]`).
   - Calendar/rules: `get_weekdays()` (Mon–Fri only, no weekend classes), `is_bank_holiday_fr()` (French fixed + Easter-relative holidays), `get_current_week_and_year()` (ISO week; rolls Sat/Sun forward to next Monday's week), `is_reservation_allowed()` (core booking-window rule: can't book past days in the current week, same-day changes allowed until 1h before the course's start time, Sat/Sun always allows booking into *next* week).
   - Config-from-secrets: `get_landing_banner_message()`, `get_disabled_weekdays()`.
4. **Role-based views**, each a function taking the current user (or none) and rendering with `st.tabs`/`st.form`:
   - `login_ui()` — email/password form, sets `session_state["user_id"]`/`["role"]` on success.
   - `user_view(user)` — weekly schedule tab (booking/cancel per `courseslot`, filtered by `disabled_weekdays` and, if `user["gym_douce_only"]`, to "gym douce" titles only) + account tab (password change).
   - `coach_view()` — read-only weekly roster with reservation counts and an expander listing attendees per slot.
   - `admin_view()` — full CRUD on `users` and `courseslot` via paired "Ajouter" / "Modifier / Supprimer" expanders, each wrapping an `st.form`.
5. **Main** — computes `user = get_current_user()`, then renders four top-level `st.tabs` (Connexion / Utilisateur / Coach / Admin), gating each on `user["role"]`.

### Key domain rules to preserve when editing

- Reservation capacity, waitlist status, and "already booked" checks are always scoped by `(course_id, week_num, year)` — bookings are per ISO week, not open-ended, and cancelled rows (`cancelled=True`) are excluded from counts rather than deleted.
- A user's weekly booking limit is `user["formula"]` (an integer set by admins), checked against non-waitlisted, non-cancelled reservations for the current week only.
- `is_reservation_allowed()` is the single source of truth for whether booking/cancelling a given weekday+time is currently permitted — reuse it rather than re-deriving the cutoff logic.
- Admin forms for editing/deleting a user or course slot live inside one `st.form` with two submit buttons (`update_btn`/`delete_btn`); when adding fields to these forms, keep both branches in sync.
