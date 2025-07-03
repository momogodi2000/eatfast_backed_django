# backend/models.py
from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.utils import timezone
import uuid

class ContactInquiry(models.Model):
    """Model for storing contact form submissions"""
    
    SUBJECT_CHOICES = [
        ('general', 'Demande générale'),
        ('order', 'Problème de commande'),
        ('delivery', 'Problème de livraison'),
        ('payment', 'Problème de paiement'),
        ('restaurant', 'Demande restaurant partenaire'),
        ('driver', 'Devenir livreur'),
        ('business', 'Partenariat commercial'),
        ('feedback', 'Retour d\'expérience'),
        ('complaint', 'Plainte'),
        ('other', 'Autre'),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Appel téléphonique'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours de traitement'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
    ]
    
    # Contact Information
    name = models.CharField(max_length=100, verbose_name="Nom complet")
    email = models.EmailField(validators=[EmailValidator()], verbose_name="Email")
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[RegexValidator(
            regex=r'^\+?237?[0-9]{9,}$',
            message="Numéro de téléphone camerounais invalide"
        )],
        verbose_name="Téléphone"
    )
    
    # Inquiry Details
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField(max_length=5000, verbose_name="Message")
    company = models.CharField(max_length=200, blank=True, null=True, verbose_name="Entreprise")
    website = models.URLField(blank=True, null=True, verbose_name="Site web")
    preferred_contact_method = models.CharField(
        max_length=20, 
        choices=CONTACT_METHOD_CHOICES, 
        default='email'
    )
    
    # Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True, null=True, verbose_name="Notes administrateur")
    assigned_to = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Demande de contact"
        verbose_name_plural = "Demandes de contact"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.created_at.strftime('%d/%m/%Y')})"


class PartnerApplication(models.Model):
    """Model for partner applications (restaurants, delivery agents, investors)"""
    
    PARTNER_TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('delivery-agent', 'Agent Livreur'),
        ('investor', 'Investisseur'),
        ('other', 'Autre'),
    ]
    
    APPLICATION_STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('under_review', 'En cours d\'examen'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('on_hold', 'En suspens'),
        ('additional_info_required', 'Informations supplémentaires requises'),
    ]
    
    LEGAL_STATUS_CHOICES = [
        ('individual', 'Personne physique'),
        ('sarl', 'SARL'),
        ('sa', 'SA'),
        ('gie', 'GIE'),
        ('cooperative', 'Coopérative'),
        ('association', 'Association'),
        ('other', 'Autre'),
    ]
    
    VEHICLE_TYPE_CHOICES = [
        ('motorcycle', 'Moto'),
        ('bicycle', 'Vélo'),
        ('car', 'Voiture'),
        ('scooter', 'Scooter électrique'),
        ('walking', 'À pied'),
    ]
    
    INVESTMENT_TYPE_CHOICES = [
        ('financial', 'Investissement financier'),
        ('strategic', 'Partenariat stratégique'),
        ('technology', 'Apport technologique'),
        ('real_estate', 'Immobilier'),
        ('equipment', 'Équipements'),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('logistics', 'Logistique'),
        ('marketing', 'Marketing'),
        ('technology', 'Technologie'),
        ('consulting', 'Conseil'),
        ('other', 'Autre'),
    ]
    
    # Unique Application ID
    application_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Basic Information
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES)
    contact_name = models.CharField(max_length=100, verbose_name="Personne de contact")
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?237?[0-9]{9,}$',
            message="Numéro de téléphone camerounais invalide"
        )]
    )
    
    # Business Information (for restaurants)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    cuisine_type = models.CharField(max_length=100, blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True, help_text="Commandes par jour")
    opening_hours = models.CharField(max_length=100, blank=True, null=True)
    
    # Location Information
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    # Legal Information
    legal_status = models.CharField(max_length=20, choices=LEGAL_STATUS_CHOICES, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Numéro fiscal")
    
    # Delivery Agent Specific
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, blank=True, null=True)
    driving_license = models.CharField(max_length=50, blank=True, null=True)
    
    # Investor Specific
    investment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE_CHOICES, blank=True, null=True)
    business_experience = models.PositiveIntegerField(blank=True, null=True, help_text="Années d'expérience")
    
    # Other Service Provider
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, blank=True, null=True)
    
    # Application Status
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS_CHOICES, default='pending')
    terms_accepted = models.BooleanField(default=False)
    
    # Tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Admin fields
    reviewer_notes = models.TextField(blank=True, null=True)
    assigned_reviewer = models.CharField(max_length=100, blank=True, null=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Candidature partenaire"
        verbose_name_plural = "Candidatures partenaires"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['application_id']),
            models.Index(fields=['partner_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.contact_name} - {self.get_partner_type_display()} ({self.application_id})"


class PartnerDocument(models.Model):
    """Model for storing partner application documents"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('id_document', 'Pièce d\'identité'),
        ('health_certificate', 'Certificat de santé'),
        ('menu', 'Menu/Liste de prix'),
        ('driving_license_doc', 'Permis de conduire'),
        ('vehicle_registration', 'Carte grise'),
        ('business_plan', 'Plan d\'affaires'),
        ('financial_statements', 'États financiers'),
        ('photo', 'Photo'),
        ('other', 'Autre'),
    ]
    
    application = models.ForeignKey(PartnerApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # Size in bytes
    file_path = models.CharField(max_length=500)  # Relative path or cloud storage URL
    mime_type = models.CharField(max_length=100)
    
    # File validation
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Document partenaire"
        verbose_name_plural = "Documents partenaires"
    
    def __str__(self):
        return f"{self.application.contact_name} - {self.get_document_type_display()}"


class NewsletterSubscription(models.Model):
    """Model for newsletter subscriptions from footer"""
    
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10, 
        choices=[('fr', 'Français'), ('en', 'English')], 
        default='fr'
    )
    
    # Tracking
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = "Abonnement newsletter"
        verbose_name_plural = "Abonnements newsletter"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.email} ({'Actif' if self.is_active else 'Inactif'})"