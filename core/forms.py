from django import forms
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Visiteur, Visite, Service, Porte, AgentProfile


class VisiteurForm(forms.ModelForm):
    class Meta:
        model = Visiteur
        fields = ['nom', 'prenom', 'numero_cni', 'date_naissance', 'sexe', 'profession', 'telephone', 'adresse',
                  'scan_cni_recto', 'scan_cni_verso']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_nom'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_prenom'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_numero_cni'}),
            'date_naissance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_date_naissance'}),
            'sexe': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_sexe'}),
            'profession': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_profession'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scan_cni_recto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'onchange': 'handleOCR(this)'}),
            'scan_cni_verso': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_scan_cni_recto(self):
        f = self.cleaned_data.get('scan_cni_recto')
        if f and hasattr(f, 'size') and f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La taille du fichier ne doit pas dépasser 5 Mo.")
        return f


class VisiteurEditForm(forms.ModelForm):
    class Meta:
        model = Visiteur
        fields = ['nom', 'prenom', 'numero_cni', 'date_naissance', 'sexe', 'profession', 'telephone', 'adresse',
                  'scan_cni_recto', 'scan_cni_verso']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cni': forms.TextInput(attrs={'class': 'form-control'}),
            'date_naissance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexe': forms.Select(attrs={'class': 'form-select select2'}),
            'profession': forms.TextInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scan_cni_recto': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'scan_cni_verso': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scan_cni_recto'].required = False
        self.fields['scan_cni_verso'].required = False


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['nom', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PorteForm(forms.ModelForm):
    class Meta:
        model = Porte
        fields = ['numero', 'description']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class VisiteForm(forms.ModelForm):
    class Meta:
        model = Visite
        fields = ['visiteur', 'service_visite', 'porte_entree', 'motif', 'heure_entree', 'observations']
        widgets = {
            'visiteur': forms.Select(attrs={'class': 'form-select select2'}),
            'service_visite': forms.Select(attrs={'class': 'form-select select2'}),
            'porte_entree': forms.Select(attrs={'class': 'form-select select2'}),
            'motif': forms.TextInput(attrs={'class': 'form-control'}),
            'heure_entree': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les visiteurs non présents et non archivés peuvent être sélectionnés
        self.fields['visiteur'].queryset = Visiteur.objects.filter(is_archived=False).exclude(visites__statut='PRESENT')
        self.fields['heure_entree'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')
        self.fields['heure_entree'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        
        # Définir le service par défaut sur 'Secrétariat' si disponible
        secretariat = Service.objects.filter(nom__iexact='Secrétariat').first()
        if secretariat:
            self.fields['service_visite'].initial = secretariat
        
        # Gestion du champ porte_entree selon le rôle
        if user and not user.is_superuser:
            # Pour un agent, on cache le champ car c'est automatique
            self.fields['porte_entree'].required = False
            self.fields['porte_entree'].widget = forms.HiddenInput()
        else:
            self.fields['porte_entree'].required = True
            self.fields['porte_entree'].label = "Porte d'entrée"
            self.fields['porte_entree'].queryset = Porte.objects.all().order_by('numero')


class RapportVisiteForm(forms.Form):
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date de début"
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date de fin"
    )
    service = forms.ModelChoiceField(
        queryset=Service.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Filtrer par service"
    )
    porte = forms.ModelChoiceField(
        queryset=Porte.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Filtrer par porte"
    )
    visiteur = forms.ModelChoiceField(
        queryset=Visiteur.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Filtrer par visiteur"
    )
    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(is_superuser=False),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Filtrer par agent"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.now().date()
        self.fields['date_debut'].initial = today.replace(day=1)
        self.fields['date_fin'].initial = today


class UserRegistrationForm(forms.ModelForm):
    porte_actuelle = forms.ModelChoiceField(
        queryset=Porte.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        label="Affectation Porte"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = "Prénom"
        self.fields['last_name'].label = "Nom"
        self.fields['email'].label = "Email (Optionnel)"
        self.fields['is_active'].label = "Compte actif"
        self.fields['is_active'].initial = True
        
        if self.instance.pk:
            try:
                self.fields['porte_actuelle'].initial = self.instance.profile.porte_actuelle
            except AgentProfile.DoesNotExist:
                pass
