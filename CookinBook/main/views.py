from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm, ProfileAddressForm
from .models import Profile, ChatConversation, ChatMessage, ShoppingListSession
from gemini_wrapper.client import CookinBookBot
from django.contrib import messages
import json
import logging
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .models import ShoppingListSession, ShoppingListItem


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


@login_required
def history_view(request):
    orders = ShoppingListSession.objects.filter(
        user=request.user,
        order_status__in=["OF", "D"]
    ).order_by("-id")

    order_data = []
    for order in orders:
        item_count = ShoppingListItem.objects.filter(session=order).count()

        if order.order_status == "OF":
            status_label = "OrderFinalized"
        elif order.order_status == "D":
            status_label = "Delivered"
        else:
            status_label = order.order_status

        order_data.append({
            "id": order.id,
            "date": getattr(order, "created_at", None),
            "total_cost": order.total_cost,
            "status": status_label,
            "item_count": item_count,
        })

    return render(request, "main/history/history.html", {
        "orders": orders
    })


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

    try:
        ChatMessage.objects.create(conversation=convo, sender="U", content=user_message)
    except Exception:
        logger.exception("Failed to save user message to database")
        return JsonResponse({"error": "Failed to save your message."}, status=500)

    try:
        bot = CookinBookBot()
        reply, recipes = bot.send_message(user_message)
    except Exception:
        logger.exception("Error while sending message to CookinBookBot")
        return JsonResponse(
            {"error": "Failed to get a response from the assistant."}, status=500
        )

    try:
        ChatMessage.objects.create(conversation=convo, sender="B", content=reply)
        if recipes:
            convo.artifact_content = json.dumps(recipes)
        convo.save()
    except Exception:
        logger.exception("Failed to save bot reply to database")
        return JsonResponse(
            {"error": "Failed to save Cookin' Bot's reply."}, status=500
        )

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
        logger.exception("Failed to fetch recipe details for mealdb_id=%s", mealdb_id)
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
    """Send items to Gemini cooking bot"""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    items = data.get("items", [])
    if not items:
        return JsonResponse({"error": "No items provided."}, status=400)

    conversation_id = data.get("conversation_id")
    convo = get_object_or_404(ChatConversation, pk=conversation_id, user=request.user)

    sls = ShoppingListSession.objects.create(
        user=request.user, conversation=convo, status="NS"
    )
    sls_id = sls.id

    try:
        bot = CookinBookBot()
        bot.handle_purchase(items, sls_id)
    except Exception:
        logger.exception("Error while sending ingredients to CookinBookBot")
        return JsonResponse({"error": "Failed to create a checkout."}, status=500)

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
            try:
                form.save()
            except Exception:
                logger.exception("Failed to save new user to database")
                messages.error(
                    request,
                    "An error occurred while creating your account. Please try again.",
                )
                return render(request, "main/users/signup/signup.html", {"form": form})
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            if user is None:
                logger.error(
                    "authenticate() returned None after signup for username=%s",
                    username,
                )
                messages.error(
                    request, "Account created but login failed. Please log in manually."
                )
                return redirect("login")
            login(request, user)
            messages.success(request, f"Welcome, {username}! Your account was created.")
            return redirect("chat")
    else:
        form = SignUpForm()
    return render(request, "main/users/signup/signup.html", {"form": form})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileAddressForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully!")
            return redirect("profile")
    else:
        form = ProfileAddressForm(instance=profile)

    return render(request, "main/users/profile/profile.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("home")

@login_required
def orders_list(request):
    orders = ShoppingListSession.objects.filter(
        user=request.user,
        order_status__in=["OF", "D"]
    ).order_by('-id')  

    return render(request, "main/orders/list.html", {
        "orders": orders
    })


@login_required
def order_detail(request, session_id):
    order = get_object_or_404(
        ShoppingListSession,
        id=session_id,
        user=request.user
    )

    try:
        items = order.items.all()
    except:
        items = []

    return render(request, "main/orders/detail.html", {
        "order": order,
        "items": items
    })