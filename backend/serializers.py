# backend/serializers.py
from rest_framework import serializers
from django.core.validators import EmailValidator, URLValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from .models import (
    User, ContactMessage, ContactResponse, PartnerApplication, 
    PartnerDocument, ContactAnalytics, PartnerAnalytics
)
import re
import magic

class ContactMessageSerializer(serializers.ModelSerializer):
    """Serializer for contact message submission"""
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'company', 'website',
            'subject', 'message', 'preferred_contact_method',
            'status', 'priority', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'priority', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate name field"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(_("Le nom doit contenir au moins 2 caractères."))
        if len(value) > 100:
            raise serializers.ValidationError(_("Le nom ne peut pas dépasser 100 caractères."))
        return value.strip()
    
    def validate_email(self, value):
        """Validate email field"""
        if not value:
            raise serializers.ValidationError(_("L'adresse email est requise."))
        
        # Use Django's email validator
        try:
            EmailValidator()(value)
        except:
            raise serializers.ValidationError(_("Veuillez entrer une adresse email valide."))
        
        return value.lower().strip()
    
    def validate_phone(self, value):
        """Validate phone number (Cameroon format)"""
        if value:
            # Remove spaces and special characters
            cleaned_phone = re.sub(r'[\s\-\(\)]', '', value)
            
            # Cameroon phone number pattern
            phone_pattern = r'^(\+237|237)?[2368]\d{8}$'
            
            if not re.match(phone_pattern, cleaned_phone):
                raise serializers.ValidationError(
                    _("Veuillez entrer un numéro de téléphone camerounais valide (ex: +237 6XX XXX XXX).")
                )
            
            return cleaned_phone
        return value
    
    def validate_website(self, value):
        """Validate website URL"""
        if value:
            try:
                URLValidator()(value)
            except:
                raise serializers.ValidationError(_("Veuillez entrer une URL valide (ex: https://exemple.com)."))
            
            # Ensure URL has protocol
            if not value.startswith(('http://', 'https://')):
                value = 'https://' + value
                
        return value
    
    def validate_message(self, value):
        """Validate message content"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(_("Le message doit contenir au moins 10 caractères."))
        if len(value) > 5000:
            raise serializers.ValidationError(_("Le message ne peut pas dépasser 5000 caractères."))
        
        # Check for spam-like content
        spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'congratulations']
        if any(keyword in value.lower() for keyword in spam_keywords):
            raise serializers.ValidationError(_("Votre message contient du contenu suspect."))
        
        return value.strip()
    
    def create(self, validated_data):
        """Create contact message with request metadata"""
        request = self.context.get('request')
        
        if request:
            # Add IP address and user agent
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                validated_data['ip_address'] = x_forwarded_for.split(',')[0]
            else:
                validated_data['ip_address'] = request.META.get('REMOTE_ADDR')
            
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            
            # Extract UTM parameters from query params
            validated_data['utm_source'] = request.query_params.get('utm_source')
            validated_data['utm_medium'] = request.query_params.get('utm_medium')
            validated_data['utm_campaign'] = request.query_params.get('utm_campaign')
        
        return super().create(validated_data)

class ContactResponseSerializer(serializers.ModelSerializer):
    """Serializer for contact responses"""
    
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    
    class Meta:
        model = ContactResponse
        fields = [
            'id', 'response_text', 'is_public', 'responder_name', 'created_at'
        ]
        read_only_fields = ['id', 'responder_name', 'created_at']

class ContactMessageDetailSerializer(ContactMessageSerializer):
    """Detailed serializer for contact message with responses"""
    
    responses = ContactResponseSerializer(many=True, read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta(ContactMessageSerializer.Meta):
        fields = ContactMessageSerializer.Meta.fields + [
            'responses', 'assigned_to_name', 'status_display', 
            'subject_display', 'priority_display', 'utm_source', 
            'utm_medium', 'utm_campaign', 'resolved_at'
        ]

class PartnerDocumentSerializer(serializers.ModelSerializer):
    """Serializer for partner documents"""
    
    class Meta:
        model = PartnerDocument
        fields = [
            'id', 'document_type', 'file', 'original_filename',
            'file_size', 'mime_type', 'uploaded_at'
        ]
        read_only_fields = ['id', 'original_filename', 'file_size', 'mime_type', 'uploaded_at']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            return value
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                _("La taille du fichier ne peut pas dépasser 10 MB.")
            )
        
        # Check file type
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/jpg', 
            'image/png',
        ]
        
        # Get MIME type
        if isinstance(value, (InMemoryUploadedFile, TemporaryUploadedFile)):
            try:
                mime_type = magic.from_buffer(value.read(1024), mime=True)
                value.seek(0)  # Reset file pointer
            except:
                mime_type = value.content_type
        else:
            mime_type = value.content_type
        
        if mime_type not in allowed_types:
            raise serializers.ValidationError(
                _("Type de fichier non supporté. Utilisez PDF, DOC, DOCX, JPG ou PNG.")
            )
        
        return value

class PartnerApplicationSerializer(serializers.ModelSerializer):
    """Serializer for partner application submission"""
    
    documents = PartnerDocumentSerializer(many=True, read_only=True)
    
    # File uploads (handled separately)
    id_document = serializers.FileField(write_only=True, required=True)
    health_certificate = serializers.FileField(write_only=True, required=False)
    menu = serializers.FileField(write_only=True, required=False)
    driving_license_doc = serializers.FileField(write_only=True, required=False)
    vehicle_registration = serializers.FileField(write_only=True, required=False)
    business_plan = serializers.FileField(write_only=True, required=False)
    financial_statements = serializers.FileField(write_only=True, required=False)
    photos = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        max_length=5
    )
    
    class Meta:
        model = PartnerApplication
        fields = [
            'id', 'partner_type', 'status', 'contact_name', 'email', 'phone',
            'business_name', 'cuisine_type', 'capacity', 'opening_hours',
            'address', 'city', 'legal_status', 'tax_id', 'vehicle_type',
            'driving_license', 'investment_amount', 'investment_type',
            'business_experience', 'service_type', 'created_at', 'updated_at',
            'documents', 'id_document', 'health_certificate', 'menu',
            'driving_license_doc', 'vehicle_registration', 'business_plan',
            'financial_statements', 'photos'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'documents']
    
    def validate_contact_name(self, value):
        """Validate contact name"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(_("Le nom du contact doit contenir au moins 2 caractères."))
        return value.strip()
    
    def validate_email(self, value):
        """Validate email"""
        if not value:
            raise serializers.ValidationError(_("L'adresse email est requise."))
        
        try:
            EmailValidator()(value)
        except:
            raise serializers.ValidationError(_("Veuillez entrer une adresse email valide."))
        
        return value.lower().strip()
    
    def validate_phone(self, value):
        """Validate phone number"""
        if not value:
            raise serializers.ValidationError(_("Le numéro de téléphone est requis."))
        
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', value)
        phone_pattern = r'^(\+237|237)?[2368]\d{8}$'
        
        if not re.match(phone_pattern, cleaned_phone):
            raise serializers.ValidationError(
                _("Veuillez entrer un numéro de téléphone camerounais valide.")
            )
        
        return cleaned_phone
    
    def validate(self, data):
        """Cross-field validation based on partner type"""
        partner_type = data.get('partner_type')
        
        if partner_type == 'restaurant':
            required_fields = ['business_name', 'cuisine_type', 'address', 'city']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: _("Ce champ est requis pour les restaurants.")
                    })
        
        elif partner_type == 'delivery-agent':
            required_fields = ['vehicle_type', 'address', 'city']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: _("Ce champ est requis pour les agents de livraison.")
                    })
        
        elif partner_type == 'investor':
            required_fields = ['investment_amount', 'investment_type']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({
                        field: _("Ce champ est requis pour les investisseurs.")
                    })
            
            # Validate investment amount
            if data.get('investment_amount') and data['investment_amount'] <= 0:
                raise serializers.ValidationError({
                    'investment_amount': _("Le montant d'investissement doit être supérieur à 0.")
                })
        
        return data
    
    def create(self, validated_data):
        """Create partner application with documents"""
        # Extract file data
        files_data = {}
        file_fields = [
            'id_document', 'health_certificate', 'menu', 'driving_license_doc',
            'vehicle_registration', 'business_plan', 'financial_statements', 'photos'
        ]
        
        for field in file_fields:
            if field in validated_data:
                files_data[field] = validated_data.pop(field)
        
        # Create application
        application = super().create(validated_data)
        
        # Process and save documents
        self._create_documents(application, files_data)
        
        return application
    
    def _create_documents(self, application, files_data):
        """Create document instances for the application"""
        import magic
        
        # Document type mapping
        doc_type_mapping = {
            'id_document': 'id_document',
            'health_certificate': 'health_certificate',
            'menu': 'menu',
            'driving_license_doc': 'driving_license',
            'vehicle_registration': 'vehicle_registration',
            'business_plan': 'business_plan',
            'financial_statements': 'financial_statements',
        }
        
        for field_name, file_data in files_data.items():
            if field_name == 'photos' and file_data:
                # Handle multiple photo uploads
                for photo in file_data:
                    self._create_single_document(application, 'photo', photo)
            elif file_data and field_name in doc_type_mapping:
                # Handle single file uploads
                doc_type = doc_type_mapping[field_name]
                self._create_single_document(application, doc_type, file_data)
    
    def _create_single_document(self, application, doc_type, file_data):
        """Create a single document instance"""
        try:
            # Get MIME type
            mime_type = magic.from_buffer(file_data.read(1024), mime=True)
            file_data.seek(0)  # Reset file pointer
        except:
            mime_type = getattr(file_data, 'content_type', 'application/octet-stream')
        
        PartnerDocument.objects.create(
            application=application,
            document_type=doc_type,
            file=file_data,
            original_filename=file_data.name,
            file_size=file_data.size,
            mime_type=mime_type
        )

