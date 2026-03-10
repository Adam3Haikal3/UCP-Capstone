import requests
from elasticsearch import Elasticsearch, helpers
from django.conf import settings
from string import ascii_lowercase

# Used to create the recipe index in the ES server if it does not exist
def create_index():
    es = Elasticsearch(settings.ELASTICSEARCH_HOST)
    index_name = settings.ELASTICSEARCH_INDEX

    if es.indices.exists(index=index_name):
        print(f"[ES] Index '{index_name}' already exists.")
        return
    
    print(f"[ES] Index '{index_name}' not found. Creating now... ")
    es.indices.create(
        index = index_name,
        mappings = {
            "properties": {
                "title": {"type": "text"},
                "ingredients": {"type": "keyword"},
                "instructions": {"type": "text"},
            }
        },
    )

# Collects recipes from TheMealDB and indexes them into the server
def seed_from_mealdb():
    es = Elasticsearch(settings.ELASTICSEARCH_HOST)
    index_name = settings.ELASTICSEARCH_INDEX

    create_index()

    actions = []

    for l in ascii_lowercase:
        URL = f"http://www.themealdb.com/api/json/v1/1/search.php?f={l}"
        r = requests.get(url = URL)
        meals = r.json()

        if meals['meals'] == None:
            continue
    
        for meal in meals['meals']:
            title = meal['strMeal']
            instructions = meal['strInstructions']

            ingredients = []
            for n in range(1, 20):
                
                ingredients.append(meal[f"strIngredient{n}"] or "")

            actions.append(
                {
                    "_index": index_name,
                    "_id": meal["idMeal"],
                    "_source": {
                        "title": title,
                        "ingredients": ingredients,
                        "instructions": instructions,
                    }
                }
            )
        
    helpers.bulk(es, actions)

