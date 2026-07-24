import json
import os
import tempfile
from datetime import datetime, date, timedelta
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.conf import settings
from xhtml2pdf import pisa

from django.contrib.auth.models import User
import secrets
import string
from .models import Visiteur, Visite, Service, LogAction, Archive, Porte, AgentProfile
from .forms import (
    VisiteurForm, VisiteurEditForm, VisiteForm, ServiceForm, 
    RapportVisiteForm, UserRegistrationForm, PorteForm
)
from .utils import log_action
from .ocr import extract_cnib_info


# ============================================================
# AUTHENTIFICATION
# ============================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            # Vérifier si le 2FA est activé pour cet utilisateur
            try:
                profile = user.profile
                two_factor = profile.two_factor_enabled
            except Exception:
                two_factor = False

            if two_factor:
                # Stocker l'ID de l'utilisateur dans la session et rediriger vers la page 2FA
                request.session['pre_2fa_user_id'] = user.id
                return redirect('login_2fa')
            
            login(request, user)
            log_action(user, 'CONNEXION', f"L'utilisateur {u} s'est connecté.")
            return redirect('dashboard')
        else:
            messages.error(request, "Identifiants invalides.")
    return render(request, 'core/login.html')


def login_2fa(request):
    import pyotp
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        try:
            profile = user.profile
            secret = profile.two_factor_secret
        except Exception:
            secret = None

        if secret:
            totp = pyotp.TOTP(secret)
            if totp.verify(code):
                login(request, user)
                if 'pre_2fa_user_id' in request.session:
                    del request.session['pre_2fa_user_id']
                log_action(user, 'CONNEXION', f"L'utilisateur {user.username} s'est connecté (2FA).")
                messages.success(request, f"Connexion réussie ! Bienvenue {user.username}.")
                return redirect('dashboard')
            else:
                log_action(user, 'CONNEXION_2FA_ECHEC', f"Échec de connexion 2FA (code invalide) pour {user.username}.", None)
                messages.error(request, "Code Google Authenticator invalide. Veuillez réessayer.")
        else:
            messages.error(request, "Configuration 2FA manquante. Veuillez contacter l'administrateur.")
            return redirect('login')

    return render(request, 'core/login_2fa.html')


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'DECONNEXION', f"L'utilisateur {request.user.username} s'est déconnecté.")
    logout(request)
    return redirect('login')


