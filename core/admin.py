from django.contrib import admin
from .models import Visiteur, Service, Visite, LogAction, Archive

@admin.register(Visiteur)
class VisiteurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'numero_cni', 'telephone', 'date_enregistrement', 'is_archived')
    search_fields = ('nom', 'prenom', 'numero_cni')
    list_filter = ('is_archived', 'date_enregistrement')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)

@admin.register(Visite)
class VisiteAdmin(admin.ModelAdmin):
    list_display = ('visiteur', 'service_visite', 'porte_entree', 'porte_sortie', 'date_visite', 'heure_entree', 'heure_sortie', 'statut')
    list_filter = ('statut', 'date_visite', 'service_visite')
    search_fields = ('visiteur__nom', 'visiteur__prenom', 'motif')

@admin.register(LogAction)
class LogActionAdmin(admin.ModelAdmin):
    list_display = ('action', 'date_heure', 'details', 'entite_id', 'admin')
    list_filter = ('action', 'date_heure')
    readonly_fields = ('action', 'date_heure', 'details', 'entite_id', 'admin')

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ('type_entite', 'date_archivage', 'admin')
    list_filter = ('type_entite', 'date_archivage')
    readonly_fields = ('type_entite', 'donnees_json', 'date_archivage', 'admin')
