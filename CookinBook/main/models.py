from django.db import models
from django.contrib.auth.models import User  # Use Django's built-in User


class Profile(models.Model):
    """Extends Django's built-in User with app-specific fields."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    birth_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class ChatConversation(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations"
    )
    title = models.CharField(max_length=255, blank=True, default="New Chat")
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class ChatMessage(models.Model):
    SENDER_CHOICES = {
        "B": "Bot",
        "U": "User",
    }

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.CharField(max_length=1, choices=SENDER_CHOICES)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]

    def __str__(self):
        return f"[{self.get_sender_display()}] {self.content[:50]}"


class Recipe(models.Model):
    elasticsearch_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    ingredients = models.JSONField(default=list, blank=True)
    instructions = models.TextField(blank=True, default="")
    cook_time = models.CharField(max_length=50, blank=True, default="")
    servings = models.PositiveIntegerField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ShoppingListSession(models.Model):
    STATUS_CHOICES = {
        "NS": "Not Started",
        "IP": "In Progress",
        "C": "Completed",
    }
    ORDER_STATUS_CHOICES = {
        "P": "Pending",
        "OF": "Order Finalized",
        "D": "Delivered",
    }
    DELIVERY_CHOICES = {
        "P": "Pickup",
        "D": "Delivery",
    }

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shopping_sessions"
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="shopping_sessions",
    )
    recipes = models.ManyToManyField(
        Recipe, blank=True, related_name="shopping_sessions"
    )
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default="NS")
    order_status = models.CharField(
        max_length=2, choices=ORDER_STATUS_CHOICES, default="P", blank=True
    )
    delivery_method = models.CharField(
        max_length=1, choices=DELIVERY_CHOICES, blank=True, default=""
    )
    ucp_transaction_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session #{self.pk} - {self.user.username}"


class ShoppingListItem(models.Model):
    session = models.ForeignKey(
        ShoppingListSession, on_delete=models.CASCADE, related_name="items"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shopping_items",
    )
    ingredient_name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    retailer = models.CharField(max_length=100, blank=True, default="")
    is_available = models.BooleanField(default=True)
    purchased_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient_name}"
