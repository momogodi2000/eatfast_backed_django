# backend/serializers.py
from rest_framework import serializers
from .models import ContactInquiry, PartnerApplication, PartnerDocument, NewsletterSubscription
from .forms import ContactInquiryForm, PartnerApplicationForm, NewsletterSubscriptionForm
import re

class ContactInquirySerializer(serializers.ModelSerializer):
    """Serializer for contact inquiries"""
    
    class Meta:
        model = ContactInquiry
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message', 
            'company', 'website', 'preferred_contact_method', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate name field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le nom est requis.")
        
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Le nom doit contenir au moins 2 caractères.")
        
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\'\.]+$', value):
            raise serializers.ValidationError("Le nom contient des caractères invalides.")
        
        return value
    
    def validate_email(self, value):
        """Validate email field"""
        if not value:
            raise serializers.ValidationError("L'email est requis.")
        
        # Basic email validation is handled by EmailField
        return value.strip().lower()
    
    def validate_phone(self, value):
        """Validate phone field"""
        if value:
            phone = re.sub(r'\s+', '', value.strip())
            if not re.match(r'^\+?237?[0-9]{9,}$', phone):
                raise serializers.ValidationError("Numéro de téléphone camerounais invalide.")
            
            # Normalize format
            if phone.startswith('237'):
                phone = '+' + phone
            elif not phone.startswith('+237'):
                if phone.startswith('6') or phone.startswith('2'):
                    phone = '+237' + phone
            
            return phone
        return value
    
    def validate_message(self, value):
        """Validate message field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le message est requis.")
        
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Le message doit contenir au moins 10 caractères.")
        
        if len(value) > 5000:
            raise serializers.ValidationError("Le message ne peut pas dépasser 5000 caractères.")
        
        return value
    
    def create(self, validated_data):
        """Create contact inquiry with additional tracking data"""
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PartnerApplicationSerializer(serializers.ModelSerializer):
    """Serializer for partner applications"""
    
    documents = serializers.SerializerMethodField()
    
    class Meta:
        model = PartnerApplication
        fields = [
            'application_id', 'partner_type', 'contact_name', 'email', 'phone',
            'business_name', 'cuisine_type', 'capacity', 'opening_hours',
            'address', 'city', 'legal_status', 'tax_id', 'vehicle_type',
            'driving_license', 'investment_amount', 'investment_type',
            'business_experience', 'service_type', 'status', 'terms_accepted',
            'created_at', 'updated_at', 'documents'
        ]
        read_only_fields = ['application_id', 'status', 'created_at', 'updated_at', 'documents']
    
    def get_documents(self, obj):
        """Get uploaded documents for this application"""
        documents = obj.documents.all()
        return PartnerDocumentSerializer(documents, many=True).data
    
    def validate_contact_name(self, value):
        """Validate contact name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Le nom de contact est requis.")
        
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Le nom doit contenir au moins 2 caractères.")
        
        return value
    
    def validate_email(self, value):
        """Validate email and check for duplicates"""
        if not value:
            raise serializers.ValidationError("L'email est requis.")
        
        value = value.strip().lower()
        
        # Check for existing applications (excluding current instance during updates)
        queryset = PartnerApplication.objects.filter(email=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("Une candidature existe déjà avec cet email.")
        
        return value
    
    def validate_phone(self, value):
        """Validate phone field"""
        if not value:
            raise serializers.ValidationError("Le numéro de téléphone est requis.")
        
        phone = re.sub(r'\s+', '', value.strip())
        if not re.match(r'^\+?237?[0-9]{9,}$', phone):
            raise serializers.ValidationError("Numéro de téléphone camerounais invalide.")
        
        # Normalize format
        if phone.startswith('237'):
            phone = '+' + phone
        elif not phone.startswith('+237'):
            if phone.startswith('6') or phone.startswith('2'):
                phone = '+237' + phone
        
        return phone
    
    def validate_terms_accepted(self, value):
        """Validate terms acceptance"""
        if not value:
            raise serializers.ValidationError("Vous devez accepter les conditions d'utilisation.")
        return value
    
    def validate(self, data):
        """Cross-field validation based on partner type"""
        partner_type = data.get('partner_type')
        
        if partner_type == 'restaurant':
            required_fields = {
                'business_name': "Le nom de l'entreprise est requis pour les restaurants.",
                'cuisine_type': "Le type de cuisine est requis pour les restaurants.",
                'address': "L'adresse est requise pour les restaurants.",
                'city': "La ville est requise pour les restaurants."
            }
            
            for field, error_message in required_fields.items():
                if not data.get(field):
                    raise serializers.ValidationError({field: error_message})
        
        elif partner_type == 'delivery-agent':
            required_fields = {
                'vehicle_type': "Le type de véhicule est requis pour les livreurs.",
                'address': "L'adresse est requise pour les livreurs.",
                'city': "La ville est requise pour les livreurs."
            }
            
            for field, error_message in required_fields.items():
                if not data.get(field):
                    raise serializers.ValidationError({field: error_message})
        
        elif partner_type == 'investor':
            required_fields = {
                'investment_amount': "Le montant d'investissement est requis pour les investisseurs.",
                'investment_type': "Le type d'investissement est requis pour les investisseurs."
            }
            
            for field, error_message in required_fields.items():
                if not data.get(field):
                    raise serializers.ValidationError({field: error_message})
            
            # Validate minimum investment amount
            investment_amount = data.get('investment_amount')
            if investment_amount and investment_amount < 100000:
                raise serializers.ValidationError({
                    'investment_amount': "Le montant minimum d'investissement est de 100 000 FCFA."
                })
        
        elif partner_type == 'other':
            if not data.get('service_type'):
                raise serializers.ValidationError({
                    'service_type': "Le type de service est requis pour les autres partenaires."
                })
        
        return data
    
    def create(self, validated_data):
        """Create partner application with tracking data"""
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PartnerDocumentSerializer(serializers.ModelSerializer):
    """Serializer for partner documents"""
    
    class Meta:
        model = PartnerDocument
        fields = [
            'id', 'document_type', 'file_name', 'file_size', 
            'mime_type', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'file_size', 'mime_type', 'is_verified', 'created_at']


class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for newsletter subscriptions"""
    
    class Meta:
        model = NewsletterSubscription
        fields = [
            'id', 'email', 'preferred_language', 'subscribed_at', 
            'is_active', 'confirmed_at'
        ]
        read_only_fields = ['id', 'subscribed_at', 'is_active', 'confirmed_at']
    
    def validate_email(self, value):
        """Validate email and check for existing subscriptions"""
        if not value:
            raise serializers.ValidationError("L'adresse email est requise.")
        
        value = value.strip().lower()
        
        # Check if already subscribed and active
        if NewsletterSubscription.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("Cette adresse email est déjà abonnée à notre newsletter.")
        
        return value
    
    def create(self, validated_data):
        """Create newsletter subscription with tracking data"""
        request = self.context.get('request')
        if request:
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ApplicationStatusSerializer(serializers.ModelSerializer):
    """Serializer for checking application status"""
    
    class Meta:
        model = PartnerApplication
        fields = [
            'application_id', 'status', 'partner_type', 'contact_name',
            'created_at', 'updated_at', 'reviewed_at', 'reviewer_notes'
        ]
        read_only_fields = ['__all__']






