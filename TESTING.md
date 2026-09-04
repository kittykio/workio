# Testing Workio

Workio uses Django's built-in test runner and Coverage.py. The suite contains app-local tests plus cross-app regression tests and currently covers the `accounts`, `projects`, `billing`, `conversations`, and `notifications` applications.

## Setup

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Using `python -m ...` ensures commands use the interpreter and packages from the active virtual environment.

## Run all tests

```bash
python manage.py test
```

Django creates an isolated test database, applies migrations, runs the tests, and removes the database afterward. The command does not modify the development SQLite database.

For more detail, including individual test names:

```bash
python manage.py test --verbosity 2
```

## Measure coverage

Coverage must execute the tests before it can generate a report:

```bash
python -m coverage erase
python -m coverage run manage.py test
python -m coverage report -m
```

The final `TOTAL` row is the overall application coverage percentage. The `Missing` column lists uncovered line numbers. `coverage erase` prevents data from an older run from affecting the result.

To create a browsable HTML report:

```bash
python -m coverage html
```

Open `htmlcov/index.html` in a browser. The generated `htmlcov` directory should not be committed.

## Coverage scope

[`.coveragerc`](.coveragerc) measures application code in these packages:

- `accounts`
- `billing`
- `conversations`
- `notifications`
- `projects`

Migrations, Django admin registration, app configuration, and test modules are excluded. These are framework wiring or generated code and would otherwise distort the percentage. Models, forms, views, services, context processors, management commands, and URL modules remain included.

The project target is greater than 90% total application coverage. Coverage is a useful signal, but new tests should assert behavior, permissions, validation, state changes, and side effects rather than only executing lines.

## Test organization

Each Django application has a local test module:

- `accounts/tests.py`: signup, profiles, account settings, portfolios, reviews, authentication, and dashboard behavior.
- `projects/tests.py`: project permissions, invitations, tasks, milestones, comments, and activity history.
- `billing/tests.py`: time entries, invoices, billing filters, status transitions, and ownership rules.
- `conversations/tests.py`: messaging, unread state, live feeds, and participant access.
- `notifications/tests.py`: notification ownership and email delivery preferences.
- `test_app_coverage.py`: cross-app regression, validation-boundary, file-handling, command, and integration coverage.

Tests subclass `django.test.TestCase`, so each test runs with database isolation. Shared cross-app fixtures are created by `AppCase.setUp()`.

## Run focused tests

Run one application:

```bash
python manage.py test billing
```

Run one test class:

```bash
python manage.py test projects.tests.ProjectPermissionTests
```

Run one test method:

```bash
python manage.py test projects.tests.ProjectPermissionTests.test_outsider_cannot_view_project
```

Run the cross-app suite:

```bash
python manage.py test test_app_coverage
```

Coverage can wrap any focused command, but only a full-suite run should be used when reporting the app's overall percentage.

## Writing new tests

For a new behavior, cover the relevant combination of:

1. The successful path and resulting database state.
2. Invalid input and form error messages.
3. Anonymous, participant, owner, and outsider permissions where applicable.
4. Notifications, email, redirects, file changes, or other side effects.
5. Boundary states such as draft/sent/paid invoices or submitted/approved milestones.

Prefer `reverse()` over hard-coded paths, `force_login()` for tests unrelated to authentication itself, and `TemporaryDirectory` with `override_settings(MEDIA_ROOT=...)` for uploaded files. Use Django's in-memory email outbox (`django.core.mail.outbox`) to assert email behavior.

## Troubleshooting

### `No module named coverage`

Coverage is not installed in the Python environment running the command. Activate the virtual environment and reinstall requirements:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m coverage --version
```

### `No data to report`

Run the suite through Coverage.py before requesting the report:

```bash
python -m coverage run manage.py test
python -m coverage report -m
```

### Migration-related database errors

Check that model and migration state agree:

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate
```

### A test passes alone but fails in the full suite

The test may depend on shared state, test order, the filesystem, or the email outbox. Ensure all records are created inside the test or `setUp()`, and isolate uploaded files with a temporary media directory.

## Pre-commit verification

Before committing a change, run:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python -m coverage erase
python -m coverage run manage.py test
python -m coverage report -m
```

The expected outcome is a clean Django check, no uncommitted migration changes, a fully passing suite, and total application coverage above 90%.
