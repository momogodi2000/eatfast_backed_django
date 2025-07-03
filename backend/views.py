# backend/views.py
from rest_framework import generics, status, permissions, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.db.models import Q, Count, Avg, F
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
import logging
from datetime import datetime, timedelta
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    ContactMessage, ContactResponse, PartnerApplication, 
    PartnerDocument, ContactAnalytics, PartnerAnalytics
)
from .serializers import (
    ContactMessageSerializer, ContactMessageDetailSerializer,
    ContactResponseSerializer, PartnerApplicationSerializer,
    PartnerApplicationDetailSerializer, PartnerApplicationStatusSerializer,
    PartnerApplicationUpdateSerializer, PartnerDocumentSerializer,
    ContactAnalyticsSerializer, PartnerAnalyticsSerializer,
    ContactFormConfigSerializer, PartnerFormConfigSerializer,
    ServiceHealthSerializer, BulkContactUpdateSerializer,
    BulkPartnerUpdateSerializer
)
from .permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from .filters import ContactMessageFilter, PartnerApplicationFilter
from .utils import (
    send_contact_confirmation_email, send_partner_application_email,
    generate_contact_analytics, generate_partner_analytics,
    check_rate_limit, get_client_ip
)

logger = logging.getLogger(__name__)

# Pagination Classes
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200

