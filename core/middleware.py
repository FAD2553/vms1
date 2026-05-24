import time
from django.contrib.auth.models import User
from core.utils import log_action

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        is_explicit_logout = request.path == '/logout/'

        if user.is_authenticated:
            # L'utilisateur est connecté, on définit un cookie signé pour mémoriser son nom d'utilisateur
            response = self.get_response(request)
            response.set_signed_cookie('last_active_user', user.username, max_age=86400)  # 1 jour
            return response
        else:
            # L'utilisateur est anonyme, vérifions s'il a le cookie signed de sa dernière session active
            try:
                last_username = request.get_signed_cookie('last_active_user', default=None)
            except Exception:
                last_username = None

            if last_username and not is_explicit_logout:
                try:
                    old_user = User.objects.get(username=last_username)
                    # Enregistrement de la déconnexion automatique dans le journal des actions
                    log_action(
                        old_user,
                        'DECONNEXION_AUTO',
                        f"Déconnexion automatique de l'utilisateur {old_user.username} après 30 minutes d'inactivité.",
                        None
                    )
                except User.DoesNotExist:
                    pass

                # On génère la réponse et on nettoie le cookie pour éviter de consigner l'action plusieurs fois
                response = self.get_response(request)
                response.delete_cookie('last_active_user')
                return response

        return self.get_response(request)
