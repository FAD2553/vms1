from .models import LogAction


def log_action(admin_user, action, details, entite_id=None):
    """Create an audit log entry."""
    LogAction.objects.create(
        action=action,
        details=details,
        entite_id=entite_id,
        admin=admin_user
    )