class PartnerApplicationDetailSerializer(PartnerApplicationSerializer):
    """Detailed serializer for partner application with all relations"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    partner_type_display = serializers.CharField(source='get_partner_type_display', read_only=True)
    legal_status_display = serializers.CharField(source='get_legal_status_display', read_only=True)
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)
    investment_type_display = serializers.CharField(source='get_investment_type_display', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    
    class Meta(PartnerApplicationSerializer.Meta):
        fields = PartnerApplicationSerializer.Meta.fields + [
            'status_display', 'partner_type_display', 'legal_status_display',
            'vehicle_type_display', 'investment_type_display', 'service_type_display',
            'reviewer_name', 'review_notes', 'rejection_reason', 'reviewed_at', 'approved_at'
        ]
        read_only_fields = PartnerApplicationSerializer.Meta.read_only_fields + [
            'status_display', 'partner_type_display', 'legal_status_display',
            'vehicle_type_display', 'investment_type_display', 'service_type_display',
            'reviewer_name', 'review_notes', 'rejection_reason', 'reviewed_at', 'approved_at'
        ]

class PartnerApplicationStatusSerializer(serializers.ModelSerializer):
    """Serializer for checking application status"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    partner_type_display = serializers.CharField(source='get_partner_type_display', read_only=True)
    
    class Meta:
        model = PartnerApplication
        fields = [
            'id', 'status', 'status_display', 'partner_type', 'partner_type_display',
            'contact_name', 'email', 'created_at', 'updated_at', 'reviewed_at'
        ]
        read_only_fields = '__all__'

class PartnerApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating application status (admin only)"""
    
    class Meta:
        model = PartnerApplication
        fields = ['status', 'review_notes', 'rejection_reason']
    
    def validate(self, data):
        """Validate status update"""
        status = data.get('status')
        
        if status == 'rejected' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': _("La raison du rejet est requise.")
            })
        
        return data
    
    def update(self, instance, validated_data):
        """Update application with tracking"""
        status = validated_data.get('status')
        
        if status and status != instance.status:
            validated_data['reviewed_at'] = timezone.now()
            
            if status == 'approved':
                validated_data['approved_at'] = timezone.now()
            
            # Set reviewer
            request = self.context.get('request')
            if request and request.user:
                validated_data['reviewer'] = request.user
        
        return super().update(instance, validated_data)

# Analytics Serializers
class ContactAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for contact analytics"""
    
    class Meta:
        model = ContactAnalytics
        fields = '__all__'

class PartnerAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for partner analytics"""
    
    class Meta:
        model = PartnerAnalytics
        fields = '__all__'

# Utility Serializers
class ContactFormConfigSerializer(serializers.Serializer):
    """Serializer for contact form configuration"""
    
    subjects = serializers.ListField(child=serializers.DictField())
    contact_methods = serializers.ListField(child=serializers.DictField())
    max_message_length = serializers.IntegerField()
    required_fields = serializers.ListField(child=serializers.CharField())

class PartnerFormConfigSerializer(serializers.Serializer):
    """Serializer for partner form configuration"""
    
    partner_types = serializers.ListField(child=serializers.DictField())
    legal_statuses = serializers.ListField(child=serializers.DictField())
    vehicle_types = serializers.ListField(child=serializers.DictField())
    investment_types = serializers.ListField(child=serializers.DictField())
    service_types = serializers.ListField(child=serializers.DictField())
    max_file_size = serializers.IntegerField()
    allowed_file_types = serializers.ListField(child=serializers.CharField())
    max_photos = serializers.IntegerField()

class ServiceHealthSerializer(serializers.Serializer):
    """Serializer for service health check"""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    database_status = serializers.CharField()
    email_service_status = serializers.CharField()
    file_storage_status = serializers.CharField()

# Bulk operations serializers
class BulkContactUpdateSerializer(serializers.Serializer):
    """Serializer for bulk contact message updates"""
    
    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=['mark_resolved', 'assign', 'set_priority'])
    assigned_to = serializers.UUIDField(required=False)
    priority = serializers.ChoiceField(
        choices=ContactMessage.PRIORITY_CHOICES,
        required=False
    )

class BulkPartnerUpdateSerializer(serializers.Serializer):
    """Serializer for bulk partner application updates"""
    
    application_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50
    )
    action = serializers.ChoiceField(choices=['approve', 'reject', 'review'])
    rejection_reason = serializers.CharField(required=False, max_length=1000)
    review_notes = serializers.CharField(required=False, max_length=1000)


