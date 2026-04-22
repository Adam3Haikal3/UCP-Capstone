import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from main.models import (
    Profile,
    ChatConversation,
    ChatMessage,
    Recipe,
    ShoppingListSession,
    ShoppingListItem,
)
from main.forms import SignUpForm


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------
class ProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", "alice@test.com", "pass1234")

    def test_create_profile(self):
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertIsNone(profile.birth_date)
        self.assertIsNotNone(profile.created_at)

    def test_str(self):
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(str(profile), "alice's profile")

    def test_one_to_one_reverse(self):
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(self.user.profile, profile)


class ChatConversationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("bob", "bob@test.com", "pass1234")

    def test_create_conversation(self):
        convo = ChatConversation.objects.create(user=self.user, title="Test Chat")
        self.assertEqual(convo.user, self.user)
        self.assertEqual(convo.title, "Test Chat")
        self.assertEqual(convo.artifact_content, "")
        self.assertIsNotNone(convo.started_at)

    def test_default_title(self):
        convo = ChatConversation.objects.create(user=self.user)
        self.assertEqual(convo.title, "New Chat")

    def test_str(self):
        convo = ChatConversation.objects.create(user=self.user, title="Dinner Ideas")
        self.assertEqual(str(convo), "Dinner Ideas (bob)")

    def test_fk_user_relationship(self):
        ChatConversation.objects.create(user=self.user, title="A")
        ChatConversation.objects.create(user=self.user, title="B")
        self.assertEqual(self.user.conversations.count(), 2)

    def test_ordering(self):
        ChatConversation.objects.create(user=self.user, title="First")
        c2 = ChatConversation.objects.create(user=self.user, title="Second")
        # Most recently updated first
        convos = list(ChatConversation.objects.filter(user=self.user))
        self.assertEqual(convos[0], c2)


class ChatMessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("carol", "c@test.com", "pass1234")
        self.convo = ChatConversation.objects.create(user=self.user, title="Chat")

    def test_create_message(self):
        msg = ChatMessage.objects.create(
            conversation=self.convo, sender="U", content="Hello"
        )
        self.assertEqual(msg.conversation, self.convo)
        self.assertEqual(msg.sender, "U")
        self.assertEqual(msg.content, "Hello")
        self.assertIsNotNone(msg.sent_at)

    def test_fk_conversation(self):
        ChatMessage.objects.create(conversation=self.convo, sender="U", content="Hi")
        ChatMessage.objects.create(conversation=self.convo, sender="B", content="Hey")
        self.assertEqual(self.convo.messages.count(), 2)

    def test_str_truncation(self):
        msg = ChatMessage.objects.create(
            conversation=self.convo, sender="B", content="A" * 100
        )
        self.assertTrue(str(msg).startswith("[Bot]"))
        self.assertLessEqual(len(str(msg)), 60)

    def test_cascade_delete(self):
        ChatMessage.objects.create(conversation=self.convo, sender="U", content="x")
        self.convo.delete()
        self.assertEqual(ChatMessage.objects.count(), 0)


class RecipeModelTest(TestCase):
    def test_create_recipe(self):
        r = Recipe.objects.create(
            elasticsearch_id="12345",
            title="Pasta",
            ingredients=["tomato", "basil"],
            instructions="Cook it",
            cook_time="30 min",
            servings=4,
        )
        self.assertEqual(r.title, "Pasta")
        self.assertEqual(r.ingredients, ["tomato", "basil"])

    def test_str(self):
        r = Recipe.objects.create(elasticsearch_id="99", title="Soup")
        self.assertEqual(str(r), "Soup")

    def test_unique_elasticsearch_id(self):
        Recipe.objects.create(elasticsearch_id="dup", title="A")
        with self.assertRaises(Exception):
            Recipe.objects.create(elasticsearch_id="dup", title="B")


class ShoppingListSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dave", "d@test.com", "pass1234")
        self.convo = ChatConversation.objects.create(user=self.user)

    def test_create_session(self):
        sls = ShoppingListSession.objects.create(
            user=self.user, conversation=self.convo
        )
        self.assertEqual(sls.status, "NS")
        self.assertEqual(sls.order_status, "P")
        self.assertEqual(sls.total_cost, Decimal("0.00"))
        self.assertIsNone(sls.completed_at)

    def test_str(self):
        sls = ShoppingListSession.objects.create(
            user=self.user, conversation=self.convo
        )
        self.assertIn("dave", str(sls))

    def test_fk_relationships(self):
        ShoppingListSession.objects.create(user=self.user, conversation=self.convo)
        self.assertEqual(self.user.shopping_sessions.count(), 1)
        self.assertEqual(self.convo.shopping_sessions.count(), 1)

    def test_m2m_recipes(self):
        sls = ShoppingListSession.objects.create(
            user=self.user, conversation=self.convo
        )
        r1 = Recipe.objects.create(elasticsearch_id="a", title="Tacos")
        r2 = Recipe.objects.create(elasticsearch_id="b", title="Pizza")
        sls.recipes.add(r1, r2)
        self.assertEqual(sls.recipes.count(), 2)


class ShoppingListItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("eve", "e@test.com", "pass1234")
        convo = ChatConversation.objects.create(user=self.user)
        self.session = ShoppingListSession.objects.create(
            user=self.user, conversation=convo
        )

    def test_create_item(self):
        item = ShoppingListItem.objects.create(
            session=self.session,
            ingredient_name="Flour",
            quantity=Decimal("2.50"),
            unit="cups",
            price=Decimal("3.99"),
        )
        self.assertEqual(item.ingredient_name, "Flour")
        self.assertTrue(item.is_available)
        self.assertIsNone(item.purchased_at)

    def test_str(self):
        item = ShoppingListItem.objects.create(
            session=self.session,
            ingredient_name="Sugar",
            quantity=Decimal("1"),
            unit="kg",
        )
        self.assertEqual(str(item), "1 kg Sugar")

    def test_fk_session(self):
        ShoppingListItem.objects.create(
            session=self.session, ingredient_name="A", quantity=1, unit="pc"
        )
        ShoppingListItem.objects.create(
            session=self.session, ingredient_name="B", quantity=2, unit="pc"
        )
        self.assertEqual(self.session.items.count(), 2)

    def test_optional_recipe_fk(self):
        recipe = Recipe.objects.create(elasticsearch_id="r1", title="Cake")
        item = ShoppingListItem.objects.create(
            session=self.session,
            recipe=recipe,
            ingredient_name="Eggs",
            quantity=3,
            unit="pcs",
        )
        self.assertEqual(item.recipe, recipe)

    def test_recipe_set_null_on_delete(self):
        recipe = Recipe.objects.create(elasticsearch_id="r2", title="Pie")
        item = ShoppingListItem.objects.create(
            session=self.session,
            recipe=recipe,
            ingredient_name="Butter",
            quantity=1,
            unit="stick",
        )
        recipe.delete()
        item.refresh_from_db()
        self.assertIsNone(item.recipe)

    def test_cascade_session_delete(self):
        ShoppingListItem.objects.create(
            session=self.session, ingredient_name="X", quantity=1, unit="u"
        )
        self.session.delete()
        self.assertEqual(ShoppingListItem.objects.count(), 0)


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------
class SignUpFormTest(TestCase):
    def test_valid_form(self):
        form = SignUpForm(
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            }
        )
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        form = SignUpForm(
            data={
                "username": "newuser",
                "email": "new@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Different!1",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_email_required(self):
        form = SignUpForm(
            data={
                "username": "newuser",
                "email": "",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_saves_user(self):
        form = SignUpForm(
            data={
                "username": "saved",
                "email": "saved@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, "saved")
        self.assertEqual(user.email, "saved@test.com")


# ---------------------------------------------------------------------------
# View / page tests
# ---------------------------------------------------------------------------
class PublicPageTests(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_login_page_returns_200(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)

    def test_signup_page_returns_200(self):
        response = self.client.get("/signup/")
        self.assertEqual(response.status_code, 200)

    def test_home_redirects_authenticated_user(self):
        User.objects.create_user("u", "u@t.com", "pass1234")
        self.client.login(username="u", password="pass1234")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("chat"))


class ProtectedPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("prot", "p@t.com", "pass1234")

    def test_chat_returns_200_for_anonymous(self):
        # chat_view does NOT have @login_required; renders for all
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)

    def test_chat_returns_200_for_authenticated(self):
        self.client.login(username="prot", password="pass1234")
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)

    def test_chat_with_conversation_id(self):
        self.client.login(username="prot", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user, title="Test")
        response = self.client.get(f"/chat/{convo.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_chat_conversation_404_for_other_user(self):
        other = User.objects.create_user("other", "o@t.com", "pass1234")
        convo = ChatConversation.objects.create(user=other, title="Other")
        self.client.login(username="prot", password="pass1234")
        response = self.client.get(f"/chat/{convo.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_history_returns_200(self):
        # history_view has no @login_required
        response = self.client.get("/history/")
        self.assertEqual(response.status_code, 200)

    def test_profile_redirects_anonymous(self):
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_profile_returns_200_authenticated(self):
        self.client.login(username="prot", password="pass1234")
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_conversation_list_redirects_anonymous(self):
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, 302)

    def test_conversation_list_authenticated(self):
        self.client.login(username="prot", password="pass1234")
        ChatConversation.objects.create(user=self.user, title="C1")
        response = self.client.get("/api/conversations/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["conversations"]), 1)

    def test_conversation_detail_authenticated(self):
        self.client.login(username="prot", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user, title="Detail")
        ChatMessage.objects.create(conversation=convo, sender="U", content="hi")
        response = self.client.get(f"/api/conversations/{convo.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Detail")
        self.assertEqual(len(data["messages"]), 1)

    def test_conversation_detail_with_recipes(self):
        self.client.login(username="prot", password="pass1234")
        convo = ChatConversation.objects.create(
            user=self.user,
            title="Recipes",
            artifact_content='[{"id": "1", "title": "Tacos"}]',
        )
        response = self.client.get(f"/api/conversations/{convo.pk}/")
        data = response.json()
        self.assertEqual(len(data["recipes"]), 1)

    def test_conversation_delete(self):
        self.client.login(username="prot", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user, title="Del")
        response = self.client.post(f"/api/conversations/{convo.pk}/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatConversation.objects.count(), 0)

    def test_conversation_delete_wrong_user(self):
        other = User.objects.create_user("other2", "o2@t.com", "pass1234")
        convo = ChatConversation.objects.create(user=other, title="Nope")
        self.client.login(username="prot", password="pass1234")
        response = self.client.post(f"/api/conversations/{convo.pk}/delete/")
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Auth flow tests
# ---------------------------------------------------------------------------
class AuthFlowTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            "/signup/",
            {
                "username": "signuptest",
                "email": "signup@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("chat"))
        self.assertTrue(User.objects.filter(username="signuptest").exists())
        # Verify user is logged in
        profile_resp = self.client.get("/profile/")
        self.assertEqual(profile_resp.status_code, 200)

    def test_signup_invalid_shows_form(self):
        response = self.client.post(
            "/signup/",
            {
                "username": "",
                "email": "bad@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            },
        )
        self.assertEqual(response.status_code, 200)  # Re-renders form
        self.assertFalse(User.objects.filter(email="bad@test.com").exists())

    def test_login_valid_credentials(self):
        User.objects.create_user("loginuser", "l@t.com", "pass1234")
        response = self.client.post(
            "/login/", {"username": "loginuser", "password": "pass1234"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("chat"))

    def test_login_invalid_credentials(self):
        User.objects.create_user("loginuser2", "l2@t.com", "pass1234")
        response = self.client.post(
            "/login/", {"username": "loginuser2", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)  # Re-renders form

    def test_logout_redirects_home(self):
        User.objects.create_user("logoutuser", "lo@t.com", "pass1234")
        self.client.login(username="logoutuser", password="pass1234")
        response = self.client.get("/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))
        # Verify logged out - profile should redirect
        profile_resp = self.client.get("/profile/")
        self.assertEqual(profile_resp.status_code, 302)

    def test_full_signup_login_logout_cycle(self):
        # Sign up
        self.client.post(
            "/signup/",
            {
                "username": "cycleuser",
                "email": "cycle@test.com",
                "password1": "Str0ng!Pass",
                "password2": "Str0ng!Pass",
            },
        )
        # Logout
        self.client.get("/logout/")
        # Login again
        response = self.client.post(
            "/login/", {"username": "cycleuser", "password": "Str0ng!Pass"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("chat"))


# ---------------------------------------------------------------------------
# Chat API tests
# ---------------------------------------------------------------------------
class ChatSendAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("chatter", "ch@t.com", "pass1234")

    def test_unauthenticated_rejected(self):
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_get_method_not_allowed(self):
        self.client.login(username="chatter", password="pass1234")
        response = self.client.get("/chat/send/")
        self.assertEqual(response.status_code, 405)

    def test_invalid_json(self):
        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/", "not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid JSON")

    def test_empty_message(self):
        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "   "}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Message is empty")

    @patch("main.views.CookinBookBot")
    def test_new_conversation_created(self, MockBot):
        mock_bot = MockBot.return_value
        mock_bot.send_message.return_value = ("Here are some recipes!", [])

        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "find me chicken recipes"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["reply"], "Here are some recipes!")
        self.assertIn("conversation_id", data)

        # Verify DB state
        convo = ChatConversation.objects.get(pk=data["conversation_id"])
        self.assertEqual(convo.user, self.user)
        self.assertEqual(convo.messages.count(), 2)  # user + bot
        self.assertEqual(convo.messages.first().sender, "U")
        self.assertEqual(convo.messages.last().sender, "B")

    @patch("main.views.CookinBookBot")
    def test_existing_conversation(self, MockBot):
        mock_bot = MockBot.return_value
        mock_bot.send_message.return_value = ("Got it!", [])

        self.client.login(username="chatter", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user, title="Existing")

        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "more ideas", "conversation_id": convo.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["conversation_id"], convo.pk)
        self.assertEqual(convo.messages.count(), 2)

    @patch("main.views.CookinBookBot")
    def test_recipes_in_response(self, MockBot):
        recipes = [
            {"id": "52772", "title": "Chicken Curry", "ingredients": ["chicken"]}
        ]
        mock_bot = MockBot.return_value
        mock_bot.send_message.return_value = ("Found recipes!", recipes)

        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "chicken"}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(len(data["recipes"]), 1)
        self.assertEqual(data["recipes"][0]["title"], "Chicken Curry")

        # Verify artifact_content saved
        convo = ChatConversation.objects.get(pk=data["conversation_id"])
        self.assertEqual(json.loads(convo.artifact_content), recipes)

    @patch("main.views.CookinBookBot")
    def test_bot_error_returns_500(self, MockBot):
        mock_bot = MockBot.return_value
        mock_bot.send_message.side_effect = RuntimeError("Gemini down")

        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "hello"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json())

    def test_conversation_id_wrong_user(self):
        other = User.objects.create_user("other3", "o3@t.com", "pass1234")
        convo = ChatConversation.objects.create(user=other, title="Theirs")

        self.client.login(username="chatter", password="pass1234")
        response = self.client.post(
            "/chat/send/",
            json.dumps({"message": "hi", "conversation_id": convo.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class AddToCartAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("shopper", "s@t.com", "pass1234")

    def test_unauthenticated_rejected(self):
        response = self.client.post(
            "/api/cart/add/",
            json.dumps({"items": [{"name": "flour"}]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    @patch("main.views.CookinBookBot")
    def test_add_to_cart_success(self, MockBot):
        mock_bot = MockBot.return_value
        mock_bot.handle_purchase.return_value = None

        self.client.login(username="shopper", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user)
        response = self.client.post(
            "/api/cart/add/",
            json.dumps(
                {
                    "items": [{"name": "flour", "measure": "1 cup"}],
                    "conversation_id": convo.pk,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(ShoppingListSession.objects.count(), 1)

    def test_empty_items(self):
        self.client.login(username="shopper", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user)
        response = self.client.post(
            "/api/cart/add/",
            json.dumps({"items": [], "conversation_id": convo.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json(self):
        self.client.login(username="shopper", password="pass1234")
        response = self.client.post(
            "/api/cart/add/", "bad", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("main.views.CookinBookBot")
    def test_bot_error_returns_500(self, MockBot):
        mock_bot = MockBot.return_value
        mock_bot.handle_purchase.side_effect = Exception("UCP down")

        self.client.login(username="shopper", password="pass1234")
        convo = ChatConversation.objects.create(user=self.user)
        response = self.client.post(
            "/api/cart/add/",
            json.dumps(
                {
                    "items": [{"name": "milk"}],
                    "conversation_id": convo.pk,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


class RecipeDetailAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("viewer", "v@t.com", "pass1234")

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/recipe/52772/")
        self.assertEqual(response.status_code, 302)

    @patch("main.views.requests.get")
    def test_recipe_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "meals": [
                {
                    "idMeal": "52772",
                    "strMeal": "Chicken Curry",
                    "strInstructions": "Cook it",
                    "strMealThumb": "http://img.jpg",
                    "strCategory": "Chicken",
                    "strArea": "Indian",
                    "strIngredient1": "Chicken",
                    "strMeasure1": "500g",
                    "strIngredient2": "",
                    "strMeasure2": "",
                    **{f"strIngredient{i}": "" for i in range(3, 21)},
                    **{f"strMeasure{i}": "" for i in range(3, 21)},
                }
            ]
        }
        mock_get.return_value = mock_response

        self.client.login(username="viewer", password="pass1234")
        response = self.client.get("/api/recipe/52772/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Chicken Curry")
        self.assertEqual(len(data["ingredients"]), 1)
        self.assertEqual(data["ingredients"][0]["name"], "Chicken")

    @patch("main.views.requests.get")
    def test_recipe_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"meals": None}
        mock_get.return_value = mock_response

        self.client.login(username="viewer", password="pass1234")
        response = self.client.get("/api/recipe/99999/")
        self.assertEqual(response.status_code, 404)

    @patch("main.views.requests.get")
    def test_api_failure(self, mock_get):
        mock_get.side_effect = Exception("timeout")

        self.client.login(username="viewer", password="pass1234")
        response = self.client.get("/api/recipe/52772/")
        self.assertEqual(response.status_code, 502)


# ---------------------------------------------------------------------------
# Gemini wrapper tests (CookinBookBot with mocked genai.Client)
# ---------------------------------------------------------------------------
class CookinBookBotTests(TestCase):
    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_send_message_returns_reply(self, MockGenaiClient, MockUCPTools):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "I found 3 chicken recipes for you!"
        mock_chat.send_message.return_value = mock_response
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        reply, recipes = bot.send_message("chicken recipes")

        self.assertEqual(reply, "I found 3 chicken recipes for you!")
        self.assertIsInstance(recipes, list)
        mock_chat.send_message.assert_called_once()

    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_send_message_captures_search_results(self, MockGenaiClient, MockUCPTools):
        import gemini_wrapper.client as client_mod

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Here are recipes"

        def fake_send(prompt):
            # Simulate search_recipes populating the global
            client_mod._last_search_results = [
                {"id": "1", "title": "Tacos", "ingredients": ["beef"]}
            ]
            return mock_response

        mock_chat.send_message.side_effect = fake_send
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        reply, recipes = bot.send_message("tacos")

        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0]["title"], "Tacos")

    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_send_message_raises_on_gemini_error(self, MockGenaiClient, MockUCPTools):
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API error")
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        with self.assertRaises(RuntimeError) as ctx:
            bot.send_message("test")
        self.assertIn("Gemini", str(ctx.exception))

    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_handle_purchase_calls_send_message(self, MockGenaiClient, MockUCPTools):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Order placed!"
        mock_chat.send_message.return_value = mock_response
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        items = [{"name": "flour", "measure": "2 cups"}]
        bot.handle_purchase(items, sls_id=999)
        mock_chat.send_message.assert_called_once()

    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_handle_purchase_raises_on_error_response(
        self, MockGenaiClient, MockUCPTools
    ):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "ERROR: create_cart - failed"
        mock_chat.send_message.return_value = mock_response
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        with self.assertRaises(ValueError):
            bot.handle_purchase([{"name": "egg"}], sls_id=1)

    @patch("gemini_wrapper.client.genai.Client")
    def test_missing_api_key_raises(self, MockGenaiClient):
        MockGenaiClient.side_effect = AttributeError("no key")

        from gemini_wrapper.client import CookinBookBot

        with self.assertRaises(ValueError) as ctx:
            CookinBookBot()
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    @patch("gemini_wrapper.client.UCPClientTools")
    @patch("gemini_wrapper.client.genai.Client")
    def test_cart_status_in_prompt(self, MockGenaiClient, MockUCPTools):
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "reply"
        mock_chat.send_message.return_value = mock_response
        MockGenaiClient.return_value.chats.create.return_value = mock_chat

        from gemini_wrapper.client import CookinBookBot

        bot = CookinBookBot()
        bot.send_message("hello")

        call_args = mock_chat.send_message.call_args[0][0]
        self.assertIn("Current Cart: Empty", call_args)
