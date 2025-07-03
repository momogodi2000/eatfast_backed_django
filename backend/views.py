# backend/views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import os
import uuid
import logging
from .models import ContactInquiry, PartnerApplication, PartnerDocument, NewsletterSubscription
from .serializers import (
    ContactInquirySerializer, PartnerApplicationSerializer, 
    NewsletterSubscriptionSerializer, ApplicationStatusSerializer
)
from .services.email_service import EmailService

logger = logging.getLogger(__name__)

# Initialize email service
email_service = EmailService()

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root endpoint for Eat Fast backend"""
    return Response({
        'message': 'Welcome to Eat Fast API',
        'version': '1.0.0',
        'service': 'eatfast-backend',
        'endpoints': {
            'health': '/api/health/',
            'contact': '/api/contact/',
            'partner-application': '/api/partner-application/',
            'partner-status': '/api/partner-status/',
            'newsletter': '/api/newsletter/',
            'admin': '/admin/',
        },
        'timestamp': timezone.now().isoformat()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'eatfast-backend',
        'timestamp': timezone.now().isoformat(),
        'database': 'connected',
        'email_service': 'active'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def submit_contact_inquiry(request):
    """Submit contact form inquiry"""
    try:
        serializer = ContactInquirySerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            with transaction.atomic():
                # Save the contact inquiry
                contact_inquiry = serializer.save()
                
                # Send confirmation email to user
                try:
                    email_service.send_contact_confirmation(contact_inquiry)
                except Exception as e:
                    logger.error(f"Failed to send contact confirmation email: {str(e)}")
                
                # Send notification email to admin
                try:
                    email_service.send_contact_notification(contact_inquiry)
                except Exception as e:
                    logger.error(f"Failed to send contact notification email: {str(e)}")
            
            return Response({
                'success': True,
                'message': 'Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais.',
                'data': {
                    'id': contact_inquiry.id,
                    'created_at': contact_inquiry.created_at
                }
            }, status=status.HTTP_201_CREATED)
        
        else:
            return Response({
                'success': False,
                'message': 'Veuillez corriger les erreurs dans le formulaire.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Contact form submission error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Une erreur inattendue s\'est produite. Veuillez réessayer.',
            'error': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def submit_partner_application(request):
    """Submit partner application with file uploads"""
    try:
        # Extract form data and files
        form_data = request.data.copy()
        files = request.FILES
        
        # Validate main application data
        serializer = PartnerApplicationSerializer(data=form_data, context={'request': request})
        
        if serializer.is_valid():
            with transaction.atomic():
                # Save partner application
                application = serializer.save()
                
                # Process file uploads
                uploaded_files = []
                file_errors = []
                
                for field_name, uploaded_file in files.items():
                    try:
                        if uploaded_file:
                            # Validate file
                            if not validate_uploaded_file(uploaded_file):
                                file_errors.append(f"Fichier {field_name} invalide")
                                continue
                            
                            # Save file and create document record
                            document = save_partner_document(application, field_name, uploaded_file)
                            uploaded_files.append({
                                'field': field_name,
                                'filename': document.file_name,
                                'size': document.file_size
                            })
                    
                    except Exception as e:
                        logger.error(f"File upload error for {field_name}: {str(e)}")
                        file_errors.append(f"Erreur lors du téléchargement de {field_name}")
                
                # Send confirmation emails
                try:
                    email_service.send_partner_application_confirmation(application)
                except Exception as e:
                    logger.error(f"Failed to send partner confirmation email: {str(e)}")
                
                try:
                    email_service.send_partner_application_notification(application)
                except Exception as e:
                    logger.error(f"Failed to send partner notification email: {str(e)}")
                
                response_data = {
                    'success': True,
                    'message': 'Votre candidature a été soumise avec succès!',
                    'data': {
                        'id': str(application.application_id),
                        'email': application.email,
                        'created_at': application.created_at,
                        'uploaded_files': uploaded_files
                    }
                }
                
                if file_errors:
                    response_data['file_warnings'] = file_errors
                
                return Response(response_data, status=status.HTTP_201_CREATED)
        
        else:
            return Response({
                'success': False,
                'message': 'Veuillez corriger les erreurs dans le formulaire.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Partner application submission error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Une erreur inattendue s\'est produite. Veuillez réessayer.',
            'error': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def check_application_status(request):
    """Check partner application status"""
    try:
        application_id = request.data.get('application_id')
        email = request.data.get('email')
        
        if not application_id or not email:
            return Response({
                'success': False,
                'message': 'ID de candidature et email requis.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            application = PartnerApplication.objects.get(
                application_id=application_id, 
                email=email.lower().strip()
            )
            
            serializer = ApplicationStatusSerializer(application)
            
            return Response({
                'success': True,
                'message': 'Statut de candidature trouvé.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except PartnerApplication.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Candidature non trouvée. Vérifiez l\'ID et l\'email.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Application status check error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erreur lors de la vérification du statut.',
            'error': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def subscribe_newsletter(request):
    """Subscribe to newsletter"""
    try:
        serializer = NewsletterSubscriptionSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            with transaction.atomic():
                # Check if email was previously unsubscribed and reactivate
                email = serializer.validated_data['email']
                existing_subscription = NewsletterSubscription.objects.filter(email=email).first()
                
                if existing_subscription:
                    if existing_subscription.is_active:
                        return Response({
                            'success': False,
                            'message': 'Cette adresse email est déjà abonnée à notre newsletter.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # Reactivate subscription
                        existing_subscription.is_active = True
                        existing_subscription.subscribed_at = timezone.now()
                        existing_subscription.confirmed_at = timezone.now()
                        existing_subscription.save()
                        subscription = existing_subscription
                else:
                    # Create new subscription
                    subscription = serializer.save()
                    subscription.confirmed_at = timezone.now()
                    subscription.save()
                
                # Send welcome email
                try:
                    email_service.send_newsletter_welcome(subscription)
                except Exception as e:
                    logger.error(f"Failed to send newsletter welcome email: {str(e)}")
            
            return Response({
                'success': True,
                'message': 'Merci pour votre abonnement ! Vous recevrez bientôt nos dernières nouvelles.',
                'data': {
                    'email': subscription.email,
                    'subscribed_at': subscription.subscribed_at
                }
            }, status=status.HTTP_201_CREATED)
        
        else:
            return Response({
                'success': False,
                'message': 'Adresse email invalide.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Newsletter subscription error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Une erreur s\'est produite lors de l\'abonnement.',
            'error': str(e) if settings.DEBUG else 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def service_health(request):
    """Service health check for frontend"""
    try:
        # Test database connection
        ContactInquiry.objects.count()
        
        # Test email service
        email_available = email_service.test_connection()
        
        return Response({
            'success': True,
            'message': 'Service opérationnel',
            'services': {
                'database': 'active',
                'email': 'active' if email_available else 'limited',
                'api': 'active'
            },
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Service health check failed: {str(e)}")
        return Response({
            'success': False,
            'message': 'Service partiellement disponible',
            'error': str(e) if settings.DEBUG else 'Service error'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# Helper functions
def validate_uploaded_file(uploaded_file):
    """Validate uploaded file size and type"""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/jpg',
        'image/png'
    ]
    
    if uploaded_file.size > MAX_FILE_SIZE:
        return False
    
    if uploaded_file.content_type not in ALLOWED_TYPES:
        return False
    
    return True

def save_partner_document(application, document_type, uploaded_file):
    """Save uploaded document and create database record"""
    # Generate unique filename
    file_extension = os.path.splitext(uploaded_file.name)[1]
    unique_filename = f"{application.application_id}_{document_type}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    # Create directory path
    upload_path = f"partner_documents/{application.application_id}/"
    file_path = upload_path + unique_filename
    
    # Save file
    saved_path = default_storage.save(file_path, ContentFile(uploaded_file.read()))
    
    # Create document record
    document = PartnerDocument.objects.create(
        application=application,
        document_type=document_type,
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        file_path=saved_path,
        mime_type=uploaded_file.content_type
    )
    
    return document