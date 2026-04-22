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
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re


logger = logging.getLogger(__name__)


def _history_orders_for_user(user):
    orders = (
        ShoppingListSession.objects.filter(user=user, order_status__in=["OF", "D"])
        .select_related("conversation")
        .prefetch_related("items", "recipes")
        .order_by("-completed_at", "-id")
    )
    return [_decorate_order(order) for order in orders]


def _format_profile_address(profile):
    if not profile:
        return ""

    lines = [profile.street_address, profile.street_address_2]
    city_line_parts = [profile.city, profile.state, profile.zip_code]
    city_line = " ".join(part for part in city_line_parts if part)

    parts = [line for line in lines if line]
    if city_line:
        parts.append(city_line)
    if profile.country:
        parts.append(profile.country)

    return ", ".join(parts)


def _decorate_order(order):
    order.prefetched_items = list(order.items.all())
    order.item_count = len(order.prefetched_items)
    order.prefetched_recipes = list(order.recipes.all())
    order.primary_recipe = order.prefetched_recipes[0] if order.prefetched_recipes else None
    order.display_title = (
        order.primary_recipe.title
        if order.primary_recipe
        else order.conversation.title or "Cookin' Book checkout"
    )
    order.recipe_overview = _build_recipe_overview(order)
    order.recipe_steps = (
        _extract_recipe_steps(order.primary_recipe.instructions)
        if order.primary_recipe
        else []
    )
    return order


def _format_name_list(names):
    clean_names = [name for name in names if name]
    if not clean_names:
        return ""
    if len(clean_names) == 1:
        return clean_names[0]
    if len(clean_names) == 2:
        return f"{clean_names[0]} and {clean_names[1]}"
    return ", ".join(clean_names[:-1]) + f", and {clean_names[-1]}"


def _recipe_ingredient_names(recipe):
    names = []
    for ingredient in recipe.ingredients or []:
        if isinstance(ingredient, dict):
            name = (ingredient.get("name") or "").strip()
        else:
            name = str(ingredient).strip()
        if name:
            names.append(name)
    return names


def _build_recipe_overview(order):
    if order.primary_recipe:
        recipe_names = _recipe_ingredient_names(order.primary_recipe)[:4]
        if recipe_names:
            return f"Built around {_format_name_list(recipe_names)}."

        instruction_steps = _extract_recipe_steps(order.primary_recipe.instructions)
        if instruction_steps:
            return instruction_steps[0]

    item_names = [item.ingredient_name for item in order.prefetched_items[:4]]
    if item_names:
        return f"Built around {_format_name_list(item_names)}."

    return ""


def _extract_recipe_steps(instructions):
    text = (instructions or "").strip()
    if not text:
        return []

    lines = [
        line.strip(" \t\r\n-•")
        for line in re.split(r"\r?\n+", text)
        if line.strip()
    ]

    if len(lines) > 1:
        return lines

    normalized = re.sub(r"\s+", " ", text)
    steps = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
        if segment.strip()
    ]

    return steps or [normalized]


def _parse_measure_value(measure):
    measure = (measure or "").strip()
    if not measure:
        return Decimal("1"), "item"

    tokens = measure.split()
    quantity_token = tokens[0]
    unit_start = 1

    if len(tokens) > 1 and tokens[0].isdigit() and "/" in tokens[1]:
        quantity_token = f"{tokens[0]} {tokens[1]}"
        unit_start = 2

    try:
        if " " in quantity_token:
            whole, fraction = quantity_token.split(" ", 1)
            frac = Fraction(fraction)
            quantity = Decimal(whole) + (
                Decimal(frac.numerator) / Decimal(frac.denominator)
            )
        elif "/" in quantity_token:
            frac = Fraction(quantity_token)
            quantity = Decimal(frac.numerator) / Decimal(frac.denominator)
        else:
            quantity = Decimal(quantity_token)
        unit = " ".join(tokens[unit_start:]).strip() or "item"
        return quantity, unit[:30]
    except (InvalidOperation, ValueError, ZeroDivisionError):
        return Decimal("1"), measure[:30]


def _persist_session_items(session, items, recipe=None):
    saved_items = []

    for item in items:
        ingredient_name = (item.get("name") or "").strip()
        if not ingredient_name:
            continue

        quantity, unit = _parse_measure_value(item.get("measure", ""))

        try:
            price = Decimal(str(item.get("price", 0) or 0))
        except (InvalidOperation, TypeError, ValueError):
            price = Decimal("0")

        saved_items.append(
            session.items.model(
                session=session,
                recipe=recipe,
                ingredient_name=ingredient_name[:100],
                quantity=quantity,
                unit=(unit or "item")[:30],
                price=price,
                retailer=(item.get("retailer") or "")[:100],
                is_available=item.get("is_available", True),
            )
        )

    if saved_items:
        session.items.bulk_create(saved_items)


def _persist_session_recipe(session, recipe_data):
    if not isinstance(recipe_data, dict):
        return None

    recipe_id = str(recipe_data.get("id") or "").strip()
    recipe_title = (recipe_data.get("title") or "").strip()

    if not recipe_id or not recipe_title:
        return None

    recipe, _ = session.recipes.model.objects.update_or_create(
        elasticsearch_id=recipe_id,
        defaults={
            "title": recipe_title[:255],
            "ingredients": recipe_data.get("ingredients") or [],
            "instructions": recipe_data.get("instructions") or "",
        },
    )
    session.recipes.add(recipe)
    return recipe


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
    if request.user.is_authenticated:
        orders = _history_orders_for_user(request.user)
    else:
        orders = ShoppingListSession.objects.none()

    return render(request, "main/history/history.html", {"orders": orders})


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
    recipe_data = data.get("recipe") or {}

    conversation_id = data.get("conversation_id")
    convo = get_object_or_404(ChatConversation, pk=conversation_id, user=request.user)

    sls = ShoppingListSession.objects.create(
        user=request.user, conversation=convo, status="NS"
    )
    sls_id = sls.id

    try:
        bot = CookinBookBot()
        purchase_result = bot.handle_purchase(items, sls_id)
        saved_items = items
        if isinstance(purchase_result, dict) and purchase_result.get("items"):
            saved_items = purchase_result["items"]
        saved_recipe = _persist_session_recipe(sls, recipe_data)
        _persist_session_items(sls, saved_items, recipe=saved_recipe)
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
    orders = _history_orders_for_user(request.user)

    return render(request, "main/orders/list.html", {"orders": orders})


@login_required
def order_detail(request, session_id):
    order = get_object_or_404(
        ShoppingListSession.objects.select_related("conversation").prefetch_related(
            "items", "recipes"
        ),
        id=session_id,
        user=request.user,
    )
    order = _decorate_order(order)
    items = order.prefetched_items

    profile = getattr(request.user, "profile", None)

    address = _format_profile_address(profile) or "N/A"

    estimated_delivery = None
    if order.created_at and order.order_status != "D":
        estimated_delivery = order.created_at + timedelta(days=3)

    return render(
        request,
        "main/orders/detail.html",
        {
            "order": order,
            "items": items,
            "address": address,
            "estimated_delivery": estimated_delivery,
        },
    )