@login_required
def profile_2fa_setup(request):
    if request.user.username == 'admin_secours':
        return redirect('dashboard')
    import pyotp
    import qrcode
    import io
    import base64

    try:
        profile = request.user.profile
    except Exception:
        profile = AgentProfile.objects.create(user=request.user)

    if profile.two_factor_enabled:
        return render(request, 'core/profile_2fa_setup.html', {
            'enabled': True
        })

    secret = request.session.get('two_factor_setup_secret')
    if not secret:
        secret = pyotp.random_base32()
        request.session['two_factor_setup_secret'] = secret

    totp = pyotp.TOTP(secret)
    provisioning_url = totp.provisioning_uri(
        name=request.user.email or request.user.username,
        issuer_name="UWaZy VMS"
    )

    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(provisioning_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_code_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render(request, 'core/profile_2fa_setup.html', {
        'enabled': False,
        'secret': secret,
        'qr_code': qr_code_base64
    })


@login_required
def profile_2fa_verify(request):
    if request.user.username == 'admin_secours':
        return redirect('dashboard')
    import pyotp
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        secret = request.session.get('two_factor_setup_secret')

        if not secret:
            messages.error(request, "Session de configuration expirée. Veuillez recommencer.")
            return redirect('profile_2fa_setup')

        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            try:
                profile = request.user.profile
            except Exception:
                profile = AgentProfile.objects.create(user=request.user)

            profile.two_factor_secret = secret
            profile.two_factor_enabled = True
            profile.save()

            if 'two_factor_setup_secret' in request.session:
                del request.session['two_factor_setup_secret']

            log_action(request.user, 'ACTIVER_2FA', f"Double facteur activé pour {request.user.username}.", None)
            messages.success(request, "Félicitations ! L'authentification à double facteur (2FA) est maintenant activée.")
        else:
            messages.error(request, "Code de validation invalide. Veuillez réessayer.")

    return redirect('profile_2fa_setup')


@login_required
def profile_2fa_disable(request):
    if request.user.username == 'admin_secours':
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            profile = request.user.profile
            profile.two_factor_enabled = False
            profile.two_factor_secret = None
            profile.save()
            log_action(request.user, 'DESACTIVER_2FA', f"Double facteur désactivé pour {request.user.username}.", None)
            messages.warning(request, "L'authentification à double facteur (2FA) a été désactivée de votre compte.")
        except Exception:
            pass
    return redirect('profile_2fa_setup')


# ============================================================
# TABLEAU DE BORD
# ============================================================

@login_required
def dashboard(request):
    now = timezone.now()
    today = now.date()
    
    # Base Visites pour filtrage selon l'utilisateur
    visites_base = Visite.objects.all()
    porte_actuelle = None
    
    if not request.user.is_superuser:
        try:
            porte_actuelle = request.user.profile.porte_actuelle
            if not porte_actuelle:
                # Si l'agent n'a pas de porte assignée, il ne voit que les présents par sécurité
                visites_base = Visite.objects.filter(statut='PRESENT')
        except AgentProfile.DoesNotExist:
            visites_base = Visite.objects.filter(statut='PRESENT')
    
    # 1. Stats de base
    total_visiteurs = Visiteur.objects.filter(is_archived=False).count()
    visiteurs_presents = Visite.objects.filter(statut='PRESENT').count()
    if porte_actuelle:
        visites_aujourdhui = Visite.objects.filter(
            Q(porte_entree=porte_actuelle) | Q(porte_sortie=porte_actuelle),
            date_visite=today
        ).count()
    else:
        visites_aujourdhui = Visite.objects.filter(date_visite=today).count() if request.user.is_superuser else 0
    total_services = Service.objects.filter(is_archived=False).count()
    total_portes = Porte.objects.filter(is_archived=False).count()
    
    # Stats Agents (Admin Only)
    total_agents = User.objects.exclude(profile__is_archived=True).filter(is_superuser=False).count() if request.user.is_superuser else 0
    active_agents = User.objects.exclude(profile__is_archived=True).filter(is_superuser=False, is_active=True).count() if request.user.is_superuser else 0
    sorties_aujourdhui = Visite.objects.filter(statut='SORTI', heure_sortie__date=today).count() if request.user.is_superuser else 0
    
    # 2. Graphiques
    # Visites par heure (Aujourd'hui)
    daily_labels = [f"{i}h" for i in range(24)]
    daily_data = [0] * 24
    daily_stats = visites_base.filter(date_visite=today).values('heure_entree__hour').annotate(count=Count('id'))
    for stat in daily_stats:
        hour = stat['heure_entree__hour']
        if hour is not None:
            daily_data[hour] = stat['count']
    
    # Répartition par service (Top 5)
    service_stats = visites_base.values('service_visite__nom').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    service_labels = [s['service_visite__nom'] or "Inconnu" for s in service_stats]
    service_data = [s['count'] for s in service_stats]
    total_s = sum(service_data) or 1
    service_percents = [round((s / total_s) * 100, 1) for s in service_data]

    # Stats hebdo (7 derniers jours)
    last_week = today - timedelta(days=6)
    weekly_labels = [(last_week + timedelta(days=i)).strftime('%d/%m') for i in range(7)]
    weekly_data = [0] * 7
    weekly_stats = visites_base.filter(date_visite__gte=last_week).values('date_visite').annotate(
        count=Count('id')
    ).order_by('date_visite')
    
    weekly_dict = {s['date_visite'].strftime('%d/%m'): s['count'] for s in weekly_stats}
    for i, label in enumerate(weekly_labels):
        weekly_data[i] = weekly_dict.get(label, 0)

    # Stats Mensuelles (Année en cours)
    monthly_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    monthly_data = [0] * 12
    monthly_stats = visites_base.filter(date_visite__year=today.year).annotate(
        month=TruncMonth('date_visite')
    ).values('month').annotate(count=Count('id'))
    
    for stat in monthly_stats:
        m_idx = stat['month'].month - 1
        monthly_data[m_idx] = stat['count']

    # Stats Annuelles (5 dernières années)
    yearly_labels = [str(today.year - i) for i in range(4, -1, -1)]
    yearly_data = [0] * 5
    yearly_stats = visites_base.filter(date_visite__year__gte=today.year - 4).values('date_visite__year').annotate(
        count=Count('id')
    ).order_by('date_visite__year')
    
    yearly_dict = {str(s['date_visite__year']): s['count'] for s in yearly_stats}
    for i, year in enumerate(yearly_labels):
        yearly_data[i] = yearly_dict.get(year, 0)

    # 3. Listes récentes filtrées
    visites_sur_place = visites_base.filter(statut='PRESENT').select_related('visiteur', 'service_visite').order_by('-heure_entree')[:10]
    recent_visites = visites_base.select_related('visiteur', 'service_visite').order_by('-heure_entree')[:10]

    # Agents en ligne (ayant agi dans les 15 dernières minutes, excluant les admins)
    fifteen_minutes_ago = now - timedelta(minutes=15)
    agents_en_ligne = LogAction.objects.filter(
        date_heure__gte=fifteen_minutes_ago,
        admin__is_superuser=False
    ).values('admin').distinct().count()

    show_2fa_warning = False
    if request.user.username != 'admin_secours' and not request.session.get('dismissed_2fa_warning', False):
        try:
            profile = request.user.profile
            if not profile.two_factor_enabled:
                show_2fa_warning = True
        except Exception:
            show_2fa_warning = True

    if request.GET.get('format') == 'json':
        visites_sur_place_json = []
        for v in visites_sur_place:
            visites_sur_place_json.append({
                'pk': v.pk,
                'visiteur': f"{v.visiteur.prenom} {v.visiteur.nom}",
                'visiteur_pk': v.visiteur.pk,
                'visiteur_cni': v.visiteur.numero_cni,
                'service': v.service_visite.nom if v.service_visite else "Aucun",
                'heure_entree': v.heure_entree.astimezone(timezone.get_current_timezone()).strftime('%H:%M') if v.heure_entree else "",
                'sortie_url': reverse('visite_sortie', kwargs={'pk': v.pk}),
            })

        recent_visites_json = []
        for v in recent_visites:
            recent_visites_json.append({
                'pk': v.pk,
                'visiteur': f"{v.visiteur.prenom} {v.visiteur.nom}",
                'visiteur_pk': v.visiteur.pk,
                'service': v.service_visite.nom if v.service_visite else "Aucun",
                'porte_entree': v.porte_entree.numero if v.porte_entree else "",
                'heure_entree': v.heure_entree.astimezone(timezone.get_current_timezone()).strftime('%d/%m %H:%M') if v.heure_entree else "",
                'statut': v.statut,
                'visiteur_detail_url': reverse('visiteur_detail', kwargs={'pk': v.visiteur.pk}),
            })

        return JsonResponse({
            'total_visiteurs': total_visiteurs,
            'visiteurs_presents': visiteurs_presents,
            'visites_aujourdhui': visites_aujourdhui,
            'total_services': total_services,
            'total_portes': total_portes,
            'total_agents': total_agents,
            'active_agents': active_agents,
            'agents_en_ligne': agents_en_ligne,
            'porte_actuelle': porte_actuelle.numero if porte_actuelle else None,
            'show_2fa_warning': show_2fa_warning,
            'visites_sur_place': visites_sur_place_json,
            'recent_visites': recent_visites_json,
            'daily_labels': daily_labels,
            'daily_data': daily_data,
            'weekly_labels': weekly_labels,
            'weekly_data': weekly_data,
            'monthly_labels': monthly_labels,
            'monthly_data': monthly_data,
            'yearly_labels': yearly_labels,
            'yearly_data': yearly_data,
            'service_labels': service_labels,
            'service_data': service_data,
            'service_percents': service_percents,
        })

    context = {
        'total_visiteurs': total_visiteurs,
        'visiteurs_presents': visiteurs_presents,
        'visites_aujourdhui': visites_aujourdhui,
        'total_services': total_services,
        'total_portes': total_portes,
        'total_agents': total_agents,
        'active_agents': active_agents,
        'agents_en_ligne': agents_en_ligne,
        'porte_actuelle': porte_actuelle,
        'visites_sur_place': visites_sur_place,
        'recent_visites': recent_visites,
        'show_2fa_warning': show_2fa_warning,
        # JSON pour les graphiques
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_data': json.dumps(weekly_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
        'yearly_labels': json.dumps(yearly_labels),
        'yearly_data': json.dumps(yearly_data),
        'service_labels': json.dumps(service_labels),
        'service_data': json.dumps(service_data),
        'service_percents': json.dumps(service_percents),
    }
    return render(request, 'core/dashboard.html', context)



# ============================================================
# VISITEURS
# ============================================================

@login_required
def visiteur_list(request):
    # Bloquer l'agent sans porte
    if not request.user.is_superuser:
        try:
            if not request.user.profile.porte_actuelle:
                messages.error(request, "Accès refusé : Vous devez être affecté à une porte pour consulter la liste des visiteurs.")
                return redirect('dashboard')
        except AgentProfile.DoesNotExist:
            return redirect('dashboard')

    query = request.GET.get('q', '')
    visiteurs = Visiteur.objects.filter(is_archived=False)
    if query:
        visiteurs = visiteurs.filter(
            Q(nom__icontains=query) | Q(prenom__icontains=query) | Q(numero_cni__icontains=query)
        )
    return render(request, 'core/visiteur_list.html', {
        'visiteurs': visiteurs, 
        'query': query,
        'is_receptionist': not request.user.is_superuser
    })


@login_required
def visiteur_create(request):
    # Bloquer l'agent sans porte dès le chargement du formulaire
    if not request.user.is_superuser:
        try:
            if not request.user.profile.porte_actuelle:
                messages.error(request, "Opération non autorisée : Vous n'êtes affecté à aucune porte.")
                return redirect('dashboard')
        except AgentProfile.DoesNotExist:
            return redirect('dashboard')

    if request.method == 'POST':
        form = VisiteurForm(request.POST, request.FILES)
        if form.is_valid():
            # Sauvegarder les fichiers capturés par caméra s'il y en a
            for field_name, file_obj in request.FILES.items():
                if file_obj.name.startswith('capture_') or 'capture' in file_obj.name:
                    camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
                    os.makedirs(camera_dir, exist_ok=True)
                    suffix = '.' + file_obj.name.split('.')[-1] if '.' in file_obj.name else '.jpg'
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    saved_filename = f"{field_name}_{timestamp}{suffix}"
                    saved_filepath = os.path.join(camera_dir, saved_filename)
                    with open(saved_filepath, 'wb') as dest:
                        for chunk in file_obj.chunks():
                            dest.write(chunk)
            visiteur = form.save()
            log_action(
                request.user, 'CREATION_VISITEUR',
                f"Création du visiteur {visiteur.prenom} {visiteur.nom} (CNI: {visiteur.numero_cni})",
                visiteur.id
            )
            messages.success(request, f"Visiteur {visiteur.prenom} {visiteur.nom} enregistré. Veuillez maintenant saisir les détails de la visite.")
            return redirect(f"{reverse('visite_create')}?visiteur_id={visiteur.pk}")
    else:
        form = VisiteurForm()
    return render(request, 'core/visiteur_form.html', {'form': form, 'title': 'Nouveau Visiteur'})


@login_required
def visiteur_detail(request, pk):
    visiteur = get_object_or_404(Visiteur, pk=pk)
    if visiteur.is_archived:
        messages.error(request, "Ce visiteur a été archivé.")
        return redirect('visiteur_list')
        
    visites = visiteur.visites.select_related('service_visite', 'porte_entree', 'porte_sortie').order_by('-heure_entree')
    
    # Stats temps réel
    total_visites = visites.count()
    derniere_visite = visites.first() if total_visites > 0 else None
    actuellement_present = visites.filter(statut='PRESENT').exists()
    
    # Service préféré
    top_service_stats = visiteur.visites.values('service_visite__nom').annotate(count=Count('id')).order_by('-count').first()
    top_service = top_service_stats['service_visite__nom'] if top_service_stats else "Aucun"
    
    # Données pour le graphique
    service_distribution = visiteur.visites.values('service_visite__nom').annotate(count=Count('id')).order_by('-count')
    chart_labels = [s['service_visite__nom'] for s in service_distribution]
    chart_data = [s['count'] for s in service_distribution]
    
    context = {
        'visiteur': visiteur,
        'visites': visites,
        'total_visites': total_visites,
        'derniere_visite': derniere_visite,
        'top_service': top_service,
        'actuellement_present': actuellement_present,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
    }
    return render(request, 'core/visiteur_detail.html', context)


@login_required
def visiteur_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit. Seul l'administrateur peut modifier la fiche d'un visiteur.")
        return redirect('dashboard')
        
    visiteur = get_object_or_404(Visiteur, pk=pk)
    if visiteur.is_archived:
        messages.error(request, "Impossible de modifier un visiteur archivé.")
        return redirect('visiteur_list')
        
    if visiteur.est_present:
        messages.error(request, "Impossible de modifier les informations d'un visiteur actuellement présent.")
        return redirect('visiteur_detail', pk=visiteur.pk)
        
    if request.method == 'POST':
        form = VisiteurEditForm(request.POST, request.FILES, instance=visiteur)
        if form.is_valid():
            # Sauvegarder les fichiers capturés par caméra s'il y en a
            for field_name, file_obj in request.FILES.items():
                if file_obj.name.startswith('capture_') or 'capture' in file_obj.name:
                    camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
                    os.makedirs(camera_dir, exist_ok=True)
                    suffix = '.' + file_obj.name.split('.')[-1] if '.' in file_obj.name else '.jpg'
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    saved_filename = f"{field_name}_{timestamp}{suffix}"
                    saved_filepath = os.path.join(camera_dir, saved_filename)
                    with open(saved_filepath, 'wb') as dest:
                        for chunk in file_obj.chunks():
                            dest.write(chunk)
            form.save()
            log_action(
                request.user, 'MODIFICATION_VISITEUR',
                f"Modification du visiteur {visiteur.prenom} {visiteur.nom}",
                visiteur.id
            )
            messages.success(request, "Visiteur modifié avec succès.")
            return redirect('visiteur_detail', pk=visiteur.pk)
    else:
        form = VisiteurEditForm(instance=visiteur)
    return render(request, 'core/visiteur_form.html', {
        'form': form,
        'title': 'Modifier Visiteur',
        'edit': True,
        'visiteur': visiteur,
    })


@login_required
def visiteur_archive(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit. Seul l'administrateur peut archiver un visiteur.")
        return redirect('dashboard')
        
    visiteur = get_object_or_404(Visiteur, pk=pk, is_archived=False)
    if visiteur.visites.filter(statut='PRESENT').exists():
        messages.error(request, "Impossible d'archiver un visiteur actuellement présent.")
        return redirect('visiteur_detail', pk=pk)

    if request.method == 'POST':
        motif = request.POST.get('motif_archivage', '').strip()
        if not motif:
            messages.error(request, "Le motif de l'archivage est obligatoire.")
            return render(request, 'core/confirm_archive.html', {'object': visiteur, 'is_visiteur': True})

        Archive.objects.create(
            type_entite='VISITEUR',
            donnees_json={
                'id': visiteur.id,
                'nom': visiteur.nom,
                'prenom': visiteur.prenom,
                'numero_cni': visiteur.numero_cni,
                'date_naissance': str(visiteur.date_naissance),
                'telephone': visiteur.telephone,
                'motif_archivage': motif,
            },
            admin=request.user
        )
        visiteur.is_archived = True
        visiteur.motif_archivage = motif
        visiteur.save()
        log_action(
            request.user, 'ARCHIVAGE_VISITEUR',
            f"Archivage du visiteur {visiteur.prenom} {visiteur.nom}. Motif: {motif}",
            visiteur.id
        )
        messages.success(request, "Visiteur archivé avec succès.")
        return redirect('visiteur_list')
    return render(request, 'core/confirm_archive.html', {'object': visiteur, 'is_visiteur': True})


@login_required
def visiteur_desarchiver_quick(request, pk):
    visiteur = get_object_or_404(Visiteur, pk=pk)
    if visiteur.is_archived:
        visiteur.is_archived = False
        motif_original = visiteur.motif_archivage
        visiteur.motif_archivage = None
        visiteur.save()
        Archive.objects.filter(type_entite='VISITEUR', donnees_json__id=visiteur.id).delete()
        log_action(
            request.user, 'DESARCHIVAGE_VISITEUR_OCR',
            f"Désarchivage rapide du visiteur {visiteur.prenom} {visiteur.nom} (Motif d'archivage d'origine : {motif_original})",
            visiteur.id
        )
        messages.success(request, f"Le visiteur {visiteur.prenom} {visiteur.nom} a été désarchivé. Vous pouvez maintenant enregistrer sa visite.")
    return redirect(f"{reverse('visite_create')}?visiteur_id={visiteur.id}")


@login_required
def check_cnib(request):
    cni = request.GET.get('cni', '').strip()
    if not cni:
        return JsonResponse({'exists': False})
        
    visiteur = Visiteur.objects.filter(numero_cni=cni).first()
    if visiteur:
        active_visite = visiteur.visites.filter(statut='PRESENT').first()
        return JsonResponse({
            'exists': True,
            'visiteur_id': visiteur.id,
            'prenom': visiteur.prenom,
            'nom': visiteur.nom,
            'numero_cni': visiteur.numero_cni,
            'is_archived': visiteur.is_archived,
            'motif_archivage': visiteur.motif_archivage or "Aucun motif spécifié.",
            'is_on_site': bool(active_visite),
            'redirect_url_desarchiver': reverse('visiteur_desarchiver_quick', kwargs={'pk': visiteur.pk}) if visiteur.is_archived else None,
            'redirect_url_normal': reverse('visite_sortie', kwargs={'pk': active_visite.pk}) if active_visite else (reverse('visite_create') + f"?visiteur_id={visiteur.id}")
        })
    return JsonResponse({'exists': False})


# ============================================================
# PORTES (ADMINISTRATION UNIQUEMENT)
# ============================================================

@login_required
def porte_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    portes = Porte.objects.filter(is_archived=False).order_by('numero')
    return render(request, 'core/porte_list.html', {'portes': portes})


@login_required
def porte_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = PorteForm(request.POST)
        if form.is_valid():
            porte = form.save()
            log_action(request.user, 'CREATION_PORTE', f"Création de la porte {porte.numero}", porte.id)
            messages.success(request, "Porte créée avec succès.")
            return redirect('porte_list')
    else:
        form = PorteForm()
    return render(request, 'core/porte_form.html', {'form': form, 'title': 'Nouvelle Porte'})


@login_required
def porte_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    porte = get_object_or_404(Porte, pk=pk, is_archived=False)
    if request.method == 'POST':
        form = PorteForm(request.POST, instance=porte)
        if form.is_valid():
            form.save()
            messages.success(request, "Porte mise à jour.")
            return redirect('porte_list')
    else:
        form = PorteForm(instance=porte)
    return render(request, 'core/porte_form.html', {'form': form, 'title': f'Modifier Porte {porte.numero}'})


@login_required
def porte_detail(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    porte = get_object_or_404(Porte, pk=pk, is_archived=False)
    visites = Visite.objects.filter(Q(porte_entree=porte) | Q(porte_sortie=porte)).select_related('visiteur', 'service_visite', 'agent_entree').order_by('-heure_entree')
    
    total_visites = visites.count()
    presents = visites.filter(statut='PRESENT').count()
    
    # Durée moyenne (min)
    visites_sorties = visites.filter(statut='SORTI', heure_sortie__isnull=False)
    duree_totale = sum([(v.heure_sortie - v.heure_entree).total_seconds() for v in visites_sorties])
    duree_moyenne = round((duree_totale / 60) / visites_sorties.count(), 1) if visites_sorties.count() > 0 else 0

    context = {
        'porte': porte,
        'visites': visites[:50],
        'total_visites': total_visites,
        'presents': presents,
        'duree_moyenne': duree_moyenne,
    }
    return render(request, 'core/porte_detail.html', context)


@login_required
def porte_archive(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
        
    porte = get_object_or_404(Porte, pk=pk, is_archived=False)
    if porte.visites_entrees.filter(statut='PRESENT').exists():
        messages.error(request, "Impossible d'archiver une porte avec des visiteurs présents.")
        return redirect('porte_list')
        
    if porte.agents_affectes.filter(is_archived=False).exists():
        messages.error(request, "Impossible d'archiver une porte avec des agents affectés. Réaffectez ou archivez d'abord les agents.")
        return redirect('porte_list')

    if request.method == 'POST':
        Archive.objects.create(
            type_entite='PORTE',
            donnees_json={
                'id': porte.id,
                'numero': porte.numero,
                'description': porte.description or '',
                'total_visites': porte.visites_entrees.count()
            },
            admin=request.user
        )
        porte.is_archived = True
        porte.save()
        log_action(request.user, 'ARCHIVAGE_PORTE', f"Archivage de la porte {porte.numero}", porte.id)
        messages.success(request, "Porte archivée avec succès.")
        return redirect('porte_list')
    return render(request, 'core/confirm_archive.html', {'object': porte})


# ============================================================
# VISITES
# ============================================================

@login_required
def visite_list(request):
    statut_filter = request.GET.get('statut', '')
    service_filter = request.GET.get('service', '')
    porte_filter = request.GET.get('porte', '')
    query = request.GET.get('q', '')
    visites = Visite.objects.select_related('visiteur', 'service_visite', 'agent_entree', 'porte_entree', 'porte_sortie')
    
    # Les agents peuvent désormais voir toutes les visites (historique global)
    # pour faciliter le suivi des visiteurs entre les différentes portes.
    if not request.user.is_superuser:
        try:
            porte = request.user.profile.porte_actuelle
            if not porte:
                # Si l'agent n'est pas encore affecté, on peut restreindre aux présents
                # ou lui donner accès s'il est considéré comme personnel de sécurité.
                # Ici on lui permet de voir les présents au minimum.
                visites = visites.filter(statut='PRESENT')
        except AgentProfile.DoesNotExist:
            visites = visites.filter(statut='PRESENT')

    if statut_filter:
        visites = visites.filter(statut=statut_filter)
    if service_filter:
        visites = visites.filter(service_visite_id=service_filter)
    if porte_filter:
        visites = visites.filter(Q(porte_entree_id=porte_filter) | Q(porte_sortie_id=porte_filter))
    if query:
        visites = visites.filter(
            Q(visiteur__nom__icontains=query) |
            Q(visiteur__prenom__icontains=query) |
            Q(service_visite__nom__icontains=query)
        )
    return render(request, 'core/visite_list.html', {
        'visites': visites.order_by('-heure_entree'),
        'statut_filter': statut_filter,
        'service_filter': service_filter,
        'porte_filter': porte_filter,
        'query': query,
    })


@login_required
def visite_create(request):
    cni_query = request.GET.get('cni')
    id_query = request.GET.get('visiteur_id')
    initial_visiteur = None
    
    if id_query:
        initial_visiteur = Visiteur.objects.filter(pk=id_query, is_archived=False).first()
    elif cni_query:
        initial_visiteur = Visiteur.objects.filter(numero_cni=cni_query, is_archived=False).first()

    if initial_visiteur and initial_visiteur.est_present:
        messages.warning(request, f"Le visiteur {initial_visiteur.prenom} {initial_visiteur.nom} est déjà enregistré comme 'Sur place'.")
        return redirect('visiteur_detail', pk=initial_visiteur.pk)

    if request.method == 'POST':
        form = VisiteForm(request.POST, user=request.user)
        if form.is_valid():
            visite = form.save(commit=False)
            
            # Affectation de la porte
            if not request.user.is_superuser:
                try:
                    porte = request.user.profile.porte_actuelle
                    if not porte:
                        messages.error(request, "Opération impossible : Vous n'êtes affecté à aucune porte. Contactez l'administrateur.")
                        return redirect('dashboard')
                    visite.porte_entree = porte
                except AgentProfile.DoesNotExist:
                    messages.error(request, "Profil agent introuvable.")
                    return redirect('dashboard')
            else:
                porte = visite.porte_entree
                if not porte:
                    messages.error(request, "Veuillez sélectionner une porte.")
                    return render(request, 'core/visite_form.html', {'form': form, 'title': 'Nouvelle Visite'})

            visite.agent_entree = request.user
            visite.save()
            log_action(
                request.user, 'CREATION_VISITE',
                f"Entrée du visiteur {visite.visiteur} à la Porte {porte.numero}",
                visite.id
            )
            messages.success(request, "Entrée enregistrée avec succès.")
            return redirect('visite_detail', pk=visite.pk)
    else:
        # Bloquer l'agent sans porte dès le chargement du formulaire
        if not request.user.is_superuser:
            try:
                if not request.user.profile.porte_actuelle:
                    messages.error(request, "Vous ne pouvez pas enregistrer d'entrées car vous n'êtes affecté à aucune porte.")
                    return redirect('dashboard')
            except AgentProfile.DoesNotExist:
                return redirect('dashboard')

        initial_data = {'visiteur': initial_visiteur} if initial_visiteur else {}
        form = VisiteForm(initial=initial_data, user=request.user)
        
    return render(request, 'core/visite_form.html', {
        'form': form, 
        'title': 'Nouvelle Visite',
        'visiteur': initial_visiteur,
    })


@login_required
def visite_detail(request, pk):
    visite = get_object_or_404(Visite.objects.select_related('visiteur', 'service_visite', 'agent_entree', 'agent_sortie', 'porte_entree', 'porte_sortie'), pk=pk)
    
    # Les agents peuvent consulter les détails de n'importe quelle visite
    # pour assurer la cohérence avec l'accès global au journal.
    if not request.user.is_superuser:
        try:
            if not request.user.profile.porte_actuelle:
                # Si l'agent n'a pas de porte, il ne voit que les présents
                if visite.statut != 'PRESENT':
                    messages.error(request, "Accès restreint aux visites en cours.")
                    return redirect('visite_list')
        except AgentProfile.DoesNotExist:
            if visite.statut != 'PRESENT':
                return redirect('visite_list')
            
    return render(request, 'core/visite_detail.html', {'visite': visite})


@login_required
def visite_sortie(request, pk):
    visite = get_object_or_404(Visite, pk=pk, statut='PRESENT')
    
    # On vérifie juste que l'agent a une porte
    if not request.user.is_superuser:
        try:
            if not request.user.profile.porte_actuelle:
                messages.error(request, "Vous devez être affecté à une porte pour enregistrer une sortie.")
                return redirect('visite_list')
        except AgentProfile.DoesNotExist:
            return redirect('visite_list')

    if request.method == 'POST':
        visite.heure_sortie = timezone.now()
        visite.statut = 'SORTI'
        visite.agent_sortie = request.user
        
        if request.user.is_superuser:
            porte_id = request.POST.get('porte_sortie')
            if porte_id:
                visite.porte_sortie = get_object_or_404(Porte, pk=porte_id)
            else:
                messages.error(request, "Veuillez sélectionner une porte de sortie.")
                return render(request, 'core/visite_sortie.html', {
                    'visite': visite,
                    'porte_actuelle': None,
                    'all_portes': Porte.objects.filter(is_archived=False)
                })
        else:
            visite.porte_sortie = request.user.profile.porte_actuelle
        
        # Sauvegarder les notes de sortie
        notes = request.POST.get('notes_sortie', '').strip()
        if notes:
            visite.notes_sortie = notes
            
        visite.save()
        p_sort = visite.porte_sortie.numero if visite.porte_sortie else "admin"
        log_action(request.user, 'SORTIE_VISITE', f"Sortie de {visite.visiteur} par la Porte {p_sort}", visite.id)
        messages.success(request, f"Sortie enregistrée pour {visite.visiteur.prenom} {visite.visiteur.nom}.")
        return redirect('visite_list')
    porte_actuelle = None
    if not request.user.is_superuser:
        try:
            porte_actuelle = request.user.profile.porte_actuelle
        except AgentProfile.DoesNotExist:
            pass

    all_portes = Porte.objects.filter(is_archived=False) if request.user.is_superuser else None

    return render(request, 'core/visite_sortie.html', {
        'visite': visite,
        'porte_actuelle': porte_actuelle,
        'all_portes': all_portes
    })


# ============================================================
# SERVICES
# ============================================================

@login_required
def service_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    services = Service.objects.filter(is_archived=False).annotate(nb_visites=Count('visites'))
    return render(request, 'core/service_list.html', {'services': services})


@login_required
def service_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            log_action(request.user, 'CREATION_SERVICE', f"Création du service {service.nom}", service.id)
            messages.success(request, "Service ajouté avec succès.")
            return redirect('service_list')
    else:
        form = ServiceForm()
    return render(request, 'core/service_form.html', {'form': form, 'title': 'Nouveau Service'})


@login_required
def service_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            log_action(request.user, 'MODIFICATION_SERVICE', f"Modification du service {service.nom}", service.id)
            messages.success(request, "Service mis à jour avec succès.")
            return redirect('service_list')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'core/service_form.html', {'form': form, 'title': f'Modifier {service.nom}', 'edit': True})


@login_required
def service_detail(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    service = get_object_or_404(Service.objects.annotate(nb_visites=Count('visites')), pk=pk)
    visites = service.visites.select_related('visiteur', 'porte_entree').order_by('-heure_entree')
    
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    visites_aujourdhui = service.visites.filter(date_visite=today).count()
    visites_semaine = service.visites.filter(date_visite__gte=start_of_week).count()
    visites_mois = service.visites.filter(date_visite__gte=start_of_month).count()
    visiteurs_presents = service.visites.filter(statut='PRESENT').count()
    
    last_7_days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    labels = [d.strftime('%d/%m') for d in last_7_days]
    data = [service.visites.filter(date_visite=d).count() for d in last_7_days]
    
    # Taux de fréquentation (part du service ce mois-ci)
    total_visites_mois = Visite.objects.filter(date_visite__gte=start_of_month).count()
    taux_frequentation = round((visites_mois / total_visites_mois) * 100, 1) if total_visites_mois > 0 else 0
    
    # Top Visiteur
    top_stats = service.visites.values('visiteur__id').annotate(count=Count('id')).order_by('-count').first()
    top_visiteur = None
    if top_stats:
        top_visiteur = Visiteur.objects.get(pk=top_stats['visiteur__id'])
        top_visiteur.visit_count = top_stats['count']
        
    context = {
        'service': service,
        'visites': visites[:50],
        'visites_aujourdhui': visites_aujourdhui,
        'visites_semaine': visites_semaine,
        'visites_mois': visites_mois,
        'visiteurs_presents': visiteurs_presents,
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data),
        'top_visiteur': top_visiteur,
        'taux_frequentation': taux_frequentation,
    }
    return render(request, 'core/service_detail.html', context)


@login_required
def service_archive(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    service = get_object_or_404(Service, pk=pk, is_archived=False)
    if service.visites.filter(statut='PRESENT').exists():
        messages.error(request, "Impossible d'archiver un service avec des visiteurs présents.")
        return redirect('service_list')

    if request.method == 'POST':
        Archive.objects.create(
            type_entite='SERVICE',
            donnees_json={
                'id': service.id,
                'nom': service.nom,
                'description': service.description or '',
                'total_visites': service.visites.count()
            },
            admin=request.user
        )
        service.is_archived = True
        service.save()
        log_action(request.user, 'ARCHIVAGE_SERVICE', f"Archivage du service {service.nom}", service.id)
        messages.success(request, "Service archivé avec succès.")
        return redirect('service_list')
    return render(request, 'core/confirm_archive.html', {'object': service})


# ============================================================
# OCR & OUTILS
# ============================================================

@login_required
def ocr_scan(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        suffix = '.' + image_file.name.split('.')[-1]
        
        # Dossier de sauvegarde des photos de la caméra
        camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
        os.makedirs(camera_dir, exist_ok=True)
        
        # Enregistrer une copie avec un horodatage unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        saved_filename = f"ocr_scan_{timestamp}{suffix}"
        saved_filepath = os.path.join(camera_dir, saved_filename)
        
        with open(saved_filepath, 'wb') as dest:
            for chunk in image_file.chunks():
                dest.write(chunk)

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = extract_cnib_info(tmp_path)
            
            # Vérifier si le visiteur existe déjà
            if result.get('numero_cni'):
                visiteur = Visiteur.objects.filter(numero_cni=result['numero_cni']).first()
                if visiteur:
                    result['already_exists'] = True
                    result['visiteur_id'] = visiteur.id
                    result['prenom'] = visiteur.prenom
                    result['nom'] = visiteur.nom
                    
                    if visiteur.is_archived:
                        result['is_archived'] = True
                        result['motif_archivage'] = visiteur.motif_archivage or "Aucun motif spécifié."
                        result['redirect_url'] = reverse('visiteur_desarchiver_quick', kwargs={'pk': visiteur.pk})
                    else:
                        result['is_archived'] = False
                        # Vérifier si le visiteur est déjà sur place
                        active_visite = visiteur.visites.filter(statut='PRESENT').first()
                        if active_visite:
                            result['is_on_site'] = True
                            result['redirect_url'] = reverse('visite_sortie', kwargs={'pk': active_visite.pk})
                        else:
                            result['is_on_site'] = False
                            result['redirect_url'] = reverse('visite_create') + f"?visiteur_id={visiteur.id}"
                else:
                    result['already_exists'] = False
            
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'Aucune image fournie.'})


@login_required
def visiteur_cnib_view(request, pk, side):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit aux documents d'identité.")
        return redirect('dashboard')
        
    visiteur = get_object_or_404(Visiteur, pk=pk)
    scan = visiteur.scan_cni_recto if side == 'recto' else visiteur.scan_cni_verso
    if not scan:
        raise Http404

    log_action(request.user, 'CONSULTATION_CNIB', f"Consultation du scan CNIB ({side}) de {visiteur}", visiteur.id)
    
    file_path = os.path.join(settings.PRIVATE_MEDIA_ROOT, scan.name)
    if not os.path.exists(file_path):
        raise Http404
            
    with open(file_path, 'rb') as f:
        content = f.read()
    content_type = 'image/jpeg' if scan.name.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
    return HttpResponse(content, content_type=content_type)


# ============================================================
# GÉNÉRATION DE PDF
# ============================================================

def _render_to_pdf(request, template_path, context, filename):
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    context['logo_path'] = logo_path
    context['now'] = timezone.now()
    
    html_string = render(request, template_path, context).content.decode()
    result = BytesIO()
    pdf_status = pisa.CreatePDF(html_string, dest=result, encoding='utf-8')
    if pdf_status.err:
        return HttpResponse('Erreur lors de la génération du PDF.', status=500)
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def pdf_rapport_visites(request):
    form = RapportVisiteForm(request.GET)
    visites = Visite.objects.all().select_related('visiteur', 'service_visite', 'porte_entree', 'porte_sortie', 'agent_entree')
    service_nom = "Tous les services"
    porte_nom = "Toutes les portes"
    visiteur_nom = "Tous les visiteurs"
    agent_nom = "Tous les agents"
    
    if form.is_valid():
        date_debut = form.cleaned_data['date_debut']
        date_fin = form.cleaned_data['date_fin']
        service = form.cleaned_data['service']
        porte = form.cleaned_data['porte']
        visiteur = form.cleaned_data['visiteur']
        agent = form.cleaned_data['agent']
        
        visites = visites.filter(date_visite__range=[date_debut, date_fin])
        if service:
            visites = visites.filter(service_visite=service)
            service_nom = service.nom
        if porte:
            visites = visites.filter(Q(porte_entree=porte) | Q(porte_sortie=porte))
            porte_nom = porte.numero
        if visiteur:
            visites = visites.filter(visiteur=visiteur)
            visiteur_nom = f"{visiteur.prenom} {visiteur.nom}"
        if agent:
            visites = visites.filter(Q(agent_entree=agent) | Q(agent_sortie=agent))
            agent_nom = agent.username
    else:
        visites = visites.filter(date_visite=timezone.now().date())
        date_debut = date_fin = timezone.now().date()

    context = {
        'visites': visites.order_by('-heure_entree'),
        'date_debut': date_debut,
        'date_fin': date_fin,
        'service_nom': service_nom,
        'porte_nom': porte_nom,
        'visiteur_nom': visiteur_nom,
        'agent_nom': agent_nom,
    }
    return _render_to_pdf(request, 'core/pdf/rapport_visites.html', context, 'rapport_visites.pdf')


@login_required
def log_list(request):
    action_filter = request.GET.get('action', '')
    logs = LogAction.objects.select_related('admin')
    if action_filter:
        logs = logs.filter(action=action_filter)
    action_types = sorted(set(LogAction.objects.values_list('action', flat=True)))
    return render(request, 'core/log_list.html', {
        'logs': logs[:200],
        'action_filter': action_filter,
        'action_types': action_types,
    })


@login_required
def pdf_log_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    action_filter = request.GET.get('action', '')
    logs = LogAction.objects.select_related('admin').order_by('-date_heure')
    if action_filter:
        logs = logs.filter(action=action_filter)
        
    context = {
        'logs': logs[:500],
        'action_filter': action_filter or "Toutes les actions",
    }
    return _render_to_pdf(request, 'core/pdf/log_list.html', context, 'journal_audit.pdf')


@login_required
def pdf_fiche_visiteur(request, pk):
    import base64
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    visiteur = get_object_or_404(Visiteur, pk=pk)
    visites = visiteur.visites.select_related('service_visite', 'porte_entree').order_by('-heure_entree')
    
    cnib_recto_base64 = None
    cnib_recto_type = None
    
    if visiteur.scan_cni_recto:
        file_path = os.path.join(settings.PRIVATE_MEDIA_ROOT, visiteur.scan_cni_recto.name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                cnib_recto_base64 = base64.b64encode(f.read()).decode('utf-8')
            cnib_recto_type = 'image/jpeg' if visiteur.scan_cni_recto.name.lower().endswith(('.jpg', '.jpeg')) else 'image/png'

    context = {
        'visiteur': visiteur,
        'visites': visites,
        'cnib_recto_base64': cnib_recto_base64,
        'cnib_recto_type': cnib_recto_type,
    }
    
    log_action(request.user, 'TELECHARGEMENT_FICHE_PDF', f"Téléchargement de la fiche PDF du visiteur {visiteur}", visiteur.id)
    return _render_to_pdf(request, 'core/pdf/fiche_visiteur.html', context, f'fiche_visiteur_{visiteur.numero_cni}.pdf')


@login_required
def pdf_fiche_visite(request, pk):
    visite = get_object_or_404(Visite.objects.select_related('visiteur', 'service_visite', 'agent_entree', 'agent_sortie', 'porte_entree', 'porte_sortie'), pk=pk)
    
    if not request.user.is_superuser:
        try:
            if not request.user.profile.porte_actuelle:
                if visite.statut != 'PRESENT':
                    messages.error(request, "Accès restreint aux visites en cours.")
                    return redirect('visite_list')
        except AgentProfile.DoesNotExist:
            if visite.statut != 'PRESENT':
                return redirect('visite_list')
    
    context = {
        'visite': visite,
    }
    
    log_action(request.user, 'TELECHARGEMENT_FICHE_PDF', f"Téléchargement du rapport PDF de la visite #{visite.id}", visite.id)
    return _render_to_pdf(request, 'core/pdf/fiche_visite.html', context, f'rapport_visite_{visite.id}.pdf')


@login_required
def archive_list(request):
    archives = Archive.objects.select_related('admin').order_by('-date_archivage')
    type_filter = request.GET.get('type')
    if type_filter:
        archives = archives.filter(type_entite=type_filter)
    return render(request, 'core/archive_list.html', {'archives': archives, 'type_filter': type_filter})


@login_required
def archive_restore(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit. Seul l'administrateur peut désarchiver.")
        return redirect('dashboard')
        
    archive = get_object_or_404(Archive, pk=pk)
    
    if archive.type_entite == 'VISITEUR':
        visitor_id = archive.donnees_json.get('id')
        visiteur = get_object_or_404(Visiteur, pk=visitor_id)
        visiteur.is_archived = False
        visiteur.motif_archivage = None
        visiteur.save()
        
        log_action(
            request.user, 'DESARCHIVAGE_VISITEUR',
            f"Désarchivage du visiteur {visiteur.prenom} {visiteur.nom}",
            visiteur.id
        )
        messages.success(request, f"Le visiteur {visiteur.prenom} {visiteur.nom} a été désarchivé avec succès.")
        archive.delete()
        
    elif archive.type_entite == 'SERVICE':
        service_data = archive.donnees_json
        service_id = service_data.get('id')
        service = get_object_or_404(Service, pk=service_id)
        if Service.objects.filter(nom=service_data.get('nom'), is_archived=False).exclude(pk=service.pk).exists():
            messages.error(request, f"Un service actif avec le nom '{service_data.get('nom')}' existe déjà.")
            return redirect('archive_list')
        
        service.nom = service_data.get('nom')
        service.description = service_data.get('description', '')
        service.is_archived = False
        service.save()
        log_action(
            request.user, 'DESARCHIVAGE_SERVICE',
            f"Désarchivage du service {service.nom}",
            service.id
        )
        messages.success(request, f"Le service {service.nom} a été restauré avec succès.")
        archive.delete()
        
    elif archive.type_entite == 'PORTE':
        porte_data = archive.donnees_json
        porte_id = porte_data.get('id')
        porte = get_object_or_404(Porte, pk=porte_id)
        if Porte.objects.filter(numero=porte_data.get('numero'), is_archived=False).exclude(pk=porte.pk).exists():
            messages.error(request, f"Une porte active avec le numéro '{porte_data.get('numero')}' existe déjà.")
            return redirect('archive_list')
        
        porte.numero = porte_data.get('numero')
        porte.description = porte_data.get('description', '')
        porte.is_archived = False
        porte.save()
        log_action(
            request.user, 'DESARCHIVAGE_PORTE',
            f"Désarchivage de la porte {porte.numero}",
            porte.id
        )
        messages.success(request, f"La porte {porte.numero} a été restaurée avec succès.")
        archive.delete()

    elif archive.type_entite == 'AGENT':
        agent_data = archive.donnees_json
        agent_id = agent_data.get('id')
        agent = get_object_or_404(User, pk=agent_id)
        
        profile, created = AgentProfile.objects.get_or_create(user=agent)
        profile.is_archived = False
        profile.save()
        
        agent.is_active = True
        agent.save()
        
        log_action(
            request.user, 'DESARCHIVAGE_AGENT',
            f"Désarchivage de l'agent {agent.username}",
            agent.id
        )
        messages.success(request, f"L'agent {agent.username} a été restauré avec succès.")
        archive.delete()
        
    return redirect('archive_list')


# ============================================================
# GESTION DES UTILISATEURS (ADMINISTRATION UNIQUEMENT)
# ============================================================

@login_required
def user_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
    users = User.objects.exclude(profile__is_archived=True).select_related('profile__porte_actuelle').order_by('-date_joined')
    if request.user.username != 'admin_secours':
        users = users.exclude(username='admin_secours')
    return render(request, 'core/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, current_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            
            def clean_str(s):
                import unicodedata
                return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()
            
            f_name = clean_str(user.first_name)[:4]
            l_name = clean_str(user.last_name)[:4]
            base_username = f"agent_{f_name}{l_name}"
            user.username = base_username
            
            count = 1
            while User.objects.filter(username=user.username).exists():
                user.username = f"{base_username}{count}"
                count += 1
            
            alphabet = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(alphabet) for i in range(10))
            user.set_password(password)
            user.is_staff = True
            user.is_active = True
            user.save()
            
            # Affectation porte
            porte = form.cleaned_data.get('porte_actuelle')
            if porte:
                profile, created = AgentProfile.objects.get_or_create(user=user)
                profile.porte_actuelle = porte
                profile.save()
                log_action(request.user, 'AFFECTATION_PORTE', f"Agent {user.username} affecté à la Porte {porte.numero}", user.id)

            log_action(request.user, 'CREATION_USER', f"Création du compte agent : {user.username}", user.id)
            messages.success(request, f"Compte agent créé ! Identifiant : {user.username} | Mot de passe : {password}")
            return redirect('user_list')
    else:
        form = UserRegistrationForm(current_user=request.user)
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Nouvel Agent'})


@login_required
def user_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, instance=user, current_user=request.user)
        if form.is_valid():
            form.save()
            
            # Mise à jour porte (uniquement si le champ est présent dans le formulaire)
            if 'porte_actuelle' in form.fields:
                porte = form.cleaned_data.get('porte_actuelle')
                profile, created = AgentProfile.objects.get_or_create(user=user)
                if profile.porte_actuelle != porte:
                    profile.porte_actuelle = porte
                    profile.save()
                    log_action(request.user, 'AFFECTATION_PORTE', f"Agent {user.username} réaffecté à la Porte {porte.numero if porte else 'Aucune'}", user.id)

            log_action(request.user, 'MODIFICATION_USER', f"Modification de l'utilisateur {user.username}", user.id)
            messages.success(request, "Profil utilisateur mis à jour.")
            return redirect('user_list')
    else:
        form = UserRegistrationForm(instance=user, current_user=request.user)
    return render(request, 'core/user_form.html', {'form': form, 'title': f'Modifier {user.username}', 'edit': True})


@login_required
def user_archive(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    if user == request.user or user.is_superuser:
        messages.error(request, "Impossible d'archiver cet utilisateur.")
        return redirect('user_list')

    if request.method == 'POST':
        Archive.objects.create(
            type_entite='AGENT',
            donnees_json={
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email
            },
            admin=request.user
        )
        profile, created = AgentProfile.objects.get_or_create(user=user)
        profile.is_archived = True
        profile.save()
        user.is_active = False
        user.save()
        log_action(request.user, 'ARCHIVAGE_AGENT', f"Archivage de l'agent {user.username}", user.id)
        messages.success(request, "Agent archivé avec succès.")
        return redirect('user_list')
    return render(request, 'core/confirm_archive.html', {'object': user, 'is_user': True})


@login_required
def user_toggle_status(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    if user == request.user or user.is_superuser:
        messages.error(request, "Action impossible sur ce compte.")
        return redirect('user_list')
        
    user.is_active = not user.is_active
    user.save()
    
    action = "ACTIVATION_USER" if user.is_active else "DESACTIVATION_USER"
    log_action(request.user, action, f"Compte {user.username} {'activé' if user.is_active else 'désactivé'}", user.id)
    messages.success(request, f"Compte de {user.username} mis à jour.")
    return redirect('user_list')


@login_required
def user_password_reset(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    alphabet = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(alphabet) for i in range(12))
    user.set_password(new_password)
    user.save()
    
    log_action(request.user, 'RESET_PASSWORD', f"Réinitialisation mot de passe pour {user.username}", user.id)
    messages.success(request, f"Nouveau mot de passe généré pour {user.username} : {new_password}")
    return redirect('user_list')


@login_required
def user_disable_2fa(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    
    try:
        profile = user.profile
        if profile.two_factor_enabled:
            profile.two_factor_enabled = False
            profile.two_factor_secret = None
            profile.save()
            log_action(request.user, 'DESACTIVER_2FA', f"Désactivation du 2FA par l'administrateur pour {user.username}", user.id)
            messages.success(request, f"L'authentification 2FA a été désactivée pour l'agent {user.username}.")
        else:
            messages.warning(request, f"L'agent {user.username} n'a pas le 2FA activé.")
    except Exception:
        messages.warning(request, f"Le profil de l'agent {user.username} est introuvable.")
        
    return redirect('user_list')


@login_required
def captures_camera_view(request):
    if request.user.username != 'admin_secours':
        messages.error(request, "Accès interdit. Cette galerie est réservée à l'administrateur de secours.")
        return redirect('dashboard')
        
    import re
    from django.core.paginator import Paginator
    
    camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
    if not os.path.exists(camera_dir):
        os.makedirs(camera_dir, exist_ok=True)
        
    files = []
    date_pattern = re.compile(r'(\d{8})_(\d{6})')
    
    for filename in os.listdir(camera_dir):
        filepath = os.path.join(camera_dir, filename)
        if not os.path.isfile(filepath):
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            continue
            
        try:
            stat = os.stat(filepath)
            size_bytes = stat.st_size
            size_kb = round(size_bytes / 1024, 1)
            
            match = date_pattern.search(filename)
            if match:
                date_str_raw = match.group(1)
                time_str_raw = match.group(2)
                try:
                    dt = datetime.strptime(f"{date_str_raw}_{time_str_raw}", "%Y%m%d_%H%M%S")
                except Exception:
                    dt = datetime.fromtimestamp(stat.st_mtime)
                
                idx = filename.find(match.group(0))
                if idx > 0:
                    prefix = filename[:idx].rstrip('_')
                else:
                    prefix = 'capture'
            else:
                dt = datetime.fromtimestamp(stat.st_mtime)
                prefix = os.path.splitext(filename)[0]
                prefix = re.sub(r'_\d+$', '', prefix)
                
            files.append({
                'name': filename,
                'url': settings.MEDIA_URL + 'captures_camera/' + filename,
                'prefix': prefix,
                'datetime': dt,
                'date_str': dt.strftime('%d/%m/%Y'),
                'time_str': dt.strftime('%H:%M:%S'),
                'date_iso': dt.date().isoformat(),
                'size_kb': size_kb,
            })
        except Exception:
            pass
            
    prefixes = sorted(list(set(f['prefix'] for f in files)))
    
    q = request.GET.get('q', '').strip()
    if q:
        files = [f for f in files if q.lower() in f['name'].lower()]
        
    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        files = [f for f in files if f['prefix'] == type_filter]
        
    date_filter = request.GET.get('date', '').strip()
    if date_filter:
        files = [f for f in files if f['date_iso'] == date_filter]
        
    sort = request.GET.get('sort', 'newest')
    if sort == 'oldest':
        files = sorted(files, key=lambda x: x['datetime'])
    else:
        files = sorted(files, key=lambda x: x['datetime'], reverse=True)
        
    paginator = Paginator(files, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.GET.get('format') == 'json':
        from django.utils.text import slugify
        serialized_files = []
        for f in page_obj:
            serialized_files.append({
                'name': f['name'],
                'url': f['url'],
                'prefix': f['prefix'],
                'date_str': f['date_str'],
                'time_str': f['time_str'],
                'size_kb': f['size_kb'],
                'slug': slugify(f['name']),
            })

        pagination = {
            'has_other_pages': page_obj.has_other_pages(),
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'number': page_obj.number,
            'num_pages': paginator.num_pages,
            'page_range': list(paginator.page_range),
            'total_count': len(files),
        }

        return JsonResponse({
            'files': serialized_files,
            'pagination': pagination,
            'prefixes': prefixes,
        })

    context = {
        'page_obj': page_obj,
        'prefixes': prefixes,
        'q': q,
        'selected_type': type_filter,
        'selected_date': date_filter,
        'sort': sort,
        'total_count': len(files),
    }
    return render(request, 'core/captures_camera.html', context)


@login_required
def delete_capture_view(request, filename):
    if request.user.username != 'admin_secours':
        return JsonResponse({'success': False, 'error': 'Accès interdit.'}, status=403)
        
    if request.method == 'POST':
        filename = os.path.basename(filename)
        camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
        filepath = os.path.join(camera_dir, filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                os.remove(filepath)
                log_action(request.user, 'SUPPRESSION_CAPTURE', f"Suppression de la capture caméra : {filename}")
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'Fichier introuvable.'}, status=404)
            
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)


@login_required
def delete_all_captures_view(request):
    if request.user.username != 'admin_secours':
        return JsonResponse({'success': False, 'error': 'Accès interdit.'}, status=403)
        
    if request.method == 'POST':
        camera_dir = os.path.join(settings.MEDIA_ROOT, 'captures_camera')
        if os.path.exists(camera_dir):
            try:
                count = 0
                for filename in os.listdir(camera_dir):
                    filepath = os.path.join(camera_dir, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        count += 1
                log_action(request.user, 'SUPPRESSION_TOUTES_CAPTURES', f"Suppression de {count} captures caméra.")
                return JsonResponse({'success': True, 'count': count})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        return JsonResponse({'success': True, 'count': 0})
            
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)



@login_required
def dismiss_2fa_warning(request):
    """
    Dismisses the 2FA warning banner for the current session.
    """
    if request.method == 'POST':
        request.session['dismissed_2fa_warning'] = True
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

