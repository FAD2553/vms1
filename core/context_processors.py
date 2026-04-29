from django.utils import timezone
from django.contrib.auth.models import User
from .models import Visiteur, Service, Visite, Porte, AgentProfile

def report_context(request):
    if request.user.is_authenticated:
        # Alerte visites > 5h (Visites trop longues sans sortie)
        threshold = timezone.now() - timezone.timedelta(hours=5)
        long_visites_query = Visite.objects.filter(statut='PRESENT', heure_entree__lt=threshold)
        
        if not request.user.is_superuser:
            try:
                porte = request.user.profile.porte_actuelle
                if not porte:
                    # Si l'agent n'a pas de porte, il ne reçoit pas d'alertes
                    long_visites_query = Visite.objects.none()
            except AgentProfile.DoesNotExist:
                long_visites_query = Visite.objects.none()
            
        return {
            'all_visiteurs': Visiteur.objects.filter(is_archived=False).order_by('nom'),
            'all_services': Service.objects.all().order_by('nom'),
            'all_portes': Porte.objects.all().order_by('numero'),
            'all_agents': User.objects.filter(is_superuser=False).order_by('username'),
            'nb_alertes': long_visites_query.count(),
            'alertes_visites': long_visites_query,
        }
    return {}
