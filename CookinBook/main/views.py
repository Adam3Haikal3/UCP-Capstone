from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from .forms import SignUpForm
from .models import ChatConversation, ChatMessage
from gemini_wrapper.client import CookinBookBot
import json
import logging

logger = logging.getLogger(__name__)


# Create your views here.
def chat_view(request):
    return render(request, "main/chat/chat.html")


def home_view(request):
    if request.user.is_authenticated:
        return redirect("chat")
    return render(request, "main/home/home.html")


@require_POST
def chat_send(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message is empty"}, status=400)

    conversation_id = data.get("conversation_id")
    if conversation_id:
        try:
            conversation = ChatConversation.objects.get(
                id=conversation_id, user=request.user
            )
        except ChatConversation.DoesNotExist:
            return JsonResponse({"error": "Conversation not found"}, status=404)
    else:
        conversation = ChatConversation.objects.create(user=request.user)

    ChatMessage.objects.create(
        conversation=conversation,
        sender="U",
        content=user_message,
    )

    try:
        bot = CookinBookBot()
        bot_reply = bot.send_message(user_message)
    except Exception:
        logger.exception("Error while sending message to CookinBookBot")
        return JsonResponse(
            {"error": "Failed to get a response from the assistant."}, status=500
        )

    ChatMessage.objects.create(
        conversation=conversation,
        sender="B",
        content=bot_reply,
    )

    return JsonResponse({"response": bot_reply, "conversation_id": conversation.id})


@login_required
def history_view(request):
    return render(request, "main/history/history.html")


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
            form.save()  # Saves the user to the database
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password1")
            user = authenticate(username=username, password=password)
            login(request, user)  # Log the user in immediately
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
