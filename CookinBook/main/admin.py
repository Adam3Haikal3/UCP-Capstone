from django.contrib import admin
from .models import (
    Profile,
    ChatConversation,
    ChatMessage,
    Recipe,
    ShoppingListSession,
    ShoppingListItem,
)

admin.site.register(Profile)
admin.site.register(ChatConversation)
admin.site.register(ChatMessage)
admin.site.register(Recipe)
admin.site.register(ShoppingListSession)
admin.site.register(ShoppingListItem)
