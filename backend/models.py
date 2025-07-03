# backend/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import os

# Custom User Model
class User(AbstractUser):
    """Extended User model for EatFast platform"""
    USER_TYPE_CHOICES = [
        ('customer', _('Customer')),
        ('restaurant', _('Restaurant')),
        ('delivery_agent', _('Delivery Agent')),
        ('admin', _('Admin')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    phone_number = models.CharField(
        max_length=20, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$')],
        blank=True, null=True
    )
    is_phone_verified = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Fix for auth clash - add related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="backend_user_set",
        related_query_name="backend_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="backend_user_set",
        related_query_name="backend_user",
    )

    def __str__(self):
        return f"{self.username} ({self.user_type})"

# Contact Management Models
class ContactMessage(models.Model):
    """Model for handling contact form submissions"""
    
    SUBJECT_CHOICES = [
        ('general', _('Question générale')),
        ('support', _('Support technique')),
        ('partnership', _('Partenariat')),
        ('complaint', _('Plainte')),
        ('suggestion', _('Suggestion')),
        ('billing', _('Facturation')),
        ('delivery', _('Livraison')),
        ('restaurant', _('Restaurant')),
        ('other', _('Autre')),
    ]
    
    STATUS_CHOICES = [
        ('new', _('Nouveau')),
        ('in_progress', _('En cours')),
        ('resolved', _('Résolu')),
        ('closed', _('Fermé')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Basse')),
        ('medium', _('Moyenne')),
        ('high', _('Haute')),
        ('urgent', _('Urgente')),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('email', _('Email')),
        ('phone', _('Téléphone')),
        ('whatsapp', _('WhatsApp')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_('Nom'))
    email = models.EmailField(validators=[EmailValidator()], verbose_name=_('Email'))
    phone = models.CharField(
        max_length=20, 
        validators=[RegexValidator(r'^\+?237?\d{9,15}$')],
        blank=True, null=True,
        verbose_name=_('Téléphone')
    )
    company = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Entreprise'))
    website = models.URLField(blank=True, null=True, verbose_name=_('Site web'))
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general', verbose_name=_('Sujet'))
    message = models.TextField(verbose_name=_('Message'))
    preferred_contact_method = models.CharField(
        max_length=20, 
        choices=CONTACT_METHOD_CHOICES, 
        default='email',
        verbose_name=_('Méthode de contact préférée')
    )
    
    # Tracking fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name=_('Statut'))
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Priorité'))
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Assigné à'))
    
    # UTM and analytics
    utm_source = models.CharField(max_length=100, blank=True, null=True)
    utm_medium = models.CharField(max_length=100, blank=True, null=True)
    utm_campaign = models.CharField(max_length=100, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Mis à jour le'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Résolu le'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Message de contact')
        verbose_name_plural = _('Messages de contact')
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['subject', 'priority']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()} ({self.status})"
    
    def mark_resolved(self):
        """Mark the contact message as resolved"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])

class ContactResponse(models.Model):
    """Model for responses to contact messages"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_message = models.ForeignKey(
        ContactMessage, 
        on_delete=models.CASCADE, 
        related_name='responses',
        verbose_name=_('Message de contact')
    )
    responder = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Répondant'))
    response_text = models.TextField(verbose_name=_('Réponse'))
    is_public = models.BooleanField(default=False, verbose_name=_('Réponse publique'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Réponse au contact')
        verbose_name_plural = _('Réponses aux contacts')
    
    def __str__(self):
        return f"Response to {self.contact_message.name} by {self.responder.username}"

# Partner Application Models
class PartnerApplication(models.Model):
    """Model for partner applications"""
    
    PARTNER_TYPE_CHOICES = [
        ('restaurant', _('Restaurant')),
        ('delivery-agent', _('Agent de livraison')),
        ('investor', _('Investisseur')),
        ('other', _('Autre')),
    ]
    
    APPLICATION_STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('under_review', _('En cours d\'examen')),
        ('approved', _('Approuvé')),
        ('rejected', _('Rejeté')),
        ('on_hold', _('En attente')),
        ('additional_info_required', _('Informations supplémentaires requises')),
    ]
    
    LEGAL_STATUS_CHOICES = [
        ('individual', _('Entreprise individuelle')),
        ('sarl', _('SARL')),
        ('sa', _('SA')),
        ('sas', _('SAS')),
        ('association', _('Association')),
        ('cooperative', _('Coopérative')),
    ]
    
    VEHICLE_TYPE_CHOICES = [
        ('motorcycle', _('Moto')),
        ('bicycle', _('Vélo')),
        ('car', _('Voiture')),
        ('scooter', _('Scooter')),
        ('on_foot', _('À pied')),
    ]
    
    INVESTMENT_TYPE_CHOICES = [
        ('equity', _('Participation au capital')),
        ('loan', _('Prêt')),
        ('franchise', _('Franchise')),
        ('joint_venture', _('Coentreprise')),
        ('sponsorship', _('Parrainage')),
    ]
    
    SERVICE_TYPE_CHOICES = [
        ('marketing', _('Marketing')),
        ('technology', _('Technologie')),
        ('logistics', _('Logistique')),
        ('payment', _('Paiement')),
        ('consulting', _('Conseil')),
        ('other', _('Autre')),
    ]
    
    # Primary Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    partner_type = models.CharField(max_length=20, choices=PARTNER_TYPE_CHOICES, verbose_name=_('Type de partenaire'))
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS_CHOICES, default='pending', verbose_name=_('Statut'))
    
    # Contact Information
    contact_name = models.CharField(max_length=100, verbose_name=_('Nom du contact'))
    email = models.EmailField(validators=[EmailValidator()], verbose_name=_('Email'))
    phone = models.CharField(
        max_length=20, 
        validators=[RegexValidator(r'^\+?237?\d{9,15}$')],
        verbose_name=_('Téléphone')
    )
    
    # Business Information (Restaurant)
    business_name = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Nom de l\'entreprise'))
    cuisine_type = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Type de cuisine'))
    capacity = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Capacité quotidienne'))
    opening_hours = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Heures d\'ouverture'))
    
    # Location Information
    address = models.TextField(blank=True, null=True, verbose_name=_('Adresse'))
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Ville'))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Legal Information
    legal_status = models.CharField(max_length=20, choices=LEGAL_STATUS_CHOICES, blank=True, null=True, verbose_name=_('Statut juridique'))
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Numéro d\'identification fiscale'))
    
    # Delivery Agent Specific
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, blank=True, null=True, verbose_name=_('Type de véhicule'))
    driving_license = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Numéro de permis'))
    
    # Investor Specific
    investment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name=_('Montant d\'investissement'))
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE_CHOICES, blank=True, null=True, verbose_name=_('Type d\'investissement'))
    business_experience = models.PositiveIntegerField(blank=True, null=True, verbose_name=_('Années d\'expérience'))
    
    # Other Service Specific
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, blank=True, null=True, verbose_name=_('Type de service'))
    
    # Application Processing
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_notes = models.TextField(blank=True, null=True, verbose_name=_('Notes d\'examen'))
    rejection_reason = models.TextField(blank=True, null=True, verbose_name=_('Raison du rejet'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Créé le'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Mis à jour le'))
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Examiné le'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approuvé le'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Candidature de partenaire')
        verbose_name_plural = _('Candidatures de partenaires')
        indexes = [
            models.Index(fields=['partner_type', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.contact_name} - {self.get_partner_type_display()} ({self.status})"
    
    def approve(self, reviewer):
        """Approve the partner application"""
        self.status = 'approved'
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'reviewer', 'reviewed_at', 'approved_at'])
    
    def reject(self, reviewer, reason):
        """Reject the partner application"""
        self.status = 'rejected'
        self.reviewer = reviewer
        self.rejection_reason = reason
        self.reviewed_at = timezone.now()
        self.save(update_fields=['status', 'reviewer', 'rejection_reason', 'reviewed_at'])

