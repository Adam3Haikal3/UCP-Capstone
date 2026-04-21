# Cookin' Book

## Quick Start with Docker

The fastest way to run the full stack (Django + PostgreSQL + Elasticsearch):

```bash
cd CookinBook

# Create your environment file
cp .env.example .env
# Edit .env and fill in SECRET_KEY, GEMINI_API_KEY, etc.

# Start all services
docker-compose up --build
```

The app will be available at **http://localhost:8000**.

To run database migrations or seed Elasticsearch from a separate terminal:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py shell -c "from gemini_wrapper.es import seed_from_mealdb; seed_from_mealdb()"
```

To stop everything:

```bash
docker-compose down          # keep data volumes
docker-compose down -v       # remove data volumes too
```

---

## Manual Setup (Local Development)

### Install dependencies

```bash
cd CookinBook
pip install -r requirements.txt
```

### Configure environment

```bash
cp .env.example .env
# Fill in SECRET_KEY, GEMINI_API_KEY, ELASTICSEARCH_PASSWORD, etc.
```

### Run the development server

```bash
python manage.py migrate
python manage.py runserver
```

By default the app uses SQLite. To use PostgreSQL locally, set `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgres://user:password@localhost:5432/cookinbook
```

---

## How to test the mock gemini wrapper

1. Start the Django shell:

```bash
python manage.py shell
from gemini_wrapper.client import CookinBookBot
bot = CookinBookBot()
```

2. Paste this loop for interactive chat:

```python
while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    response = bot.send_message(user_input)
    print("Bot:", response)
```

3. Press enter twice, then start a conversation (e.g. "I want to make tacos"). Type `quit` to exit chat, then `exit()` to leave the shell.

---

## How to run ElasticSearch Mock Recipe Search

Before starting, ensure that Elasticsearch is running (either via Docker Compose or locally).

If running locally, include the server password and CA cert fingerprint in `.env`.

Index recipes from TheMealDB:

```bash
python manage.py shell
from gemini_wrapper.es import seed_from_mealdb
seed_from_mealdb()
```

Then follow the gemini wrapper instructions above to search recipes.

---

## How to run UCP with Mock Server

Follow this link to access the public UCP Mock Server: https://github.com/Upsonic/ucp-client

Before going further, replace the "inventory" and "products" csv files located in the server's `test_data` folder with the `server_inventory` and `server_products` csv files located in the `data` folder of this CookinBook project.

Ensure that `UCP_MOCK_MODE=True` in `.env` before starting.

Follow the README instructions of the UCP Mock Server to run before attempting to create a checkout cart with the CookinBook bot.

---

## Running Tests

```bash
cd CookinBook
python manage.py test main
```
