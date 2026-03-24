from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("chat/", views.chat_view, name="chat"),
    path("history/", views.history_view, name="history"),
    path("chat/<int:conversation_id>/", views.chat_view, name="chat_conversation"),
    path("chat/send/", views.chat_send, name="chat_send"),
    path("api/conversations/", views.conversation_list, name="conversation_list"),
    path(
        "api/conversations/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation_detail",
    ),
    path(
        "api/conversations/<int:conversation_id>/delete/",
        views.conversation_delete,
        name="conversation_delete",
    ),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("profile/", views.profile_view, name="profile"),
    path("logout/", views.logout_view, name="logout"),
]
