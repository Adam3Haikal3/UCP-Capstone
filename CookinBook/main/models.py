from django.db import models

# Create your models here.
class User(models.Model):
    user_id = models.IntegerField(primary_key=True)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=128)
    birth_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True) # Value will be set once object is first created

class ChatConversation(models.Model):
    conversation_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) # Value will be updated when object is updated

class ChatMessage(models.Model):
    SENDER = {
        "B": "Bot",
        "U": "User"
    }

    message_id = models.IntegerField(primary_key=True)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    sender = models.CharField(max_length=1, choices=SENDER)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True) 

class Recipe(models.Model):
    recipe_id = models.IntegerField(primary_key=True)
    elasticsearch_id = models.IntegerField()
    title = models.CharField(max_length=100)
    cached_at = models.DateTimeField(auto_now=True)

class ShoppingListSession(models.Model):
    STATUS = {
        "NS": "NotStarted",
        "IP": "InProgress",
        "C" : "Completed"
    }

    ORDER_STATUS = {
        "OF": "OrderFinalized",
        "D" : "Delivered"
    }

    session_id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE)
    recipe = models.ManyToManyField(Recipe) # This might need to be a one-to-many relationship
    total_cost = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS)
    order_status = models.CharField(max_length=2, choices=ORDER_STATUS)

class ShoppingListItem(models.Model):
    item_id = models.IntegerField(primary_key=True)
    session = models.ForeignKey(ShoppingListSession, on_delete=models.CASCADE)
    ingredient_name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    retailer = models.CharField(max_length=50)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20)
