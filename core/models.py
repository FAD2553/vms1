from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

private_storage = FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


class Porte(models.Model):
    numero = models.CharField(max_length=20, unique=True, verbose_name="Numéro de porte")
    description = models.TextField(blank=True, null=True, verbose_name="Description / Localisation")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Porte"
        verbose_name_plural = "Portes"

    def __str__(self):
        return f"Porte {self.numero}"

    @property
    def total_visites(self):
        return self.visites.count()

    @property
    def presents_actuels(self):
        return self.visites.filter(statut='PRESENT').count()


class AgentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    porte_actuelle = models.ForeignKey(
        Porte, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='agents_affectes', verbose_name="Porte d'affectation"
    )

    class Meta:
        verbose_name = "Profil Agent"
        verbose_name_plural = "Profils Agents"

    def __str__(self):
        return f"Profil de {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        AgentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except AgentProfile.DoesNotExist:
        AgentProfile.objects.create(user=instance)


class Visiteur(models.Model):
    nom = models.CharField(max_length=50, verbose_name="Nom")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    numero_cni = models.CharField(max_length=50, unique=True, verbose_name="Numéro CNIB")
    date_naissance = models.DateField(verbose_name="Date de naissance")
    sexe = models.CharField(max_length=10, choices=[('M', 'Masculin'), ('F', 'Féminin')], blank=True, null=True, verbose_name="Sexe")
    profession = models.CharField(max_length=100, blank=True, null=True, verbose_name="Profession")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    adresse = models.TextField(verbose_name="Adresse", blank=True, null=True)
    scan_cni_recto = models.ImageField(
        upload_to='cni_scans/',
        storage=private_storage,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        verbose_name="Scan CNIB Recto",
        blank=True, null=True
    )
    scan_cni_verso = models.ImageField(
        upload_to='cni_scans/',
        storage=private_storage,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        verbose_name="Scan CNIB Verso",
        blank=True, null=True
    )
    date_enregistrement = models.DateTimeField(auto_now_add=True, verbose_name="Date d'enregistrement")
    is_archived = models.BooleanField(default=False, verbose_name="Archive")

    class Meta:
        ordering = ['-date_enregistrement']
        verbose_name = "Visiteur"
        verbose_name_plural = "Visiteurs"

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.numero_cni})"

    @property
    def nombre_visites_total(self):
        return self.visites.count()

    @property
    def derniere_visite(self):
        last = self.visites.order_by('-heure_entree').first()
        return last.heure_entree if last else None

    @property
    def est_present(self):
        return self.visites.filter(statut='PRESENT').exists()


class Service(models.Model):
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du Service")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return self.nom


STATUT_VISITE_CHOICES = [
    ('PRESENT', 'Présent'),
    ('SORTI', 'Sorti'),
]


class Visite(models.Model):
    visiteur = models.ForeignKey(
        Visiteur, on_delete=models.CASCADE, related_name='visites', verbose_name="Visiteur"
    )
    service_visite = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name='visites', verbose_name="Service visité"
    )
    porte = models.ForeignKey(
        Porte, on_delete=models.PROTECT, related_name='visites', verbose_name="Porte d'entrée/sortie"
    )
    agent_entree = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='visites_entrees', verbose_name="Agent d'entrée"
    )
    agent_sortie = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='visites_sorties', verbose_name="Agent de sortie"
    )
    motif = models.CharField(max_length=255, verbose_name="Motif de la visite")
    date_visite = models.DateField(default=timezone.now, verbose_name="Date")
    heure_entree = models.DateTimeField(default=timezone.now, verbose_name="Heure d'entrée")
    heure_sortie = models.DateTimeField(blank=True, null=True, verbose_name="Heure de sortie")
    statut = models.CharField(
        max_length=15, choices=STATUT_VISITE_CHOICES, default='PRESENT', verbose_name="Statut"
    )
    observations = models.TextField(blank=True, null=True, verbose_name="Observations")

    class Meta:
        ordering = ['-heure_entree']
        verbose_name = "Visite"
        verbose_name_plural = "Visites"

    def __str__(self):
        return f"Visite de {self.visiteur} (Porte {self.porte.numero})"

    @property
    def duree_visite(self):
        if self.heure_entree:
            end_time = self.heure_sortie if self.heure_sortie else timezone.now()
            diff = end_time - self.heure_entree
            hours, remainder = divmod(diff.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                return f"{int(hours)}h {int(minutes)}min"
            return f"{int(minutes)} min"
        return "N/A"

    @property
    def est_trop_longue(self):
        if self.heure_entree and not self.heure_sortie:
            diff = timezone.now() - self.heure_entree
            return diff.total_seconds() > 18000  # 5 heures
        return False


ACTION_CHOICES = [
    ('CREATION_VISITEUR', 'Création visiteur'),
    ('MODIFICATION_VISITEUR', 'Modification visiteur'),
    ('ARCHIVAGE_VISITEUR', 'Archivage visiteur'),
    ('CREATION_VISITE', 'Entrée visiteur'),
    ('SORTIE_VISITE', 'Sortie visiteur'),
    ('CONSULTATION_CNIB', 'Consultation CNIB'),
    ('CONNEXION', 'Connexion'),
    ('DECONNEXION', 'Déconnexion'),
    ('CREATION_USER', 'Création utilisateur'),
    ('MODIFICATION_USER', 'Modification utilisateur'),
    ('ACTIVATION_USER', 'Activation compte'),
    ('DESACTIVATION_USER', 'Désactivation compte'),
    ('RESET_PASSWORD', 'Réinitialisation mot de passe'),
    ('AFFECTATION_PORTE', 'Affectation à une porte'),
]


class LogAction(models.Model):
    action = models.CharField(max_length=50, verbose_name="Action")
    date_heure = models.DateTimeField(auto_now_add=True, verbose_name="Date et heure")
    details = models.TextField(verbose_name="Détails")
    entite_id = models.IntegerField(blank=True, null=True, verbose_name="ID entité")
    admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='logs', verbose_name="Administrateur"
    )

    class Meta:
        ordering = ['-date_heure']
        verbose_name = "Log"
        verbose_name_plural = "Logs"

    def __str__(self):
        return f"{self.action} - {self.date_heure.strftime('%d/%m/%Y %H:%M')}"


class Archive(models.Model):
    type_entite = models.CharField(max_length=50, verbose_name="Type d'entité")
    donnees_json = models.JSONField(verbose_name="Données archivées")
    date_archivage = models.DateTimeField(auto_now_add=True, verbose_name="Date d'archivage")
    admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='archives', verbose_name="Administrateur"
    )

    class Meta:
        ordering = ['-date_archivage']
        verbose_name = "Archive"
        verbose_name_plural = "Archives"

    def __str__(self):
        return f"Archive {self.type_entite} #{self.id} - {self.date_archivage.strftime('%d/%m/%Y')}"
