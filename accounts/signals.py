import logging
from django.db import transaction
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from .models import User

logger = logging.getLogger(__name__)


def delete_unused(storage, name):
    if name and not User.objects.filter(avatar=name).exists():
        try:
            storage.delete(name)
        except OSError:
            logger.exception('Unable to remove unused avatar')


@receiver(pre_save, sender=User)
def remove_previous_avatar(sender, instance, update_fields=None, **kwargs):
    if not instance.pk or (update_fields is not None and 'avatar' not in update_fields):
        return
    old = sender.objects.filter(pk=instance.pk).values_list('avatar', flat=True).first()
    if old and old != instance.avatar.name:
        storage = instance.avatar.storage
        transaction.on_commit(lambda: delete_unused(storage, old))


@receiver(post_delete, sender=User)
def remove_deleted_avatar(sender, instance, **kwargs):
    name, storage = instance.avatar.name, instance.avatar.storage
    transaction.on_commit(lambda: delete_unused(storage, name))