# Basic API Views
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_root(request):
    """API root endpoint for Eat Fast backend"""
    return Response({
        'message': 'Welcome to Eat Fast API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/v1/health/',
            'contact': '/api/v1/contact/',
            'partner': '/api/v1/partner/',
            'admin': '/admin/',
        },
        'timestamp': timezone.now().isoformat()
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint with service status"""
    try:
        # Check database
        db_status = 'healthy'
        try:
            ContactMessage.objects.first()
        except Exception as e:
            db_status = f'unhealthy: {str(e)}'
        
        # Check email service
        email_status = 'healthy' if settings.EMAIL_HOST else 'not_configured'
        
        # Check file storage
        storage_status = 'healthy'
        
        health_data = {
            'success': True,
            'message': 'Service is healthy',
            'timestamp': timezone.now(),
            'database_status': db_status,
            'email_service_status': email_status,
            'file_storage_status': storage_status
        }
        
        return Response(health_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return Response({
            'success': False,
            'message': 'Service is unhealthy',
            'timestamp': timezone.now(),
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# Contact Views
class ContactMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for handling contact messages"""
    
    queryset = ContactMessage.objects.all()
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ContactMessageFilter
    search_fields = ['name', 'email', 'company', 'message']
    ordering_fields = ['created_at', 'status', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return ContactMessageDetailSerializer
        return ContactMessageSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """Create contact message with rate limiting and validation"""
        client_ip = get_client_ip(request)
        
        # Check rate limiting (max 5 messages per hour per IP)
        if not check_rate_limit(client_ip, 'contact_form', max_requests=5, window_hours=1):
            return Response({
                'success': False,
                'message': 'Trop de messages envoyés. Veuillez réessayer plus tard.',
                'errors': ['rate_limit_exceeded']
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            if serializer.is_valid():
                # Save contact message
                contact_message = serializer.save()
                
                # Send confirmation email
                try:
                    send_contact_confirmation_email(contact_message)
                except Exception as e:
                    logger.error(f"Failed to send confirmation email: {str(e)}")
                
                # Log successful submission
                logger.info(f"Contact message created: {contact_message.id} from {contact_message.email}")
                
                return Response({
                    'success': True,
                    'message': 'Votre message a été envoyé avec succès! Nous vous répondrons sous 24-48 heures.',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            else:
                # Return validation errors in French
                errors = []
                for field, messages in serializer.errors.items():
                    if isinstance(messages, list):
                        errors.extend(messages)
                    else:
                        errors.append(str(messages))
                
                return Response({
                    'success': False,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.',
                    'errors': errors,
                    'field_errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Contact form submission error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Une erreur est survenue lors de l\'envoi de votre message. Veuillez réessayer.',
                'errors': ['server_error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_response(self, request, pk=None):
        """Add response to contact message"""
        contact_message = self.get_object()
        
        serializer = ContactResponseSerializer(data=request.data)
        if serializer.is_valid():
            response = serializer.save(
                contact_message=contact_message,
                responder=request.user
            )
            
            # Update contact message status if needed
            if contact_message.status == 'new':
                contact_message.status = 'in_progress'
                contact_message.save(update_fields=['status'])
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_resolved(self, request, pk=None):
        """Mark contact message as resolved"""
        contact_message = self.get_object()
        contact_message.mark_resolved()
        
        return Response({
            'success': True,
            'message': 'Message marqué comme résolu.'
        })
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bulk_update(self, request):
        """Bulk update contact messages"""
        serializer = BulkContactUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            message_ids = serializer.validated_data['message_ids']
            action_type = serializer.validated_data['action']
            
            messages = ContactMessage.objects.filter(id__in=message_ids)
            
            if action_type == 'mark_resolved':
                messages.update(status='resolved', resolved_at=timezone.now())
            elif action_type == 'assign':
                assigned_to = serializer.validated_data.get('assigned_to')
                messages.update(assigned_to_id=assigned_to)
            elif action_type == 'set_priority':
                priority = serializer.validated_data.get('priority')
                messages.update(priority=priority)
            
            return Response({
                'success': True,
                'message': f'{messages.count()} messages mis à jour.'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Partner Application Views
class PartnerApplicationViewSet(viewsets.ModelViewSet):
    """ViewSet for handling partner applications"""
    
    queryset = PartnerApplication.objects.all()
    pagination_class = StandardResultsSetPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PartnerApplicationFilter
    search_fields = ['contact_name', 'email', 'business_name', 'city']
    ordering_fields = ['created_at', 'status', 'partner_type']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return PartnerApplicationDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return PartnerApplicationUpdateSerializer
        return PartnerApplicationSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action == 'check_status':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
        
        return [permission() for permission in permission_classes]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create partner application with file uploads"""
        client_ip = get_client_ip(request)
        
        # Check rate limiting (max 3 applications per day per IP)
        if not check_rate_limit(client_ip, 'partner_application', max_requests=3, window_hours=24):
            return Response({
                'success': False,
                'message': 'Limite d\'applications quotidienne atteinte. Veuillez réessayer demain.',
                'errors': ['rate_limit_exceeded']
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            if serializer.is_valid():
                # Save application
                application = serializer.save()
                
                # Send confirmation email
                try:
                    send_partner_application_email(application)
                except Exception as e:
                    logger.error(f"Failed to send partner application email: {str(e)}")
                
                # Log successful submission
                logger.info(f"Partner application created: {application.id} from {application.email}")
                
                return Response({
                    'success': True,
                    'message': 'Votre candidature a été soumise avec succès! Nous l\'examinerons sous 3-5 jours ouvrables.',
                    'data': {
                        'id': str(application.id),
                        'status': application.status,
                        'created_at': application.created_at.isoformat()
                    }
                }, status=status.HTTP_201_CREATED)
            
            else:
                # Return validation errors
                errors = []
                for field, messages in serializer.errors.items():
                    if isinstance(messages, list):
                        errors.extend(messages)
                    else:
                        errors.append(str(messages))
                
                return Response({
                    'success': False,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.',
                    'errors': errors,
                    'field_errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Partner application submission error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Une erreur est survenue lors de la soumission. Veuillez réessayer.',
                'errors': ['server_error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def check_status(self, request):
        """Check application status"""
        application_id = request.data.get('application_id')
        email = request.data.get('email')
        
        if not application_id or not email:
            return Response({
                'success': False,
                'message': 'ID de candidature et email requis.',
                'errors': ['missing_required_fields']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            application = PartnerApplication.objects.get(
                id=application_id,
                email__iexact=email
            )
            
            serializer = PartnerApplicationStatusSerializer(application)
            
            return Response({
                'success': True,
                'message': 'Statut récupéré avec succès.',
                'data': serializer.data
            })
            
        except PartnerApplication.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Candidature non trouvée. Vérifiez l\'ID et l\'email.',
                'errors': ['application_not_found']
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Erreur lors de la vérification du statut.',
                'errors': ['server_error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve partner application"""
        application = self.get_object()
        
        if application.status != 'pending':
            return Response({
                'success': False,
                'message': 'Seules les candidatures en attente peuvent être approuvées.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        application.approve(request.user)
        
        # Send approval email
        try:
            send_partner_approval_email(application)
        except Exception as e:
            logger.error(f"Failed to send approval email: {str(e)}")
        
        return Response({
            'success': True,
            'message': 'Candidature approuvée avec succès.'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject partner application"""
        application = self.get_object()
        reason = request.data.get('reason')
        
        if not reason:
            return Response({
                'success': False,
                'message': 'Raison du rejet requise.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        application.reject(request.user, reason)
        
        # Send rejection email
        try:
            send_partner_rejection_email(application)
        except Exception as e:
            logger.error(f"Failed to send rejection email: {str(e)}")
        
        return Response({
            'success': True,
            'message': 'Candidature rejetée.'
        })
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bulk_update(self, request):
        """Bulk update partner applications"""
        serializer = BulkPartnerUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            application_ids = serializer.validated_data['application_ids']
            action_type = serializer.validated_data['action']
            
            applications = PartnerApplication.objects.filter(id__in=application_ids)
            
            if action_type == 'approve':
                for app in applications:
                    app.approve(request.user)
            elif action_type == 'reject':
                reason = serializer.validated_data.get('rejection_reason')
                for app in applications:
                    app.reject(request.user, reason)
            elif action_type == 'review':
                applications.update(
                    status='under_review',
                    reviewer=request.user,
                    reviewed_at=timezone.now()
                )
            
            return Response({
                'success': True,
                'message': f'{applications.count()} candidatures mises à jour.'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Configuration Views
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
def contact_form_config(request):
    """Get contact form configuration"""
    config = {
        'subjects': [
            {'value': choice[0], 'label': choice[1]}
            for choice in ContactMessage.SUBJECT_CHOICES
        ],
        'contact_methods': [
            {'value': choice[0], 'label': choice[1]}
            for choice in ContactMessage.CONTACT_METHOD_CHOICES
        ],
        'max_message_length': 5000,
        'required_fields': ['name', 'email', 'message']
    }
    
    serializer = ContactFormConfigSerializer(config)
    return Response({
        'success': True,
        'data': serializer.data
    })

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@method_decorator(cache_page(60 * 15), name='dispatch')  # Cache for 15 minutes
def partner_form_config(request):
    """Get partner form configuration"""
    config = {
        'partner_types': [
            {'value': choice[0], 'label': choice[1]}
            for choice in PartnerApplication.PARTNER_TYPE_CHOICES
        ],
        'legal_statuses': [
            {'value': choice[0], 'label': choice[1]}
            for choice in PartnerApplication.LEGAL_STATUS_CHOICES
        ],
        'vehicle_types': [
            {'value': choice[0], 'label': choice[1]}
            for choice in PartnerApplication.VEHICLE_TYPE_CHOICES
        ],
        'investment_types': [
            {'value': choice[0], 'label': choice[1]}
            for choice in PartnerApplication.INVESTMENT_TYPE_CHOICES
        ],
        'service_types': [
            {'value': choice[0], 'label': choice[1]}
            for choice in PartnerApplication.SERVICE_TYPE_CHOICES
        ],
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'allowed_file_types': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png'
        ],
        'max_photos': 5
    }
    
    serializer = PartnerFormConfigSerializer(config)
    return Response({
        'success': True,
        'data': serializer.data
    })

# Analytics Views
class ContactAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for contact analytics"""
    
    queryset = ContactAnalytics.objects.all()
    serializer_class = ContactAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = LargeResultsSetPagination
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get contact dashboard analytics"""
        try:
            # Generate current analytics
            today = timezone.now().date()
            generate_contact_analytics(today)
            
            # Get recent analytics
            recent_analytics = ContactAnalytics.objects.filter(
                date__gte=today - timedelta(days=30)
            ).order_by('-date')
            
            # Get summary stats
            total_messages = ContactMessage.objects.count()
            pending_messages = ContactMessage.objects.filter(
                status__in=['new', 'in_progress']
            ).count()
            
            avg_response_time = ContactMessage.objects.filter(
                resolved_at__isnull=False
            ).aggregate(
                avg_time=Avg(
                    F('resolved_at') - F('created_at')
                )
            )['avg_time']
            
            # Messages by subject
            messages_by_subject = ContactMessage.objects.values(
                'subject'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            response_data = {
                'summary': {
                    'total_messages': total_messages,
                    'pending_messages': pending_messages,
                    'avg_response_time_hours': (
                        avg_response_time.total_seconds() / 3600 
                        if avg_response_time else 0
                    ),
                    'messages_today': ContactMessage.objects.filter(
                        created_at__date=today
                    ).count()
                },
                'recent_analytics': ContactAnalyticsSerializer(
                    recent_analytics, many=True
                ).data,
                'messages_by_subject': messages_by_subject
            }
            
            return Response({
                'success': True,
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"Contact analytics error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Erreur lors de la récupération des analyses.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PartnerAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for partner analytics"""
    
    queryset = PartnerAnalytics.objects.all()
    serializer_class = PartnerAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    pagination_class = LargeResultsSetPagination
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get partner dashboard analytics"""
        try:
            # Generate current analytics
            today = timezone.now().date()
            generate_partner_analytics(today)
            
            # Get recent analytics
            recent_analytics = PartnerAnalytics.objects.filter(
                date__gte=today - timedelta(days=30)
            ).order_by('-date')
            
            # Get summary stats
            total_applications = PartnerApplication.objects.count()
            pending_applications = PartnerApplication.objects.filter(
                status='pending'
            ).count()
            approved_applications = PartnerApplication.objects.filter(
                status='approved'
            ).count()
            
            # Applications by type
            apps_by_type = PartnerApplication.objects.values(
                'partner_type'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Applications by status
            apps_by_status = PartnerApplication.objects.values(
                'status'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Monthly trend
            monthly_trend = PartnerApplication.objects.filter(
                created_at__gte=today - timedelta(days=90)
            ).extra(
                select={'month': "date_trunc('month', created_at)"}
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            response_data = {
                'summary': {
                    'total_applications': total_applications,
                    'pending_applications': pending_applications,
                    'approved_applications': approved_applications,
                    'approval_rate': (
                        (approved_applications / total_applications * 100)
                        if total_applications > 0 else 0
                    ),
                    'applications_today': PartnerApplication.objects.filter(
                        created_at__date=today
                    ).count()
                },
                'recent_analytics': PartnerAnalyticsSerializer(
                    recent_analytics, many=True
                ).data,
                'applications_by_type': apps_by_type,
                'applications_by_status': apps_by_status,
                'monthly_trend': monthly_trend
            }
            
            return Response({
                'success': True,
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"Partner analytics error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Erreur lors de la récupération des analyses.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Document Views
class PartnerDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for partner documents"""
    
    queryset = PartnerDocument.objects.all()
    serializer_class = PartnerDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get_queryset(self):
        """Filter documents by application"""
        queryset = super().get_queryset()
        application_id = self.request.query_params.get('application_id')
        
        if application_id:
            queryset = queryset.filter(application_id=application_id)
        
        return queryset

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download(self, request, pk=None):
        """Download the partner document file as an attachment"""
        document = self.get_object()
        if not document.file:
            raise Http404("File not found.")
        response = FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_filename)
        response['Content-Length'] = document.file.size
        response['Content-Type'] = document.mime_type or 'application/octet-stream'
        return response

# Export Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_contact_messages(request):
    """Export contact messages to CSV"""
    try:
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contact_messages.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nom', 'Email', 'Téléphone', 'Entreprise', 'Sujet',
            'Statut', 'Priorité', 'Créé le', 'Résolu le'
        ])
        
        # Apply filters
        queryset = ContactMessage.objects.all()
        
        # Date range filter
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Status filter
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        for message in queryset.order_by('-created_at'):
            writer.writerow([
                str(message.id),
                message.name,
                message.email,
                message.phone or '',
                message.company or '',
                message.get_subject_display(),
                message.get_status_display(),
                message.get_priority_display(),
                message.created_at.strftime('%Y-%m-%d %H:%M'),
                message.resolved_at.strftime('%Y-%m-%d %H:%M') if message.resolved_at else ''
            ])
        
        return response
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erreur lors de l\'export.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def export_partner_applications(request):
    """Export partner applications to CSV"""
    try:
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="partner_applications.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Type de partenaire', 'Nom du contact', 'Email', 'Téléphone',
            'Entreprise', 'Ville', 'Statut', 'Créé le', 'Examiné le'
        ])
        
        # Apply filters
        queryset = PartnerApplication.objects.all()
        
        # Date range filter
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Partner type filter
        partner_type = request.GET.get('partner_type')
        if partner_type:
            queryset = queryset.filter(partner_type=partner_type)
        
        # Status filter
        status_filter = request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        for application in queryset.order_by('-created_at'):
            writer.writerow([
                str(application.id),
                application.get_partner_type_display(),
                application.contact_name,
                application.email,
                application.phone,
                application.business_name or '',
                application.city or '',
                application.get_status_display(),
                application.created_at.strftime('%Y-%m-%d %H:%M'),
                application.reviewed_at.strftime('%Y-%m-%d %H:%M') if application.reviewed_at else ''
            ])
        
        return response
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erreur lors de l\'export.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Search Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def global_search(request):
    """Global search across contacts and partners"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 3:
        return Response({
            'success': False,
            'message': 'La recherche doit contenir au moins 3 caractères.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Search contacts
    contact_results = ContactMessage.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(company__icontains=query) |
        Q(message__icontains=query)
    )[:10]
    
    # Search partners
    partner_results = PartnerApplication.objects.filter(
        Q(contact_name__icontains=query) |
        Q(email__icontains=query) |
        Q(business_name__icontains=query) |
        Q(city__icontains=query)
    )[:10]
    
    response_data = {
        'contacts': ContactMessageSerializer(contact_results, many=True).data,
        'partners': PartnerApplicationSerializer(partner_results, many=True).data,
        'total_results': contact_results.count() + partner_results.count()
    }
    
    return Response({
        'success': True,
        'data': response_data
    })

# Statistics Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache for 5 minutes
def dashboard_stats(request):
    """Get overall dashboard statistics"""
    try:
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Contact stats
        contact_stats = {
            'total': ContactMessage.objects.count(),
            'today': ContactMessage.objects.filter(created_at__date=today).count(),
            'week': ContactMessage.objects.filter(created_at__date__gte=week_ago).count(),
            'month': ContactMessage.objects.filter(created_at__date__gte=month_ago).count(),
            'pending': ContactMessage.objects.filter(status__in=['new', 'in_progress']).count(),
            'resolved': ContactMessage.objects.filter(status='resolved').count()
        }
        
        # Partner stats
        partner_stats = {
            'total': PartnerApplication.objects.count(),
            'today': PartnerApplication.objects.filter(created_at__date=today).count(),
            'week': PartnerApplication.objects.filter(created_at__date__gte=week_ago).count(),
            'month': PartnerApplication.objects.filter(created_at__date__gte=month_ago).count(),
            'pending': PartnerApplication.objects.filter(status='pending').count(),
            'approved': PartnerApplication.objects.filter(status='approved').count(),
            'restaurants': PartnerApplication.objects.filter(partner_type='restaurant').count(),
            'delivery_agents': PartnerApplication.objects.filter(partner_type='delivery-agent').count(),
            'investors': PartnerApplication.objects.filter(partner_type='investor').count()
        }
        
        # Recent activity
        recent_contacts = ContactMessage.objects.filter(
            created_at__gte=week_ago
        ).order_by('-created_at')[:5]
        
        recent_partners = PartnerApplication.objects.filter(
            created_at__gte=week_ago
        ).order_by('-created_at')[:5]
        
        response_data = {
            'contact_stats': contact_stats,
            'partner_stats': partner_stats,
            'recent_activity': {
                'contacts': ContactMessageSerializer(recent_contacts, many=True).data,
                'partners': PartnerApplicationSerializer(recent_partners, many=True).data
            },
            'system_health': {
                'database': 'healthy',
                'email_service': 'healthy' if settings.EMAIL_HOST else 'not_configured',
                'file_storage': 'healthy'
            }
        }
        
        return Response({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return Response({
            'success': False,
            'message': 'Erreur lors de la récupération des statistiques.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
