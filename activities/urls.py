from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('create/', views.activity_create, name='activity_create'),
    path('report/excel/', views.generate_excel_report, name='generate_excel_report'),
    path('report/pdf/', views.generate_pdf_report, name='generate_pdf_report'),
    # Activity detail, update, delete using slug
    path('<slug:slug>/', views.activity_detail, name='activity_detail'),
    path('<slug:slug>/update/', views.activity_update, name='activity_update'),
    path('<slug:slug>/delete/', views.activity_delete, name='activity_delete'),
    # Todo operations (HTMX) - using slug
    path('<slug:slug>/todo/add/', views.add_todo, name='add_todo'),
    path('<slug:slug>/todo/<int:todo_index>/remove/', views.remove_todo, name='remove_todo'),
    path('<slug:slug>/todo/<int:todo_index>/toggle/', views.toggle_todo, name='toggle_todo'),
]
