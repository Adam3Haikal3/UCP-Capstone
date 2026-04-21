from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Auto-create a Profile row whenever a new User is created."""
    if created:
        Profile.objects.get_or_create(user=instance)
