from .models import LogAction


def log_action(admin_user, action, details, entite_id=None):
    """Crée une entrée dans le journal d'audit."""
    LogAction.objects.create(
        action=action,
        details=details,
        entite_id=entite_id,
        admin=admin_user
    )
