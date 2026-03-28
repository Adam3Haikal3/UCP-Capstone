from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import ChatConversation, ChatMessage
from gemini_wrapper.client import CookinBookBot
from django.contrib import messages
import json
import logging
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

logger = logging.getLogger(__name__)


def home_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "main/home/home.html")


def chat_view(request, conversation_id=None):
    context = {}
    if request.user.is_authenticated:
        conversations = ChatConversation.objects.filter(user=request.user)
        context["conversations"] = conversations

        if conversation_id:
            convo = get_object_or_404(
                ChatConversation, pk=conversation_id, user=request.user
            )
            context["active_conversation"] = convo
            context["active_messages"] = convo.messages.all()

    return render(request, "main/chat/chat.html", context)


def history_view(request):
    return render(request, "main/history/history.html")


@require_POST
@login_required
def chat_send(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message is empty"}, status=400)

    conversation_id = data.get("conversation_id")

    if conversation_id:
        convo = get_object_or_404(
            ChatConversation, pk=conversation_id, user=request.user
        )
    else:
        title = user_message[:60] + ("…" if len(user_message) > 60 else "")
        convo = ChatConversation.objects.create(user=request.user, title=title)

    ChatMessage.objects.create(conversation=convo, sender="U", content=user_message)

    try:
        bot = CookinBookBot()
        reply, recipes = bot.send_message(user_message)
    except Exception:
        logger.exception("Error while sending message to CookinBookBot")
        return JsonResponse(
            {"error": "Failed to get a response from the assistant."}, status=500
        )

    ChatMessage.objects.create(conversation=convo, sender="B", content=reply)

    if recipes:
        convo.artifact_content = json.dumps(recipes)
    convo.save()

    return JsonResponse(
        {
            "reply": reply,
            "conversation_id": convo.pk,
            "conversation_title": convo.title,
            "recipes": recipes,
        }
    )


@require_GET
@login_required
def conversation_list(request):
    convos = ChatConversation.objects.filter(user=request.user).values(
        "id", "title", "updated_at"
    )
    return JsonResponse({"conversations": list(convos)})


@require_GET
@login_required
def conversation_detail(request, conversation_id):
    convo = get_object_or_404(ChatConversation, pk=conversation_id, user=request.user)
    msgs = list(convo.messages.values("sender", "content", "sent_at"))

    recipes = []
    if convo.artifact_content:
        try:
            recipes = json.loads(convo.artifact_content)
        except (json.JSONDecodeError, TypeError):
            recipes = []

    return JsonResponse(
        {
            "id": convo.pk,
            "title": convo.title,
            "recipes": recipes,
            "messages": msgs,
        }
    )


@require_GET
@login_required
def recipe_detail(request, mealdb_id):
    """Fetch full recipe details from TheMealDB API by ID."""
    try:
        r = requests.get(
            f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={mealdb_id}",
            timeout=10,
        )
        data = r.json()
    except Exception:
        return JsonResponse({"error": "Failed to fetch recipe details."}, status=502)

    meals = data.get("meals")
    if not meals:
        return JsonResponse({"error": "Recipe not found."}, status=404)

    meal = meals[0]

    ingredients = []
    for n in range(1, 21):
        name = (meal.get(f"strIngredient{n}") or "").strip()
        measure = (meal.get(f"strMeasure{n}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})

    return JsonResponse(
        {
            "id": meal.get("idMeal"),
            "title": meal.get("strMeal", ""),
            "instructions": meal.get("strInstructions", ""),
            "thumbnail": meal.get("strMealThumb", ""),
            "category": meal.get("strCategory", ""),
            "area": meal.get("strArea", ""),
            "ingredients": ingredients,
        }
    )


@require_POST
@login_required
def add_to_cart(request):
    """Stub endpoint for adding ingredients to cart (UCP placeholder)."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items provided."}, status=400)

    return JsonResponse(
        {
            "status": "success",
            "message": f"{len(items)} item(s) added to cart.",
            "transaction_id": "TX-UCP-PENDING",
        }
    )


@require_POST
@login_required
def conversation_delete(request, conversation_id):
    convo = get_object_or_404(ChatConversation, pk=conversation_id, user=request.user)
    convo.delete()
    return JsonResponse({"ok": True})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect("chat")
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "main/users/login/login.html", {"form": form})


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, f"Welcome, {username}! Your account was created.")
            return redirect("chat")
    else:
        form = SignUpForm()
    return render(request, "main/users/signup/signup.html", {"form": form})


@login_required
def profile_view(request):
    return render(request, "main/users/profile/profile.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("home")
