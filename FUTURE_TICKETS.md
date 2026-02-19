# Cookin' Book — Future Tickets (Timebox 2 & 3)

> **How to use this document:**
>
> 1. **Create two milestones** in your GitHub repo (Issues tab > Milestones > New milestone):
>    - `Timebox 2 — Chat & Recipe Search`
>    - `Timebox 3 — Shopping, Testing & Production`
> 2. **Create these labels** if they don't already exist:
>    `backend`, `frontend`, `database`, `API`, `security`, `infrastructure`, `testing`, `CI/CD`, `integration`, `UCP`, `data`, `admin`, `documentation`
>    *(18 issues total: 7 in Timebox 2, 11 in Timebox 3)*
> 3. **For each issue below**, click "New Issue" in GitHub, then:
>    - Copy the **Title** line into the issue title field
>    - Copy everything from **Description** through **Key Files** into the issue body
>    - Assign the **Milestone** and **Labels** noted at the top of each issue
> 4. Issues are ordered by dependency — earlier issues should generally be completed first

---

# Timebox 2 — Chat & Recipe Search

**Milestone Goal:** A logged-in user can type in the chat, receive AI-generated responses with real recipe data, and view their past conversation history.

---

## Issue 1

**Title:** Generate database migrations and resolve User model conflict

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `backend`, `database`

### Description

The six models in `main/models.py` have never been migrated — the `migrations/` directory contains only `__init__.py`. Additionally, the custom `User` model (with its own `user_id`, `email`, `password` fields) **conflicts** with Django's built-in `django.contrib.auth.models.User` that is already used for authentication in `views.py` and `forms.py`.

The simplest fix is to remove the custom `User` class and update all foreign key references (in `ChatConversation` and `ShoppingListSession`) to point to `settings.AUTH_USER_MODEL`. All models also use manual `IntegerField(primary_key=True)` which should be switched to `AutoField` or removed so Django auto-generates IDs.

### Acceptance Criteria

