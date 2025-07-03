# backend/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ContactInquiry, PartnerApplication, PartnerDocument, NewsletterSubscription
from .services.email_service import EmailService

# Initialize email service
email_service = EmailService()

@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'subject', 'status', 'created_at', 
        'responded_at', 'view_message'
    ]
    list_filter = [
        'status', 'subject', 'preferred_contact_method', 'created_at'
    ]
    search_fields = ['name', 'email', 'company', 'message']
    readonly_fields = [
        'created_at', 'updated_at', 'ip_address', 'user_agent'
    ]
    fieldsets = (
        ('Informations de contact', {
            'fields': ('name', 'email', 'phone', 'company', 'website')
        }),
        ('Demande', {
            'fields': ('subject', 'message', 'preferred_contact_method')
        }),
        ('Gestion', {
            'fields': ('status', 'assigned_to', 'admin_notes', 'responded_at')
        }),
        ('Informations techniques', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def view_message(self, obj):
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    view_message.short_description = 'Message (aperçu)'
    
    def save_model(self, request, obj, form, change):
        # Track status changes and send notifications
        if change:
            old_obj = ContactInquiry.objects.get(pk=obj.pk)
            if old_obj.status != obj.status and obj.status == 'resolved':
                obj.responded_at = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_resolved', 'mark_as_in_progress']
    
    def mark_as_resolved(self, request, queryset):
        count = queryset.update(status='resolved', responded_at=timezone.now())
        self.message_user(request, f'{count} demande(s) marquée(s) comme résolue(s).')
    mark_as_resolved.short_description = 'Marquer comme résolu'
    
    def mark_as_in_progress(self, request, queryset):
        count = queryset.update(status='in_progress')
        self.message_user(request, f'{count} demande(s) marquée(s) en cours de traitement.')
    mark_as_in_progress.short_description = 'Marquer en cours de traitement'


class PartnerDocumentInline(admin.TabularInline):
    model = PartnerDocument
    readonly_fields = ['file_name', 'file_size', 'mime_type', 'created_at', 'is_verified']
    extra = 0
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'contact_name', 'partner_type', 'email', 'city', 
        'status', 'created_at', 'view_application_id'
    ]
    list_filter = [
        'partner_type', 'status', 'legal_status', 'created_at', 'city'
    ]
    search_fields = [
        'contact_name', 'email', 'business_name', 'application_id'
    ]
    readonly_fields = [
        'application_id', 'created_at', 'updated_at', 
        'ip_address', 'user_agent'
    ]
    inlines = [PartnerDocumentInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('application_id', 'partner_type', 'contact_name', 'email', 'phone')
        }),
        ('Informations business', {
            'fields': ('business_name', 'cuisine_type', 'capacity', 'opening_hours'),
            'classes': ('collapse',)
        }),
        ('Localisation', {
            'fields': ('address', 'city'),
            'classes': ('collapse',)
        }),
        ('Informations légales', {
            'fields': ('legal_status', 'tax_id'),
            'classes': ('collapse',)
        }),
        ('Livreur', {
            'fields': ('vehicle_type', 'driving_license'),
            'classes': ('collapse',)
        }),
        ('Investisseur', {
            'fields': ('investment_amount', 'investment_type', 'business_experience'),
            'classes': ('collapse',)
        }),
        ('Autre service', {
            'fields': ('service_type',),
            'classes': ('collapse',)
        }),
        ('Gestion candidature', {
            'fields': ('status', 'terms_accepted', 'assigned_reviewer', 'reviewer_notes', 'reviewed_at', 'approval_date')
        }),
        ('Informations techniques', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def view_application_id(self, obj):
        return str(obj.application_id)[:8] + '...'
    view_application_id.short_description = 'ID candidature'
    
    def save_model(self, request, obj, form, change):
        # Track status changes and send email notifications
        send_email = False
        old_status = None
        
        if change:
            old_obj = PartnerApplication.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                old_status = old_obj.status
                send_email = True
                obj.reviewed_at = timezone.now()
                if obj.status == 'approved':
                    obj.approval_date = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Send status update email
        if send_email and old_status:
            try:
                email_service.send_partner_status_update(obj, old_status, obj.status)
            except Exception as e:
                self.message_user(request, f'Erreur envoi email: {str(e)}', level='WARNING')
    
    actions = ['approve_applications', 'reject_applications', 'mark_under_review']
    
    def approve_applications(self, request, queryset):
        count = 0
        for application in queryset:
            old_status = application.status
            application.status = 'approved'
            application.reviewed_at = timezone.now()
            application.approval_date = timezone.now()
            application.save()
            
            try:
                email_service.send_partner_status_update(application, old_status, 'approved')
                count += 1
            except Exception as e:
                self.message_user(request, f'Erreur email pour {application.email}: {str(e)}', level='WARNING')
        
        self.message_user(request, f'{count} candidature(s) approuvée(s).')
    approve_applications.short_description = 'Approuver les candidatures sélectionnées'
    
    def reject_applications(self, request, queryset):
        count = 0
        for application in queryset:
            old_status = application.status
            application.status = 'rejected'
            application.reviewed_at = timezone.now()
            application.save()
            
            try:
                email_service.send_partner_status_update(application, old_status, 'rejected')
                count += 1
            except Exception as e:
                self.message_user(request, f'Erreur email pour {application.email}: {str(e)}', level='WARNING')
        
        self.message_user(request, f'{count} candidature(s) rejetée(s).')
    reject_applications.short_description = 'Rejeter les candidatures sélectionnées'
    
    def mark_under_review(self, request, queryset):
        count = queryset.update(status='under_review', reviewed_at=timezone.now())
        self.message_user(request, f'{count} candidature(s) marquée(s) en cours d\'examen.')
    mark_under_review.short_description = 'Marquer en cours d\'examen'


@admin.register(PartnerDocument)
class PartnerDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'application', 'document_type', 'file_name', 
        'file_size_display', 'is_verified', 'created_at'
    ]
    list_filter = ['document_type', 'is_verified', 'mime_type', 'created_at']
    search_fields = ['application__contact_name', 'application__email', 'file_name']
    readonly_fields = ['file_name', 'file_size', 'mime_type', 'created_at']
    
    def file_size_display(self, obj):
        size = obj.file_size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        else:
            return f'{size / (1024 * 1024):.1f} MB'
    file_size_display.short_description = 'Taille'
    
    actions = ['verify_documents', 'unverify_documents']
    
    def verify_documents(self, request, queryset):
        count = queryset.update(is_verified=True)
        self.message_user(request, f'{count} document(s) vérifié(s).')
    verify_documents.short_description = 'Marquer comme vérifié'
    
    def unverify_documents(self, request, queryset):
        count = queryset.update(is_verified=False)
        self.message_user(request, f'{count} document(s) marqué(s) comme non vérifié.')
    unverify_documents.short_description = 'Marquer comme non vérifié'


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'preferred_language', 'is_active', 
        'subscribed_at', 'confirmed_at'
    ]
    list_filter = [
        'is_active', 'preferred_language', 'subscribed_at', 'confirmed_at'
    ]
    search_fields = ['email']
    readonly_fields = [
        'subscribed_at', 'confirmation_sent_at', 'confirmed_at',
        'unsubscribed_at', 'ip_address', 'user_agent'
    ]
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions', 'send_welcome_email']
    
    def activate_subscriptions(self, request, queryset):
        count = queryset.update(is_active=True, unsubscribed_at=None)
        self.message_user(request, f'{count} abonnement(s) activé(s).')
    activate_subscriptions.short_description = 'Activer les abonnements'
    
    def deactivate_subscriptions(self, request, queryset):
        count = queryset.update(is_active=False, unsubscribed_at=timezone.now())
        self.message_user(request, f'{count} abonnement(s) désactivé(s).')
    deactivate_subscriptions.short_description = 'Désactiver les abonnements'
    
    def send_welcome_email(self, request, queryset):
        count = 0
        for subscription in queryset.filter(is_active=True):
            try:
                email_service.send_newsletter_welcome(subscription)
                count += 1
            except Exception as e:
                self.message_user(request, f'Erreur email pour {subscription.email}: {str(e)}', level='WARNING')
        
        self.message_user(request, f'{count} email(s) de bienvenue envoyé(s).')
    send_welcome_email.short_description = 'Envoyer email de bienvenue'


# Customize admin site
admin.site.site_header = 'EatFast Administration'
admin.site.site_title = 'EatFast Admin'
admin.site.index_title = 'Tableau de bord administrateur'