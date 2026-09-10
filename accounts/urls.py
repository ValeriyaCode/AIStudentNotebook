from django.urls import path
from . import views, group_views

urlpatterns = [
    path('students/<int:student_id>/edit/', group_views.student_edit, name='student_edit'),
    path('groups/<int:group_id>/action/', group_views.group_action, name='group_action'),
    path('groups/<int:group_id>/credentials/', group_views.group_credentials, name='group_credentials'),
    path('groups/new/', group_views.group_create, name='group_create'),
    path('groups/<int:group_id>/', group_views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/students/<int:student_id>/', group_views.student_action, name='student_action'),
    path('register/', views.register, name='register'),
]
