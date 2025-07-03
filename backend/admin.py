# backend/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.utils import timezone
import csv

from .models import (
    User, ContactMessage, ContactResponse, PartnerApplication,
    PartnerDocument, ContactAnalytics, PartnerAnalytics
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_phone_verified', 'date_joined']
    list_filter = ['user_type', 'is_phone_verified', 'is_active']
    search_fields = ['username', 'email', 'phone_number']
    readonly_fields = ['id', 'date_joined', 'last_login']

class ContactResponseInline(admin.TabularInline):
    model = ContactResponse
    extra = 0
    readonly_fields = ['created_at']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'subject', 'status', 'priority', 
        'created_at', 'assigned_to'
    ]
    list_filter = [
        'status', 'priority', 'subject', 'preferred_contact_method',
        'created_at', 'resolved_at'
    ]
    search_fields = ['name', 'email', 'company', 'message']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'resolved_at',
        'utm_source', 'utm_medium', 'utm_campaign', 'ip_address'
    ]
    inlines = [ContactResponseInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations de contact', {
            'fields': ('name', 'email', 'phone', 'company', 'website')
        }),
        ('Message', {
            'fields': ('subject', 'message', 'preferred_contact_method')
        }),
        ('Gestion', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Tracking', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_resolved', 'export_to_csv']
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{updated} messages marked as resolved.')
    mark_as_resolved.short_description = "Mark selected messages as resolved"
    
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contact_messages.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Email', 'Phone', 'Company', 'Subject', 'Status',
            'Priority', 'Created', 'Resolved'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.name, obj.email, obj.phone or '', obj.company or '',
                obj.get_subject_display(), obj.get_status_display(),
                obj.get_priority_display(), obj.created_at.strftime('%Y-%m-%d %H:%M'),
                obj.resolved_at.strftime('%Y-%m-%d %H:%M') if obj.resolved_at else ''
            ])
        
        return response
    export_to_csv.short_description = "Export selected to CSV"

class PartnerDocumentInline(admin.TabularInline):
    model = PartnerDocument
    extra = 0
    readonly_fields = ['uploaded_at', 'file_size', 'mime_type']

@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'contact_name', 'email', 'partner_type', 'status',
        'city', 'created_at', 'reviewer'
    ]
    list_filter = [
        'partner_type', 'status', 'legal_status', 'vehicle_type',
        'investment_type', 'city', 'created_at', 'reviewed_at'
    ]
    search_fields = [
        'contact_name', 'email', 'business_name', 'city', 'cuisine_type'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'reviewed_at', 'approved_at'
    ]
    inlines = [PartnerDocumentInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Type de partenaire', {
            'fields': ('partner_type', 'status')
        }),
        ('Informations de contact', {
            'fields': ('contact_name', 'email', 'phone')
        }),
        ('Informations d\'entreprise', {
            'fields': (
                'business_name', 'cuisine_type', 'capacity', 'opening_hours',
                'legal_status', 'tax_id'
            ),
            'classes': ('collapse',)
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Spécifique Livreur', {
            'fields': ('vehicle_type', 'driving_license'),
            'classes': ('collapse',)
        }),
        ('Spécifique Investisseur', {
            'fields': ('investment_amount', 'investment_type', 'business_experience'),
            'classes': ('collapse',)
        }),
        ('Spécifique Autre', {
            'fields': ('service_type',),
            'classes': ('collapse',)
        }),
        ('Examen', {
            'fields': ('reviewer', 'review_notes', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'reviewed_at', 'approved_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_applications', 'export_to_csv']
    
    def approve_applications(self, request, queryset):
        updated = 0
        for application in queryset.filter(status='pending'):
            application.approve(request.user)
            updated += 1
        
        self.message_user(request, f'{updated} applications approved.')
    approve_applications.short_description = "Approve selected applications"
    
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="partner_applications.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Contact Name', 'Email', 'Partner Type', 'Business Name',
            'City', 'Status', 'Created', 'Reviewed'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.contact_name, obj.email, obj.get_partner_type_display(),
                obj.business_name or '', obj.city or '', obj.get_status_display(),
                obj.created_at.strftime('%Y-%m-%d %H:%M'),
                obj.reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.reviewed_at else ''
            ])
        
        return response
    export_to_csv.short_description = "Export selected to CSV"

@admin.register(PartnerDocument)
class PartnerDocumentAdmin(admin.ModelAdmin):
    list_display = ['application', 'document_type', 'original_filename', 'file_size', 'uploaded_at']
    list_filter = ['document_type', 'mime_type', 'uploaded_at']
    search_fields = ['application__contact_name', 'original_filename']
    readonly_fields = ['uploaded_at', 'file_size', 'mime_type']

@admin.register(ContactAnalytics)
class ContactAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_messages', 'new_messages', 'resolved_messages',
        'avg_response_time_hours'
    ]
    list_filter = ['date']
    date_hierarchy = 'date'
    readonly_fields = [
        'date', 'total_messages', 'new_messages', 'resolved_messages',
        'avg_response_time_hours'
    ]

@admin.register(PartnerAnalytics)
class PartnerAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_applications', 'pending_applications',
        'approved_applications', 'restaurant_applications'
    ]
    list_filter = ['date']
    date_hierarchy = 'date'
    readonly_fields = [
        'date', 'total_applications', 'pending_applications',
        'approved_applications', 'rejected_applications',
        'restaurant_applications', 'delivery_applications',
        'investor_applications'
    ]

# Customize admin site
admin.site.site_header = "EatFast Administration"
admin.site.site_title = "EatFast Admin"
admin.site.index_title = "Welcome to EatFast Administration"