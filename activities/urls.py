from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('create/', views.activity_create, name='activity_create'),
    path('<str:pk>/', views.activity_detail, name='activity_detail'),
    path('<str:pk>/update/', views.activity_update, name='activity_update'),
    path('<str:pk>/delete/', views.activity_delete, name='activity_delete'),
]
