from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='juego/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('dificultad/', views.seleccionar_dificultad, name='seleccionar_dificultad'),
    path('juego/', views.juego_memoria, name='juego_memoria'),
    path('juego/ajax/', views.juego_ajax, name='juego_ajax'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
]