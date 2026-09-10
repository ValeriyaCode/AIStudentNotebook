from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Роль у застосунку', {'fields': ('role', 'study_group')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Роль у застосунку', {'fields': ('role', 'study_group')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
