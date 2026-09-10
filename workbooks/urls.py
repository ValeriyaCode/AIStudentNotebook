from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('page/<int:page_id>/', views.page_detail, name='page_detail'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/workbook/<int:workbook_id>/', views.admin_student_workbook, name='admin_student_workbook'),
]
