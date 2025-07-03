# backend/forms.py
from django import forms
from django.core.validators import EmailValidator, RegexValidator, URLValidator
from django.core.exceptions import ValidationError
from .models import ContactInquiry, PartnerApplication, NewsletterSubscription
import re

class ContactInquiryForm(forms.ModelForm):
    """Form for contact inquiries with comprehensive validation"""
    
    class Meta:
        model = ContactInquiry
        fields = [
            'name', 'email', 'phone', 'subject', 'message', 
            'company', 'website', 'preferred_contact_method'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entrez votre nom complet',
                'maxlength': 100
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'votre.email@exemple.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+237 6XX XXX XXX'
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Veuillez fournir des détails sur votre demande...',
                'maxlength': 5000
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de votre entreprise (optionnel)'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://votre-site.com (optionnel)'
            }),
            'preferred_contact_method': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError("Le nom est requis.")
        if len(name) < 2:
            raise ValidationError("Le nom doit contenir au moins 2 caractères.")
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\'\.]+$', name):
            raise ValidationError("Le nom contient des caractères invalides.")
        return name
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("L'email est requis.")
        
        # Validate email format
        email_validator = EmailValidator()
        try:
            email_validator(email)
        except ValidationError:
            raise ValidationError("Adresse email invalide.")
        
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Remove spaces and normalize
            phone = re.sub(r'\s+', '', phone)
            
            # Validate Cameroon phone number format
            if not re.match(r'^\+?237?[0-9]{9,}$', phone):
                raise ValidationError("Numéro de téléphone camerounais invalide.")
            
            # Normalize to standard format
            if phone.startswith('237'):
                phone = '+' + phone
            elif not phone.startswith('+237'):
                if phone.startswith('6') or phone.startswith('2'):
                    phone = '+237' + phone
        
        return phone
    
    def clean_website(self):
        website = self.cleaned_data.get('website', '').strip()
        if website:
            url_validator = URLValidator()
            try:
                url_validator(website)
            except ValidationError:
                raise ValidationError("URL de site web invalide.")
        return website
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise ValidationError("Le message est requis.")
        if len(message) < 10:
            raise ValidationError("Le message doit contenir au moins 10 caractères.")
        if len(message) > 5000:
            raise ValidationError("Le message ne peut pas dépasser 5000 caractères.")
        return message


class PartnerApplicationForm(forms.ModelForm):
    """Form for partner applications with type-specific validation"""
    
    class Meta:
        model = PartnerApplication
        fields = [
            'partner_type', 'contact_name', 'email', 'phone', 'business_name',
            'cuisine_type', 'capacity', 'opening_hours', 'address', 'city',
            'legal_status', 'tax_id', 'vehicle_type', 'driving_license',
            'investment_amount', 'investment_type', 'business_experience',
            'service_type', 'terms_accepted'
        ]
        widgets = {
            'partner_type': forms.Select(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la personne de contact'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+237 6XX XXX XXX'
            }),
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de votre restaurant/entreprise'
            }),
            'cuisine_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Camerounaise, Internationale, Fast-food'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Nombre de commandes par jour'
            }),
            'opening_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 8h00 - 22h00'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'legal_status': forms.Select(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro d\'identification fiscale'
            }),
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),
            'driving_license': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de permis de conduire'
            }),
            'investment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1000,
                'placeholder': 'Montant en FCFA'
            }),
            'investment_type': forms.Select(attrs={'class': 'form-control'}),
            'business_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Années d\'expérience'
            }),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'terms_accepted': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'required': True
            }),
        }
    
    def clean_contact_name(self):
        name = self.cleaned_data.get('contact_name', '').strip()
        if not name:
            raise ValidationError("Le nom de contact est requis.")
        if len(name) < 2:
            raise ValidationError("Le nom doit contenir au moins 2 caractères.")
        return name
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("L'email est requis.")
        
        email_validator = EmailValidator()
        try:
            email_validator(email)
        except ValidationError:
            raise ValidationError("Adresse email invalide.")
        
        # Check for existing applications with same email
        if PartnerApplication.objects.filter(email=email).exists():
            raise ValidationError("Une candidature existe déjà avec cet email.")
        
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise ValidationError("Le numéro de téléphone est requis.")
        
        phone = re.sub(r'\s+', '', phone)
        if not re.match(r'^\+?237?[0-9]{9,}$', phone):
            raise ValidationError("Numéro de téléphone camerounais invalide.")
        
        # Normalize
        if phone.startswith('237'):
            phone = '+' + phone
        elif not phone.startswith('+237'):
            if phone.startswith('6') or phone.startswith('2'):
                phone = '+237' + phone
        
        return phone
    
    def clean_terms_accepted(self):
        terms_accepted = self.cleaned_data.get('terms_accepted')
        if not terms_accepted:
            raise ValidationError("Vous devez accepter les conditions d'utilisation.")
        return terms_accepted
    
    def clean(self):
        cleaned_data = super().clean()
        partner_type = cleaned_data.get('partner_type')
        
        # Validate required fields based on partner type
        if partner_type == 'restaurant':
            required_fields = ['business_name', 'cuisine_type', 'address', 'city']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"Ce champ est requis pour les restaurants.")
        
        elif partner_type == 'delivery-agent':
            required_fields = ['vehicle_type', 'address', 'city']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"Ce champ est requis pour les livreurs.")
        
        elif partner_type == 'investor':
            required_fields = ['investment_amount', 'investment_type']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"Ce champ est requis pour les investisseurs.")
            
            # Validate minimum investment amount
            investment_amount = cleaned_data.get('investment_amount')
            if investment_amount and investment_amount < 100000:  # 100k FCFA minimum
                self.add_error('investment_amount', "Le montant minimum d'investissement est de 100 000 FCFA.")
        
        elif partner_type == 'other':
            if not cleaned_data.get('service_type'):
                self.add_error('service_type', "Le type de service est requis.")
        
        return cleaned_data


class NewsletterSubscriptionForm(forms.ModelForm):
    """Form for newsletter subscriptions"""
    
    class Meta:
        model = NewsletterSubscription
        fields = ['email', 'preferred_language']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre adresse email'
            }),
            'preferred_language': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("L'adresse email est requise.")
        
        email_validator = EmailValidator()
        try:
            email_validator(email)
        except ValidationError:
            raise ValidationError("Adresse email invalide.")
        
        # Check if already subscribed
        if NewsletterSubscription.objects.filter(email=email, is_active=True).exists():
            raise ValidationError("Cette adresse email est déjà abonnée à notre newsletter.")
        
        return email


class DocumentUploadForm(forms.Form):
    """Form for document uploads"""
    
    ALLOWED_FILE_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/jpg', 
        'image/png'
    ]
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
        })
    )
    document_type = forms.CharField(max_length=30)
    
    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        
        if not uploaded_file:
            raise ValidationError("Aucun fichier sélectionné.")
        
        # Check file size
        if uploaded_file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"Le fichier est trop volumineux. Taille maximum: {self.MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Check file type
        if uploaded_file.content_type not in self.ALLOWED_FILE_TYPES:
            raise ValidationError("Type de fichier non autorisé. Formats acceptés: PDF, DOC, DOCX, JPG, PNG")
        
        return uploaded_file