def upload_partner_document(instance, filename):
    """Generate upload path for partner documents"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"partner_documents/{instance.application.id}/{filename}"

class PartnerDocument(models.Model):
    """Model for partner application documents"""
    
    DOCUMENT_TYPE_CHOICES = [
        ('id_document', _('Document d\'identité')),
        ('health_certificate', _('Certificat de santé')),
        ('menu', _('Menu')),
        ('driving_license', _('Permis de conduire')),
        ('vehicle_registration', _('Carte grise')),
        ('business_plan', _('Plan d\'affaires')),
        ('financial_statements', _('États financiers')),
        ('photo', _('Photo')),
        ('other', _('Autre')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(PartnerApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES, verbose_name=_('Type de document'))
    file = models.FileField(upload_to=upload_partner_document, verbose_name=_('Fichier'))
    original_filename = models.CharField(max_length=255, verbose_name=_('Nom de fichier original'))
    file_size = models.PositiveIntegerField(verbose_name=_('Taille du fichier'))
    mime_type = models.CharField(max_length=100, verbose_name=_('Type MIME'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Téléchargé le'))
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('Document partenaire')
        verbose_name_plural = _('Documents partenaires')
        unique_together = ['application', 'document_type']
    
    def __str__(self):
        return f"{self.application.contact_name} - {self.get_document_type_display()}"
    
    def delete(self, *args, **kwargs):
        """Delete file when model instance is deleted"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)

# Analytics and Tracking Models
class ContactAnalytics(models.Model):
    """Model for contact form analytics"""
    
    date = models.DateField(unique=True)
    total_messages = models.PositiveIntegerField(default=0)
    new_messages = models.PositiveIntegerField(default=0)
    resolved_messages = models.PositiveIntegerField(default=0)
    avg_response_time_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name = _('Analyse des contacts')
        verbose_name_plural = _('Analyses des contacts')

class PartnerAnalytics(models.Model):
    """Model for partner application analytics"""
    
    date = models.DateField(unique=True)
    total_applications = models.PositiveIntegerField(default=0)
    pending_applications = models.PositiveIntegerField(default=0)
    approved_applications = models.PositiveIntegerField(default=0)
    rejected_applications = models.PositiveIntegerField(default=0)
    restaurant_applications = models.PositiveIntegerField(default=0)
    delivery_applications = models.PositiveIntegerField(default=0)
    investor_applications = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name = _('Analyse des partenaires')
        verbose_name_plural = _('Analyses des partenaires')