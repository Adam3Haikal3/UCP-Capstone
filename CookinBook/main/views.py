from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignUpForm
from django.contrib import messages
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST


# Create your views here.
def chat_view(request):
    return render(request, "main/chat/chat.html")
def home_view(request):
    return render(request, "main/home/home.html")
@require_POST
def chat_send(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = (data.get("message") or "").strip()
    if not user_message:
        return JsonResponse({"error": "Message is empty"}, status=400)

    #replace later with AI call, recipe search, database lookup
    reply = f"You said: {user_message}"
    return JsonResponse({"reply": reply})



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


def profile_view(request):
    return render(request, "main/users/profile/profile.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect("chat")