- [ ] The custom `User` class in `main/models.py` is removed
- [ ] All FK fields in `ChatConversation` and `ShoppingListSession` reference `settings.AUTH_USER_MODEL` or `django.contrib.auth.models.User`
- [ ] Manual `IntegerField(primary_key=True)` fields are switched to `AutoField` (or removed to use Django's default auto `id`)
- [ ] `python manage.py makemigrations` generates migration files without errors
- [ ] `python manage.py migrate` applies all migrations successfully
- [ ] All models are importable and can be created via the Django shell or admin

### Dependencies

None — this is a **prerequisite** for most other Timebox 2 and 3 issues.

### Key Files

- `CookinBook/main/models.py`
- `CookinBook/main/migrations/`
- `CookinBook/CookinBook/settings.py`

---

## Issue 2

**Title:** Create API endpoint for sending chat messages and receiving Gemini responses

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `backend`, `API`

### Description

There is currently no way for the frontend to communicate with the `CookinBookBot` wrapper. The `chat_view` in `views.py` simply renders a static template with no backend logic. Create a Django view (e.g., at `/api/chat/send/`) that accepts POST requests with a user message, passes it to `CookinBookBot.send_message()`, persists both the user message and bot response as `ChatMessage` records tied to a `ChatConversation`, and returns the bot response as JSON.

### Acceptance Criteria

- [ ] A new URL pattern exists (e.g., `api/chat/send/`) mapped to a view function
- [ ] The view accepts POST requests with JSON body: `{"message": "...", "conversation_id": ...}`
- [ ] If no `conversation_id` is provided, a new `ChatConversation` is created for the authenticated user
- [ ] If a `conversation_id` is provided, the existing conversation is continued
- [ ] Both user message and bot response are saved as `ChatMessage` records with correct `sender` values (`"U"` and `"B"`)
- [ ] The view returns JSON: `{"response": "...", "conversation_id": ...}`
- [ ] Unauthenticated requests return 401 or 403
- [ ] CSRF is handled properly (via `X-CSRFToken` header or `@csrf_exempt` with alternative auth)
- [ ] Gemini API errors are caught and returned as JSON error responses (not raw tracebacks)

### Dependencies

- **Issue 1** (needs working database tables for `ChatConversation` and `ChatMessage`)

### Key Files

- `CookinBook/main/views.py`
- `CookinBook/main/urls.py`
- `CookinBook/gemini_wrapper/client.py`

---

## Issue 3

**Title:** Replace chat landing page with a functional chat interface

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `frontend`

### Description

The current `chat.html` template is a hero/landing page with a "Get Started" button and **no chat functionality**. Replace it with a proper chat interface that includes a message input area, a send button, and a scrollable message history panel. Write JavaScript using the native `fetch()` API to send messages to the chat API endpoint and render responses.

**Note:** The base template loads `jquery-3.3.1.slim.min.js` which does **not** support `$.ajax()` — use the native `fetch()` API instead.

### Acceptance Criteria

- [ ] The chat page displays a message input field and a send button at the bottom
- [ ] A scrollable area above the input shows the conversation history
- [ ] User messages appear visually distinct from bot messages (e.g., right-aligned vs left-aligned, different colors)
- [ ] Pressing Enter or clicking Send dispatches the message to the API and displays it immediately
- [ ] A loading indicator is shown while waiting for the bot response
- [ ] The bot response is rendered when it arrives
- [ ] The CSRF token is included in fetch requests (extracted from cookie or template variable)
- [ ] The interface is responsive and consistent with Bootstrap 4.3.1 styling and `theme.css` variables
- [ ] Unauthenticated users are redirected to login or shown the landing content

### Dependencies

- **Issue 2** (needs the chat API endpoint to send messages to)

### Key Files

- `CookinBook/main/templates/main/chat/chat.html`
- `CookinBook/main/templates/main/chat/static/chat.css`
- `CookinBook/main/templates/main/base/static/base.js` (or create a new `chat.js`)

---

## Issue 4

**Title:** Populate the history page with past conversations from the database

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `backend`, `frontend`

### Description

The history page at `/history/` currently renders a template with just `<h1>History</h1>`, and the `history_view` function passes no context data. Update the view to query all `ChatConversation` records for the authenticated user and update the template to list conversations with timestamps, a preview, and a way to resume them in the chat page.

### Acceptance Criteria

- [ ] `history_view` requires login (`@login_required`) and redirects unauthenticated users to `/login/`
- [ ] The view queries `ChatConversation` objects filtered by current user, ordered by most recent first
- [ ] Each conversation entry shows: timestamp (`started_at` or `updated_at`), first user message preview (truncated), and message count
- [ ] Clicking a conversation navigates to `/chat/?conversation_id=<id>` to load that conversation
- [ ] The chat page, when receiving a `conversation_id` parameter, loads and displays existing messages
- [ ] An empty state message is shown when the user has no conversations
- [ ] The design is consistent with existing Bootstrap styling

### Dependencies

- **Issue 1** (database), **Issue 2** (chat API), **Issue 3** (chat UI)

### Key Files

- `CookinBook/main/views.py` — `history_view`
- `CookinBook/main/templates/main/history/history.html`
- `CookinBook/main/templates/main/chat/chat.html` (for loading existing conversations)

---

## Issue 5

**Title:** Replace mock recipe search with a real data source

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `backend`, `data`

### Description

The `search_recipes()` function in `gemini_wrapper/client.py` returns hardcoded taco recipes or a generic placeholder for any query. Replace this with a real data source. Two possible approaches:

1. **Quick path:** Create a JSON fixture file with 20-30+ recipes and search via Django ORM text matching
2. **Full path:** Integrate `elasticsearch-dsl` / `django-elasticsearch-dsl` for proper full-text search

Either way, the function signature and return format must remain compatible with Gemini's tool-calling interface.

### Acceptance Criteria

- [ ] `search_recipes()` returns real, varied recipe data (not hardcoded for "taco" only)
- [ ] A recipe data source exists: JSON fixture with 20-30+ recipes, DB-seeded `Recipe` records, or an Elasticsearch index
- [ ] Search actually filters based on the `query` parameter (title matching, ingredient matching, or full-text)
- [ ] Return format remains a list of dicts with `id`, `title`, and `ingredients` keys (Gemini tool-calling compatibility)
- [ ] If using Elasticsearch: `elasticsearch-dsl` added to `requirements.txt` and connection settings in `settings.py`
- [ ] If using Django ORM: the approach is documented so it can be swapped for Elasticsearch later
- [ ] `README.md` updated with any new setup steps (data seeding, Elasticsearch setup, etc.)

### Dependencies

- **Issue 1** (if using DB-seeded recipes)

### Key Files

- `CookinBook/gemini_wrapper/client.py` — `search_recipes()`
- `CookinBook/requirements.txt`
- `CookinBook/CookinBook/settings.py` (if adding Elasticsearch config)

---

## Issue 6

**Title:** Add `@login_required` guards and configure `LOGIN_URL`

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `backend`, `security`

### Description

Currently, `chat_view`, `history_view`, and `profile_view` in `views.py` do not check whether the user is authenticated. Any anonymous visitor can access all pages. Add Django's `@login_required` decorator to protected views and set `LOGIN_URL` in `settings.py`.

### Acceptance Criteria

- [ ] `history_view` and `profile_view` are decorated with `@login_required`
- [ ] `LOGIN_URL = "/login/"` is set in `settings.py`
- [ ] Visiting `/history/` or `/profile/` while logged out redirects to `/login/?next=<original_url>`
- [ ] After logging in via redirect, the user is sent to the page they originally requested (via `next` parameter)
- [ ] `chat_view` either requires login or conditionally shows landing vs. chat based on auth state

### Dependencies

None

### Key Files

- `CookinBook/main/views.py`
- `CookinBook/CookinBook/settings.py`

---

## Issue 7

**Title:** Add test runner to GitHub Actions CI pipeline

**Milestone:** Timebox 2 — Chat & Recipe Search
**Labels:** `infrastructure`, `CI/CD`, `testing`

### Description

The GitHub Actions workflow (`.github/workflows/lint.yml`) only runs Ruff lint and format checks. There is no step that runs the test suite. Add a job or step that installs dependencies and runs `python manage.py test`. This ensures tests are validated on every PR once they exist.

### Acceptance Criteria

- [ ] The GitHub Actions workflow includes a step that runs `python manage.py test` (or `pytest`)
- [ ] The step installs Python and project dependencies from `requirements.txt`
- [ ] At least one trivial passing test is added to `main/tests.py` to verify the runner works (e.g., `test_login_page_returns_200`)
- [ ] The workflow still runs Ruff checks as before (no regression)
- [ ] The job uses an appropriate Python version matching the team's dev environment

### Dependencies

None

### Key Files

- `.github/workflows/lint.yml`
- `CookinBook/main/tests.py`

---

# Timebox 3 — Shopping, Testing & Production

**Milestone Goal:** Users can generate shopping lists from recipes, execute purchases via UCP, track order status, and the application is tested, containerized, and hardened for deployment.

---

## Issue 8

**Title:** Create shopping list views and UI

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `frontend`

### Description

The `ShoppingListSession` and `ShoppingListItem` models exist in `models.py` but there are no views, URLs, or templates for shopping list functionality. Create a shopping list page where users can view ingredients, adjust quantities, remove items, and see estimated costs. Add a navigation link in the navbar.

### Acceptance Criteria

- [ ] New URL pattern exists (e.g., `/shopping/` and `/shopping/<session_id>/`)
- [ ] View is protected with `@login_required`
- [ ] Template displays `ShoppingListItem` records grouped by recipe: ingredient name, quantity, unit, retailer, price
- [ ] Total cost is calculated and displayed
- [ ] Users can remove individual items (via AJAX or form POST)
- [ ] Users can adjust item quantities
- [ ] A "Shopping List" link is added to the navbar in `base.html` (visible only when authenticated)
- [ ] Empty state message shown when no shopping list exists
- [ ] Design consistent with existing Bootstrap styling and theme variables

### Dependencies

- **Issue 1** (database migrations must be complete from Timebox 2)

### Key Files

- `CookinBook/main/views.py`
- `CookinBook/main/urls.py`
- New template: `CookinBook/main/templates/main/shopping/shopping.html`
- `CookinBook/main/templates/main/base/base.html` (navbar update)

---

## Issue 9

**Title:** Connect shopping list creation to the chat flow

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `integration`

### Description

After the Gemini bot suggests recipes with ingredients, the user should be able to say "add these to my shopping list" in the chat. The bot (via Gemini tool-calling) should create a `ShoppingListSession` and populate it with `ShoppingListItem` records. This requires adding a new tool function to the Gemini wrapper.

### Acceptance Criteria

- [ ] A new tool function `create_shopping_list(recipe_id, ingredients)` (or similar) is defined in `client.py`
- [ ] The function is registered with the Gemini chat session alongside `search_recipes` and `execute_purchase`
- [ ] When the user asks to add ingredients to a shopping list, Gemini calls this function
- [ ] The function creates a `ShoppingListSession` (status `"NS"`) and associated `ShoppingListItem` records
- [ ] The bot confirms creation and directs the user to view the shopping list
- [ ] If a session already exists for the conversation, items are added to it (no duplicates)
- [ ] Handles missing or malformed ingredient data gracefully

### Dependencies

- **Issue 2** (chat API from Timebox 2), **Issue 8** (shopping list views)

### Key Files

- `CookinBook/gemini_wrapper/client.py`
- `CookinBook/main/views.py` (may need a helper for creating shopping list records)

---

## Issue 10

**Title:** Replace mock `execute_purchase()` with real UCP integration

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `integration`, `UCP`

### Description

The `execute_purchase()` function in `client.py` returns a hardcoded success response with a fake transaction ID (`TX-UCP-77821`). Replace with actual UCP API calls. If the UCP API is not yet available, implement a realistic configurable mock behind an environment variable toggle (`UCP_MOCK_MODE`).

### Acceptance Criteria

- [ ] `execute_purchase()` calls a real UCP endpoint OR a configurable mock with realistic behavior (success, failure, timeout scenarios)
- [ ] The function accepts structured item data (quantities, units, retailers) — not just `list[str]`
- [ ] Success responses update `ShoppingListSession.order_status` to `"OF"` (OrderFinalized)
- [ ] Failure responses are handled gracefully with user-facing error messages
- [ ] `UCP_API_URL` and `UCP_API_KEY` (or equivalent) are configurable via environment variables
- [ ] `.env.example` is updated with UCP-related variables
- [ ] Mode is toggled via `UCP_MOCK_MODE=true/false` environment variable
- [ ] The Gemini tool-calling interface still works with the updated function

### Dependencies

- **Issue 8** (shopping list must exist to purchase from)

### Key Files

- `CookinBook/gemini_wrapper/client.py` — `execute_purchase()`
- `CookinBook/CookinBook/settings.py`
- `CookinBook/.env.example`

---

## Issue 11

**Title:** Write unit and integration tests for core features

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `testing`, `backend`

### Description

`main/tests.py` is completely empty — the project has zero test coverage. Write comprehensive tests covering models, views, the chat API, authentication flows, and the Gemini wrapper (mocked). Use Django's `TestCase` and `Client` classes, and `unittest.mock.patch` for external services.

### Acceptance Criteria

- [ ] **Model tests:** `ChatConversation`, `ChatMessage`, `ShoppingListSession`, `ShoppingListItem` can be created and FK relationships work
- [ ] **View tests:** Each page returns correct HTTP status (200 for authenticated, 302 redirect for anonymous on protected pages)
- [ ] **Auth tests:** Login, signup, and logout flows work end-to-end via Django test `Client`
- [ ] **Chat API tests:** Valid POST creates messages in DB and returns expected JSON; unauthenticated requests are rejected
- [ ] **Gemini wrapper tests:** `CookinBookBot.send_message()` tested with mocked `genai.Client` via `unittest.mock.patch`
- [ ] All tests pass with `python manage.py test`
- [ ] Coverage spans: `models.py`, `views.py`, `client.py`, `forms.py`

### Dependencies

- **Issue 1** (database from Timebox 2), **Issue 2** (chat API from Timebox 2), **Issue 8** (shopping list)

### Key Files

- `CookinBook/main/tests.py`

---

## Issue 12

**Title:** Register all custom models in Django admin

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `admin`

### Description

Currently `admin.py` only customizes the built-in `User` admin display. The project's custom models (`ChatConversation`, `ChatMessage`, `Recipe`, `ShoppingListSession`, `ShoppingListItem`) are not registered, making data inspection and debugging impossible through the admin interface.

### Acceptance Criteria

- [ ] All models from `main/models.py` are registered in `admin.py`
- [ ] Each registration includes `list_display` with relevant fields
- [ ] `ChatConversation` and `ShoppingListSession` have `list_filter` configured (by user, by status)
- [ ] `search_fields` set on models with text content (`ChatMessage.content`, `ShoppingListItem.ingredient_name`)
- [ ] Admin site accessible and all models display correctly at `/admin/`

### Dependencies

- **Issue 1** (database migrations from Timebox 2)

### Key Files

- `CookinBook/main/admin.py`

---

## Issue 13

**Title:** Harden security settings for production deployment

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `infrastructure`, `security`

### Description

`settings.py` has a hardcoded `SECRET_KEY`, `DEBUG = True`, and empty `ALLOWED_HOSTS = []`. These are insecure for any deployment beyond local development. Refactor to load sensitive values from environment variables using the existing `python-dotenv` setup.

### Acceptance Criteria

- [ ] `SECRET_KEY` loaded from `SECRET_KEY` environment variable (no hardcoded fallback in production)
- [ ] `DEBUG` loaded from environment variable, defaulting to `False`
- [ ] `ALLOWED_HOSTS` loaded from environment variable (comma-separated)
- [ ] `CSRF_TRUSTED_ORIGINS` configured for proxy/domain scenarios
- [ ] `.env.example` updated with all required variables: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `GEMINI_API_KEY`, UCP keys
- [ ] Application starts successfully in both dev mode (`.env`) and with direct env vars
- [ ] No secrets appear in version-controlled files

### Dependencies

None

### Key Files

- `CookinBook/CookinBook/settings.py`
- `CookinBook/.env.example`

---

## Issue 14

**Title:** Add error handling and logging across views and Gemini wrapper

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `infrastructure`

### Description

The Gemini wrapper uses `print()` statements (`[Wrapper Log]`) and a bare `except Exception`. Views have no error handling for database failures or edge cases. Add proper Python logging and consistent error responses.

### Acceptance Criteria

- [ ] `LOGGING` configuration added to `settings.py` with console and file handlers
- [ ] `CookinBookBot` uses `logging.getLogger()` instead of `print()` (replace `[Wrapper Log]` statements)
- [ ] API endpoints return proper HTTP error codes (400, 500) with JSON error bodies
- [ ] Chat API handles: Gemini timeout, auth failure, malformed request body, DB save failure
- [ ] User-facing pages use Django `messages` framework for success/error feedback
- [ ] No raw Python tracebacks shown to end users when `DEBUG=False`

### Dependencies

- **Issue 13** (production settings)

### Key Files

- `CookinBook/CookinBook/settings.py`
- `CookinBook/gemini_wrapper/client.py`
- `CookinBook/main/views.py`

---

## Issue 15

**Title:** Update README with complete setup instructions and architecture overview

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `documentation`

### Description

The current README has minimal instructions and references Elasticsearch setup that isn't in `requirements.txt`. Update with comprehensive documentation so any new team member can get the project running.

### Acceptance Criteria

- [ ] Project description and overview included
- [ ] Prerequisites listed (Python version, system dependencies)
- [ ] Step-by-step setup: clone, venv, `pip install`, `.env` config, `makemigrations`, `migrate`, `createsuperuser`, `runserver`
- [ ] Architecture section: Django app, Gemini wrapper, recipe data source, UCP integration, and how they connect
- [ ] Developer guide: branch naming, PR process, running tests, running linter
- [ ] Outdated information corrected (e.g., Elasticsearch steps that aren't in requirements)
- [ ] Accurate for the state of the project after Timebox 3

### Dependencies

Should be done **last** in the timebox, after all features merge.

### Key Files

- `README.md`

---

## Issue 16

**Title:** Set up Elasticsearch infrastructure and recipe data ingestion pipeline

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `infrastructure`, `data`

### Description

Issue 5 (Timebox 2) gets basic recipe search working with a JSON fixture or Django ORM queries as a stopgap. However, the project's architecture (per the presentation) is built around Elasticsearch for scalable full-text recipe search. This issue sets up the full Elasticsearch infrastructure: a running ES instance (via Docker), index configuration with proper mappings for recipe fields, a data ingestion pipeline to load recipes from an external source (public recipe API, scraped dataset, or curated CSV/JSON), and updates `search_recipes()` to query Elasticsearch instead of the ORM.

### Acceptance Criteria

- [ ] A `docker-compose.yml` includes an Elasticsearch service (or ES is added to the existing compose file from Issue 18)
- [ ] An Elasticsearch index is defined with proper field mappings: `title` (text, analyzed), `ingredients` (text/keyword), `instructions` (text), `cuisine` (keyword), `prep_time` (integer)
- [ ] `elasticsearch-dsl` and/or `django-elasticsearch-dsl` are added to `requirements.txt`
- [ ] ES connection settings are configured in `settings.py` via environment variable (`ELASTICSEARCH_URL`)
- [ ] A management command or script (`manage.py seed_recipes` or similar) loads recipe data from a source file into the ES index
- [ ] At least 50+ recipes are included in the seed data (covering diverse cuisines and dietary types)
- [ ] `search_recipes()` in `client.py` queries the Elasticsearch index instead of hardcoded/ORM data
- [ ] Search supports fuzzy matching and ingredient-based queries
- [ ] The `Recipe` model's `elasticsearch_id` field is used to link Django records to ES documents
- [ ] `.env.example` updated with `ELASTICSEARCH_URL`
- [ ] `README.md` updated with ES setup instructions

### Dependencies

- **Issue 5** (basic recipe data source from Timebox 2 — this replaces the stopgap approach)

### Key Files

- `CookinBook/gemini_wrapper/client.py` — `search_recipes()`
- `CookinBook/CookinBook/settings.py`
- `CookinBook/requirements.txt`
- New: `docker-compose.yml` (or update existing)
- New: management command for data seeding (e.g., `CookinBook/main/management/commands/seed_recipes.py`)
- New: seed data file (e.g., `CookinBook/data/recipes.json`)

---

## Issue 17

**Title:** Add order tracking UI for post-purchase status

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `backend`, `frontend`, `UCP`

### Description

After a user executes a purchase via UCP (Issue 10), there is currently no way to check order status. The `ShoppingListSession` model already has an `ORDER_STATUS` field with values `"OF"` (OrderFinalized) and `"D"` (Delivered), but no views or UI expose this to the user. Create an order tracking page where users can see their past orders, current status, items purchased, and total cost. Optionally, if UCP provides a status-check endpoint, poll it to update order status.

### Acceptance Criteria

- [ ] New URL pattern exists (e.g., `/orders/` and `/orders/<session_id>/`)
- [ ] View is protected with `@login_required`
- [ ] Order list page shows all `ShoppingListSession` records where `order_status` is set, ordered by most recent
- [ ] Each order entry displays: date, total cost, status (OrderFinalized / Delivered), number of items
- [ ] Order detail page shows full item list: ingredient name, quantity, unit, retailer, price
- [ ] Status is displayed with visual indicators (e.g., badge colors: yellow for OrderFinalized, green for Delivered)
- [ ] An "Orders" or "My Orders" link is added to the navbar (visible when authenticated)
- [ ] Empty state shown when user has no orders
- [ ] Design consistent with existing Bootstrap styling and theme variables

### Dependencies

- **Issue 10** (UCP purchase integration — orders must exist first)

### Key Files

- `CookinBook/main/views.py`
- `CookinBook/main/urls.py`
- New template: `CookinBook/main/templates/main/orders/orders.html`
- New template: `CookinBook/main/templates/main/orders/order_detail.html`
- `CookinBook/main/templates/main/base/base.html` (navbar update)

---

## Issue 18

**Title:** Create deployment configuration with Docker and docker-compose

**Milestone:** Timebox 3 — Shopping, Testing & Production
**Labels:** `infrastructure`

### Description

There is no deployment configuration in the project. Create a `Dockerfile` for the Django application and a `docker-compose.yml` that orchestrates the app, database (PostgreSQL for production), and Elasticsearch. Include a production-ready WSGI server (Gunicorn), static file collection, and environment-based configuration. This enables the team to deploy the app to any Docker-capable hosting platform (Railway, Render, AWS ECS, etc.).

### Acceptance Criteria

- [ ] A `Dockerfile` exists at the repo root that builds the Django application
- [ ] The Dockerfile uses a multi-stage build or slim Python base image for smaller size
- [ ] Gunicorn (or uvicorn) is added to `requirements.txt` as the production WSGI/ASGI server
- [ ] A `docker-compose.yml` orchestrates: Django app, PostgreSQL database, Elasticsearch (for Issue 16)
- [ ] `docker-compose up` starts all services and the app is accessible at `localhost:8000`
- [ ] Static files are collected via `python manage.py collectstatic` in the Docker build
- [ ] `settings.py` supports PostgreSQL via `DATABASE_URL` environment variable (with SQLite fallback for local dev)
- [ ] `dj-database-url` (or equivalent) added to `requirements.txt` for database URL parsing
- [ ] `.env.example` updated with `DATABASE_URL` and any new variables
- [ ] A `.dockerignore` file excludes unnecessary files (`.git`, `__pycache__`, `.env`, `db.sqlite3`)
- [ ] `README.md` updated with Docker-based setup instructions as an alternative to manual setup

### Dependencies

None (can start immediately, but coordinates with Issue 16 for Elasticsearch in compose)

### Key Files

- New: `Dockerfile`
- New: `docker-compose.yml`
- New: `.dockerignore`
- `CookinBook/requirements.txt`
- `CookinBook/CookinBook/settings.py`
- `CookinBook/.env.example`

---

# Quick Reference

## Dependency Graph

```
TIMEBOX 2
=========
Can start immediately (no dependencies):
  - Issue 1:  Migrations & model fix      [backend, database]
  - Issue 6:  Auth guards                  [backend, security]
  - Issue 7:  CI test runner               [infrastructure, CI/CD, testing]

After Issue 1 merges:
  - Issue 2:  Chat API                     [backend, API]
  - Issue 5:  Recipe data source           [backend, data]

After Issue 2 merges:
  - Issue 3:  Chat frontend                [frontend]

After Issues 2 + 3 merge:
  - Issue 4:  History page                 [backend, frontend]


TIMEBOX 3
=========
Can start immediately (needs Issue 1 from TB2):
  - Issue 8:  Shopping list UI             [backend, frontend]
  - Issue 12: Admin registration           [backend, admin]

No dependencies (can start immediately):
  - Issue 13: Security settings            [infrastructure, security]
  - Issue 18: Deployment (Docker)          [infrastructure]

After Issue 5 (TB2) merges:
  - Issue 16: Elasticsearch & data pipeline [backend, infrastructure, data]

After Issue 8 merges:
  - Issue 9:  Chat → Shopping flow         [backend, integration]
  - Issue 10: UCP integration              [backend, integration, UCP]

After Issue 10 merges:
  - Issue 17: Order tracking UI            [backend, frontend, UCP]

After Issues 1, 2, 8 are stable:
  - Issue 11: Tests                        [testing, backend]

After Issue 13 merges:
  - Issue 14: Error handling & logging     [backend, infrastructure]

After everything merges:
  - Issue 15: Documentation                [documentation]
```

## Priority Table

| Priority | Issue | Title | Milestone |
|----------|-------|-------|-----------|
| **P0** | 1 | Migrations & model fix | Timebox 2 |
| **P0** | 2 | Chat API endpoint | Timebox 2 |
| **P0** | 3 | Chat frontend UI | Timebox 2 |
| **P1** | 5 | Recipe data source | Timebox 2 |
| **P1** | 6 | Auth guards | Timebox 2 |
| **P1** | 4 | History page | Timebox 2 |
| **P2** | 7 | CI test runner | Timebox 2 |
| **P0** | 8 | Shopping list UI | Timebox 3 |
| **P0** | 10 | UCP integration | Timebox 3 |
| **P0** | 18 | Deployment (Docker) | Timebox 3 |
| **P1** | 9 | Chat → Shopping flow | Timebox 3 |
| **P1** | 16 | Elasticsearch & data pipeline | Timebox 3 |
| **P1** | 17 | Order tracking UI | Timebox 3 |
| **P1** | 11 | Unit & integration tests | Timebox 3 |
| **P1** | 13 | Security settings | Timebox 3 |
| **P2** | 12 | Admin registration | Timebox 3 |
| **P2** | 14 | Error handling & logging | Timebox 3 |
| **P2** | 15 | README & documentation | Timebox 3 |

## Labels to Create

| Label | Color Suggestion | Used In |
|-------|-----------------|---------|
| `backend` | `#0075ca` | Issues 1-2, 4-6, 8-14, 16-17 |
| `frontend` | `#7057ff` | Issues 3-4, 8, 17 |
| `database` | `#d73a4a` | Issue 1 |
| `API` | `#0e8a16` | Issue 2 |
| `security` | `#b60205` | Issues 6, 13 |
| `infrastructure` | `#006b75` | Issues 7, 13-14, 16, 18 |
| `testing` | `#fbca04` | Issues 7, 11 |
| `CI/CD` | `#1d76db` | Issue 7 |
| `integration` | `#5319e7` | Issues 9-10 |
| `UCP` | `#e99695` | Issues 10, 17 |
| `data` | `#c2e0c6` | Issues 5, 16 |
| `admin` | `#bfdadc` | Issue 12 |
| `documentation` | `#0075ca` | Issue 15 |
