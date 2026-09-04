# Workio

A polished Django client portal for freelancers: public profiles, collaborative projects, milestones, comments and files, private direct messages, time tracking, invoices, and live notification updates.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000`. Demo accounts:

- Freelancer: `maya` / `demo12345`
- Client: `jordan` / `demo12345`

Run tests with `python manage.py test`. See [TESTING.md](TESTING.md) for the complete testing and coverage guide.

Client invitation emails are printed in the development-server terminal. Configure an SMTP or transactional email backend before production.

SQLite keeps the local demo frictionless. Before production, move the secret key and debug setting to environment variables and switch to PostgreSQL and object storage.
