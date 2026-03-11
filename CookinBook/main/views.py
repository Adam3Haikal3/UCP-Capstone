from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import ChatConversation, ChatMessage
from django.contrib import messages
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET


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

    # Placeholder reply — replace with AI call later
    reply = f"You said: {user_message}"

    ChatMessage.objects.create(conversation=convo, sender="B", content=reply)

    convo.artifact_content = reply
    convo.save()

    return JsonResponse({
        "reply": reply,
        "conversation_id": convo.pk,
        "conversation_title": convo.title,
        "artifact_content": convo.artifact_content,
    })


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
    convo = get_object_or_404(
        ChatConversation, pk=conversation_id, user=request.user
    )
    msgs = list(
        convo.messages.values("sender", "content", "sent_at")
    )
    return JsonResponse({
        "id": convo.pk,
        "title": convo.title,
        "artifact_content": convo.artifact_content,
        "messages": msgs,
    })


@require_POST
@login_required
def conversation_delete(request, conversation_id):
    convo = get_object_or_404(
        ChatConversation, pk=conversation_id, user=request.user
    )
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
            messages.success(
                request, f"Welcome, {username}! Your account was created."
            )
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
