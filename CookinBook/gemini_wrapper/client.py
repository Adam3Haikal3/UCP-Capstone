from google import genai
from google.genai import types
from django.conf import settings

# --- TOOLS (Mock Functions until elasticsearch and UCP parts are finished) ---


# Elasticsearch part
def search_recipes(query: str):
    """
    Search for recipes based on a food name.
    """
    print(f"\n[Wrapper Log] Searching Elasticsearch for: '{query}'...")
    # Mock Logic (using taco as an example)
    if "taco" in query.lower():
        return [
            {
                "id": "rec_01",
                "title": "Street Style Tacos",
                "ingredients": [
                    "Mini Corn Tortillas",
                    "Carne Asada",
                    "Onion",
                    "Cilantro",
                ],
            },
            {
                "id": "rec_02",
                "title": "Vegetarian Tacos",
                "ingredients": ["Corn Tortillas", "Black Beans", "Avocado", "Salsa"],
            },
        ]
    return [
        {
            "id": "rec_99",
            "title": f"Generic {query} Dish",
            "ingredients": [f"Fresh {query}", "Salt", "Olive Oil"],
        }
    ]


# UCP part
def execute_purchase(items: list[str]):
    """
    Buy ingredients. Use ONLY after user explicitly confirms the list.
    """
    print(f"\n[Wrapper Log] Connecting to Google UCP to buy: {items}...")
    return {
        "status": "success",
        "transaction_id": "TX-UCP-77821",
        "message": "Payment processed via UCP.",
    }


# --- THE MAIN WRAPPER CLASS ---


class CookinBookBot:
    def __init__(self):
        # 1. Load the system prompt
        self.system_prompt = """
        Role: You are "Cookin' Bot", a helpful shopping assistant.
        Rules:
        1. Always search for recipes first. Do not make up ingredients.
        2. Before buying, list the ingredients and ask for confirmation.
        3. If the user confirms, call 'execute_purchase'.
        4. Be brief and friendly.
        """

        # 2. Initialize the client using the key from settings.py
        try:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except AttributeError:
            raise ValueError("GEMINI_API_KEY is missing from settings.py!")

        # 3. Create the chat session with tools attached
        self.chat = self.client.chats.create(
            model="gemini-flash-lite-latest",
            config=types.GenerateContentConfig(
                tools=[search_recipes, execute_purchase],
                system_instruction=self.system_prompt,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=False
                ),
            ),
        )

        # Simple cart memory (reset every time the class is instantiated)
        self.cart = []

    def send_message(self, user_text):
        """
        Sends a message to the bot and returns the text response.
        """
        cart_status = (
            f"Current Cart: {self.cart}" if self.cart else "Current Cart: Empty"
        )
        full_prompt = f"[System Info: {cart_status}]\nUser says: {user_text}"

        try:
            response = self.chat.send_message(full_prompt)
            return response.text
        except Exception as e:
            return f"Error communicating with Gemini: {e}"
