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
# AUTHENTICATION
# ============================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            log_action(user, 'CONNEXION', f"L'utilisateur {u} s'est connecté.")
            return redirect('dashboard')
        else:
            messages.error(request, "Identifiants invalides.")
    return render(request, 'core/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'DECONNEXION', f"L'utilisateur {request.user.username} s'est déconnecté.")
    logout(request)
    return redirect('login')


# ============================================================
# DASHBOARD
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
            if porte_actuelle:
                visites_base = visites_base.filter(porte=porte_actuelle)
            else:
                # Si l'agent n'a pas de porte assignée, il ne voit rien par sécurité
                visites_base = Visite.objects.none()
        except AgentProfile.DoesNotExist:
            visites_base = Visite.objects.none()
    
    # 1. Stats de base
    total_visiteurs = Visiteur.objects.filter(is_archived=False).count()
    visiteurs_presents = visites_base.filter(statut='PRESENT').count()
    visites_aujourdhui = visites_base.filter(date_visite=today).count()
    total_services = Service.objects.count()
    total_portes = Porte.objects.count()
    
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

    context = {
        'total_visiteurs': total_visiteurs,
        'visiteurs_presents': visiteurs_presents,
        'visites_aujourdhui': visites_aujourdhui,
        'total_services': total_services,
        'total_portes': total_portes,
        'porte_actuelle': porte_actuelle,
        'visites_sur_place': visites_sur_place,
        'recent_visites': recent_visites,
        # Chart JSON
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
        
    visites = visiteur.visites.select_related('service_visite', 'porte').order_by('-heure_entree')
    
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
        
    if request.method == 'POST':
        form = VisiteurEditForm(request.POST, request.FILES, instance=visiteur)
        if form.is_valid():
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
        Archive.objects.create(
            type_entite='VISITEUR',
            donnees_json={
                'id': visiteur.id,
                'nom': visiteur.nom,
                'prenom': visiteur.prenom,
                'numero_cni': visiteur.numero_cni,
                'date_naissance': str(visiteur.date_naissance),
                'telephone': visiteur.telephone,
            },
            admin=request.user
        )
        visiteur.is_archived = True
        visiteur.save()
        log_action(
            request.user, 'ARCHIVAGE_VISITEUR',
            f"Archivage du visiteur {visiteur.prenom} {visiteur.nom}",
            visiteur.id
        )
        messages.success(request, "Visiteur archivé avec succès.")
        return redirect('visiteur_list')
    return render(request, 'core/confirm_archive.html', {'object': visiteur})


# ============================================================
# PORTES (ADMIN ONLY)
# ============================================================

@login_required
def porte_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    portes = Porte.objects.all().order_by('numero')
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
    porte = get_object_or_404(Porte, pk=pk)
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
    porte = get_object_or_404(Porte, pk=pk)
    visites = porte.visites.select_related('visiteur', 'service_visite', 'agent_entree').order_by('-heure_entree')
    
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


# ============================================================
# VISITES
# ============================================================

@login_required
def visite_list(request):
    statut_filter = request.GET.get('statut', '')
    query = request.GET.get('q', '')
    visites = Visite.objects.select_related('visiteur', 'service_visite', 'agent_entree', 'porte')

    # Filtrage par porte actuelle de l'agent
    if not request.user.is_superuser:
        try:
            porte = request.user.profile.porte_actuelle
            if porte:
                visites = visites.filter(porte=porte)
            else:
                visites = Visite.objects.none()
        except AgentProfile.DoesNotExist:
            visites = Visite.objects.none()

    if statut_filter:
        visites = visites.filter(statut=statut_filter)
    if query:
        visites = visites.filter(
            Q(visiteur__nom__icontains=query) |
            Q(visiteur__prenom__icontains=query) |
            Q(service_visite__nom__icontains=query)
        )
    return render(request, 'core/visite_list.html', {
        'visites': visites,
        'statut_filter': statut_filter,
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
                    visite.porte = porte
                except AgentProfile.DoesNotExist:
                    messages.error(request, "Profil agent introuvable.")
                    return redirect('dashboard')
            else:
                porte = visite.porte
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
    visite = get_object_or_404(Visite.objects.select_related('visiteur', 'service_visite', 'agent_entree', 'agent_sortie', 'porte'), pk=pk)
    
    # Un agent ne voit que les visites de sa porte
    if not request.user.is_superuser:
        try:
            if visite.porte != request.user.profile.porte_actuelle:
                messages.error(request, "Accès refusé.")
                return redirect('visite_list')
        except AgentProfile.DoesNotExist:
            return redirect('visite_list')
            
    return render(request, 'core/visite_detail.html', {'visite': visite})


@login_required
def visite_sortie(request, pk):
    visite = get_object_or_404(Visite, pk=pk, statut='PRESENT')
    
    if not request.user.is_superuser:
        try:
            if visite.porte != request.user.profile.porte_actuelle:
                messages.error(request, "Accès refusé.")
                return redirect('visite_list')
        except AgentProfile.DoesNotExist:
            return redirect('visite_list')

    if request.method == 'POST':
        visite.heure_sortie = timezone.now()
        visite.statut = 'SORTI'
        visite.agent_sortie = request.user
        visite.save()
        log_action(request.user, 'SORTIE_VISITE', f"Sortie de {visite.visiteur}", visite.id)
        messages.success(request, f"Sortie enregistrée pour {visite.visiteur.prenom} {visite.visiteur.nom}.")
        return redirect('visite_list')
    return render(request, 'core/visite_sortie.html', {'visite': visite})


# ============================================================
# SERVICES
# ============================================================

@login_required
def service_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    services = Service.objects.annotate(nb_visites=Count('visites'))
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
    visites = service.visites.select_related('visiteur', 'porte').order_by('-heure_entree')
    
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
        
    context = {
        'service': service,
        'visites': visites[:50],
        'visites_aujourdhui': visites_aujourdhui,
        'visites_semaine': visites_semaine,
        'visites_mois': visites_mois,
        'visiteurs_presents': visiteurs_presents,
        'chart_labels': json.dumps(labels),
        'chart_data': json.dumps(data),
    }
    return render(request, 'core/service_detail.html', context)


@login_required
def service_archive(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    service = get_object_or_404(Service, pk=pk)
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
        service.delete()
        log_action(request.user, 'ARCHIVAGE_SERVICE', f"Archivage du service {service.nom}", service.id)
        messages.success(request, "Service archivé avec succès.")
        return redirect('service_list')
    return render(request, 'core/confirm_archive.html', {'object': service})


# ============================================================
# OCR & UTILS
# ============================================================

@login_required
def ocr_scan(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        suffix = '.' + image_file.name.split('.')[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = extract_cnib_info(tmp_path)
            
            # Vérifier si le visiteur existe déjà
            if result.get('numero_cni'):
                visiteur = Visiteur.objects.filter(numero_cni=result['numero_cni'], is_archived=False).first()
                if visiteur:
                    result['already_exists'] = True
                    result['visiteur_id'] = visiteur.id
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
# PDF GENERATION
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
    visites = Visite.objects.all().select_related('visiteur', 'service_visite', 'porte', 'agent_entree')
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
            visites = visites.filter(porte=porte)
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
def archive_list(request):
    archives = Archive.objects.select_related('admin').order_by('-date_archivage')
    return render(request, 'core/archive_list.html', {'archives': archives})


# ============================================================
# USERS MANAGEMENT (ADMIN ONLY)
# ============================================================

@login_required
def user_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
    users = User.objects.all().select_related('profile__porte_actuelle').order_by('-date_joined')
    return render(request, 'core/user_list.html', {'users': users})


@login_required
def user_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
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
                user.profile.porte_actuelle = porte
                user.profile.save()
                log_action(request.user, 'AFFECTATION_PORTE', f"Agent {user.username} affecté à la Porte {porte.numero}", user.id)

            log_action(request.user, 'CREATION_USER', f"Création du compte agent : {user.username}", user.id)
            messages.success(request, f"Compte agent créé ! Identifiant : {user.username} | Mot de passe : {password}")
            return redirect('user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/user_form.html', {'form': form, 'title': 'Nouvel Agent'})


@login_required
def user_edit(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès interdit.")
        return redirect('dashboard')
        
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            
            # Mise à jour porte
            porte = form.cleaned_data.get('porte_actuelle')
            if porte != user.profile.porte_actuelle:
                user.profile.porte_actuelle = porte
                user.profile.save()
                log_action(request.user, 'AFFECTATION_PORTE', f"Agent {user.username} réaffecté à la Porte {porte.numero if porte else 'Aucune'}", user.id)

            log_action(request.user, 'MODIFICATION_USER', f"Modification de l'utilisateur {user.username}", user.id)
            messages.success(request, "Profil utilisateur mis à jour.")
            return redirect('user_list')
    else:
        form = UserRegistrationForm(instance=user)
    return render(request, 'core/user_form.html', {'form': form, 'title': f'Modifier {user.username}', 'edit': True})


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
