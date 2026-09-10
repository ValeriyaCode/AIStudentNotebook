from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Учень'
        ADMIN = 'admin', 'Адміністратор'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    study_group = models.ForeignKey('StudyGroup', null=True, blank=True, on_delete=models.SET_NULL, related_name='students')

    issued_password = models.TextField(blank=True, editable=False)

    avatar = models.ImageField(upload_to='avatars/', blank=True)

    @property
    def is_admin_user(self):
        return self.is_staff or self.role == self.Role.ADMIN


class StudyGroup(models.Model):
    name = models.CharField(max_length=200)
    start_date = models.DateField()
    teacher = models.ForeignKey(User, on_delete=models.PROTECT, related_name='teaching_groups')
    template = models.ForeignKey('workbooks.WorkbookTemplate', on_delete=models.PROTECT)
    open_pages = models.ManyToManyField('workbooks.WorkbookPage', blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return self.name


class SubmissionReceipt(models.Model):
    token = models.UUIDField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    scope = models.CharField(max_length=100)
    group = models.ForeignKey(StudyGroup, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
