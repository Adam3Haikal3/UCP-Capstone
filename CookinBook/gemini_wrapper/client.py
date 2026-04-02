from google import genai
from google.genai import types
from django.conf import settings
import logging
from gemini_wrapper.es import get_es

logger = logging.getLogger(__name__)

_last_search_results = []


def search_recipes(query: str):
    """
    Search for recipes based on a food name.
    """
    global _last_search_results
    logger.info("Searching Elasticsearch for: %r", query)

    try:
        es = get_es()
    except Exception as e:
        logger.error("Failed to connect to ES server: %s", e)
        _last_search_results = []
        return []

    index_name = settings.ELASTICSEARCH_INDEX

    try:
        response = es.search(
            index=index_name,
            query={
                "simple_query_string": {
                    "query": query,
                    "fields": ["title", "ingredients", "instructions"],
                    "default_operator": "or",
                }
            },
        )
    except Exception as e:
        logger.error("ES search failed: %s", e)
        _last_search_results = []
        return []

    result = []

    for hit in response["hits"]["hits"]:
        result.append(
            {
                "id": hit["_id"],
                "title": hit["_source"]["title"],
                "ingredients": hit["_source"]["ingredients"],
            }
        )

    _last_search_results = result
    return result


def execute_purchase(items: list[str]):
    """
    Buy ingredients. Use ONLY after user explicitly confirms the list.
    """
    logger.info("Connecting to Google UCP to buy: %r", items)
    return {
        "status": "success",
        "transaction_id": "TX-UCP-77821",
        "message": "Payment processed via UCP.",
    }


class CookinBookBot:
    def __init__(self):
        self.system_prompt = (
            "Role: You are 'Cookin' Bot', a friendly recipe assistant.\n"
            "Rules:\n"
            "1. Always use search_recipes to find recipes. Never invent recipes or ingredients.\n"
            "2. When search results are returned, give a brief friendly summary in chat "
            "(e.g. 'I found 5 chicken recipes for you! Browse the cards in the recipe panel "
            "and pick one you like.'). Do NOT list full ingredients in the chat — "
            "the recipe panel handles that automatically.\n"
            "3. If the user asks general cooking questions (technique, substitutions, etc.), "
            "answer directly without searching.\n"
            "4. Be brief, warm, and helpful.\n"
        )

        try:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except AttributeError:
            raise ValueError("GEMINI_API_KEY is missing from settings.py!")

        self.chat = self.client.chats.create(
            model="gemini-3.1-flash-lite-preview",
            config=types.GenerateContentConfig(
                tools=[search_recipes, execute_purchase],
                system_instruction=self.system_prompt,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=False
                ),
            ),
        )

        self.cart = []

    def send_message(self, user_text):
        """
        Sends a message and returns (reply_text, recipes_list).
        recipes_list comes from the side-effect capture in search_recipes.
        """
        global _last_search_results
        _last_search_results = []

        cart_status = (
            f"Current Cart: {self.cart}" if self.cart else "Current Cart: Empty"
        )
        full_prompt = f"[System Info: {cart_status}]\nUser says: {user_text}"

        try:
            response = self.chat.send_message(full_prompt)
            return response.text, list(_last_search_results)
        except Exception:
            logger.exception("Error communicating with Gemini")
            raise RuntimeError("Error communicating with Gemini")
