from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Учень'
        ADMIN = 'admin', 'Адміністратор'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    @property
    def is_admin_user(self):
        return self.is_staff or self.role == self.Role.ADMIN
