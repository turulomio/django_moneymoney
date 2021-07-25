from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def after_user_creation(sender, instance, created, **kwargs):
    if created:
        b=Bank()
        b.name="Personal management"
        b.active=True
        b.save()