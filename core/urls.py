from django.urls import path
from . import views

urlpatterns = [
    # Authentification
    path('login/', views.login_view, name='login'),
    path('login/2fa/', views.login_2fa, name='login_2fa'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/2fa/', views.profile_2fa_setup, name='profile_2fa_setup'),
    path('profile/2fa/verify/', views.profile_2fa_verify, name='profile_2fa_verify'),
    path('profile/2fa/disable/', views.profile_2fa_disable, name='profile_2fa_disable'),

    # Tableau de bord
    path('', views.dashboard, name='dashboard'),

    # Visiteurs
    path('visiteurs/', views.visiteur_list, name='visiteur_list'),
    path('visiteurs/nouveau/', views.visiteur_create, name='visiteur_create'),
    path('visiteurs/<int:pk>/', views.visiteur_detail, name='visiteur_detail'),
    path('visiteurs/<int:pk>/modifier/', views.visiteur_edit, name='visiteur_edit'),
    path('visiteurs/<int:pk>/archiver/', views.visiteur_archive, name='visiteur_archive'),
    path('visiteurs/<int:pk>/desarchiver-quick/', views.visiteur_desarchiver_quick, name='visiteur_desarchiver_quick'),
    path('visiteurs/check-cnib/', views.check_cnib, name='check_cnib'),
    path('visiteurs/<int:pk>/cnib/<str:side>/', views.visiteur_cnib_view, name='visiteur_cnib_view'),
    path('ocr/scan/', views.ocr_scan, name='ocr_scan'),

    # Visites
    path('visites/', views.visite_list, name='visite_list'),
    path('visites/nouvelle/', views.visite_create, name='visite_create'),
    path('visites/<int:pk>/', views.visite_detail, name='visite_detail'),
    path('visites/<int:pk>/sortie/', views.visite_sortie, name='visite_sortie'),

    # Services
    path('services/', views.service_list, name='service_list'),
    path('services/nouveau/', views.service_create, name='service_create'),
    path('services/<int:pk>/', views.service_detail, name='service_detail'),
    path('services/<int:pk>/modifier/', views.service_edit, name='service_edit'),
    path('services/<int:pk>/archiver/', views.service_archive, name='service_archive'),

    # Portes
    path('portes/', views.porte_list, name='porte_list'),
    path('portes/nouveau/', views.porte_create, name='porte_create'),
    path('portes/<int:pk>/', views.porte_detail, name='porte_detail'),
    path('portes/<int:pk>/modifier/', views.porte_edit, name='porte_edit'),

    # PDF & Rapports
    path('pdf/rapport-visites/', views.pdf_rapport_visites, name='pdf_rapport_visites'),
    path('pdf/journal-audit/', views.pdf_log_list, name='pdf_log_list'),

    # Journaux & Archives
    path('logs/', views.log_list, name='log_list'),
    path('archives/', views.archive_list, name='archive_list'),
    path('archives/<int:pk>/restaurer/', views.archive_restore, name='archive_restore'),

    # Gestion des utilisateurs
    path('users/', views.user_list, name='user_list'),
    path('users/nouveau/', views.user_create, name='user_create'),
    path('users/<int:pk>/modifier/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/supprimer/', views.user_toggle_status, name='user_toggle_status'),
    path('users/<int:pk>/reset-password/', views.user_password_reset, name='user_password_reset'),
    path('users/<int:pk>/disable-2fa/', views.user_disable_2fa, name='user_disable_2fa'),

    # Captures caméra (Admin Secours uniquement)
    path('captures-camera/', views.captures_camera_view, name='captures_camera'),
    path('captures-camera/supprimer/<str:filename>/', views.delete_capture_view, name='delete_capture'),

    # Route to dismiss the 2FA warning banner
    path('dismiss-2fa-warning/', views.dismiss_2fa_warning, name='dismiss_2fa_warning'),
]
