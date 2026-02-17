# home/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("", views.home_view, name="home"),
  # Redirect to chat page on startup
    path("chat/", views.chat_view, name="chat"),
    path("chat/send/", views.chat_send, name="chat_send"),
    path("history/", views.history_view, name="history"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("profile/", views.profile_view, name="profile"),
    path("logout/", LogoutView.as_view(next_page="chat"), name="logout"),
]
