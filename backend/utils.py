# backend/utils.py
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Avg, F
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_rate_limit(identifier, action, max_requests=5, window_hours=1):
    """Check if action is within rate limit"""
    cache_key = f"rate_limit:{action}:{identifier}"
    current_requests = cache.get(cache_key, 0)
    
    if current_requests >= max_requests:
        return False
    
    # Increment counter
    cache.set(cache_key, current_requests + 1, window_hours * 3600)
    return True

def send_contact_confirmation_email(contact_message):
    """Send confirmation email to contact form submitter"""
    try:
        subject = 'Confirmation de réception - EatFast'
        
        # Render HTML email
        html_content = render_to_string('emails/contact_confirmation.html', {
            'contact_message': contact_message,
            'support_email': settings.DEFAULT_FROM_EMAIL,
            'company_name': 'EatFast'
        })
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_message.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
        
        logger.info(f"Confirmation email sent to {contact_message.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {str(e)}")
        return False

def send_contact_notification_email(contact_message):
    """Send notification email to admin about new contact"""
    try:
        subject = f'Nouveau message de contact - {contact_message.get_subject_display()}'
        
        html_content = render_to_string('emails/contact_notification.html', {
            'contact_message': contact_message,
            'admin_url': f"{settings.SITE_URL}/admin/backend/contactmessage/{contact_message.id}/"
        })
        
        text_content = strip_tags(html_content)
        
        # Send to admin emails
        admin_emails = [email for name, email in settings.ADMINS]
        
        if admin_emails:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Contact notification sent to admins for message {contact_message.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send contact notification: {str(e)}")
        return False

def send_partner_application_email(application):
    """Send confirmation email for partner application"""
    try:
        subject = 'Candidature reçue - EatFast Partenaires'
        
        html_content = render_to_string('emails/partner_application_confirmation.html', {
            'application': application,
            'partner_type_display': application.get_partner_type_display(),
            'support_email': settings.DEFAULT_FROM_EMAIL,
            'company_name': 'EatFast'
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Partner application confirmation sent to {application.email}")
        
        # Also send notification to admins
        send_partner_notification_email(application)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send partner application email: {str(e)}")
        return False

def send_partner_notification_email(application):
    """Send notification email to admin about new partner application"""
    try:
        subject = f'Nouvelle candidature partenaire - {application.get_partner_type_display()}'
        
        html_content = render_to_string('emails/partner_notification.html', {
            'application': application,
            'admin_url': f"{settings.SITE_URL}/admin/backend/partnerapplication/{application.id}/"
        })
        
        text_content = strip_tags(html_content)
        
        admin_emails = [email for name, email in settings.ADMINS]
        
        if admin_emails:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=admin_emails
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Partner application notification sent to admins for {application.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send partner notification: {str(e)}")
        return False

def send_partner_approval_email(application):
    """Send approval email to partner"""
    try:
        subject = 'Candidature approuvée - Bienvenue chez EatFast!'
        
        html_content = render_to_string('emails/partner_approval.html', {
            'application': application,
            'partner_type_display': application.get_partner_type_display(),
            'next_steps_url': f"{settings.SITE_URL}/partner/onboarding/",
            'support_email': settings.DEFAULT_FROM_EMAIL
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Partner approval email sent to {application.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send partner approval email: {str(e)}")
        return False

def send_partner_rejection_email(application):
    """Send rejection email to partner"""
    try:
        subject = 'Mise à jour de votre candidature - EatFast'
        
        html_content = render_to_string('emails/partner_rejection.html', {
            'application': application,
            'partner_type_display': application.get_partner_type_display(),
            'reapply_url': f"{settings.SITE_URL}/become-partner/",
            'support_email': settings.DEFAULT_FROM_EMAIL
        })
        
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[application.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        logger.info(f"Partner rejection email sent to {application.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send partner rejection email: {str(e)}")
        return False

def generate_contact_analytics(date):
    """Generate contact analytics for a given date"""
    from .models import ContactMessage, ContactAnalytics
    
    try:
        # Get messages for the date
        messages = ContactMessage.objects.filter(created_at__date=date)
        
        # Calculate metrics
        total_messages = messages.count()
        new_messages = messages.filter(status='new').count()
        resolved_messages = ContactMessage.objects.filter(
            resolved_at__date=date
        ).count()
        
        # Calculate average response time for resolved messages
        resolved_with_time = ContactMessage.objects.filter(
            resolved_at__date=date,
            resolved_at__isnull=False
        ).annotate(
            response_time=F('resolved_at') - F('created_at')
        )
        
        avg_response_time = 0
        if resolved_with_time.exists():
            total_seconds = sum(
                msg.response_time.total_seconds() 
                for msg in resolved_with_time
            )
            avg_response_time = total_seconds / resolved_with_time.count() / 3600  # Convert to hours
        
        # Update or create analytics record
        analytics, created = ContactAnalytics.objects.update_or_create(
            date=date,
            defaults={
                'total_messages': total_messages,
                'new_messages': new_messages,
                'resolved_messages': resolved_messages,
                'avg_response_time_hours': round(avg_response_time, 2)
            }
        )
        
        logger.info(f"Contact analytics generated for {date}")
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to generate contact analytics for {date}: {str(e)}")
        return None

def generate_partner_analytics(date):
    """Generate partner analytics for a given date"""
    from .models import PartnerApplication, PartnerAnalytics
    
    try:
        # Get applications for the date
        applications = PartnerApplication.objects.filter(created_at__date=date)
        
        # Calculate metrics
        total_applications = applications.count()
        pending_applications = PartnerApplication.objects.filter(
            status='pending'
        ).count()
        approved_applications = PartnerApplication.objects.filter(
            approved_at__date=date
        ).count()
        rejected_applications = PartnerApplication.objects.filter(
            status='rejected',
            reviewed_at__date=date
        ).count()
        
        # Applications by type
        restaurant_applications = applications.filter(partner_type='restaurant').count()
        delivery_applications = applications.filter(partner_type='delivery-agent').count()
        investor_applications = applications.filter(partner_type='investor').count()
        
        # Update or create analytics record
        analytics, created = PartnerAnalytics.objects.update_or_create(
            date=date,
            defaults={
                'total_applications': total_applications,
                'pending_applications': pending_applications,
                'approved_applications': approved_applications,
                'rejected_applications': rejected_applications,
                'restaurant_applications': restaurant_applications,
                'delivery_applications': delivery_applications,
                'investor_applications': investor_applications
            }
        )
        
        logger.info(f"Partner analytics generated for {date}")
        return analytics
        
    except Exception as e:
        logger.error(f"Failed to generate partner analytics for {date}: {str(e)}")
        return None

def validate_cameroon_phone(phone):
    """Validate Cameroon phone number format"""
    if not phone:
        return False
    
    # Remove spaces and special characters
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Cameroon phone patterns
    patterns = [
        r'^(\+237|237)?[2368]\d{8}$',  # Standard format
        r'^(\+237|237)?6[5-9]\d{7}$',  # Mobile specific
        r'^(\+237|237)?2[2-3]\d{7}$',  # Landline Yaoundé
        r'^(\+237|237)?3[3-4]\d{7}$',  # Landline Douala
    ]
    
    return any(re.match(pattern, cleaned) for pattern in patterns)

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def get_upload_path(instance, filename):
    """Generate secure upload path for files"""
    import uuid
    from django.utils.text import slugify
    
    # Get file extension
    ext = filename.split('.')[-1].lower()
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.{ext}"
    
    # Create path based on model type
    if hasattr(instance, 'application'):
        # Partner document
        return f"partner_documents/{instance.application.id}/{unique_filename}"
    else:
        # General upload
        return f"uploads/{unique_filename}"

def clean_filename(filename):
    """Clean and sanitize filename"""
    import unicodedata
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    
    # Keep only safe characters
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Replace spaces with underscores
    filename = re.sub(r'[\s]+', '_', filename)
    
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    if len(name) > 50:
        name = name[:50]
    
    return f"{name}.{ext}" if ext else name

