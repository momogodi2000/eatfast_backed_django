# backend/services/email_service.py
import yagmail
import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Email service using yagmail for all email communications"""
    
    def __init__(self):
        self.gmail_user = getattr(settings, 'EMAIL_HOST_USER', '')
        self.gmail_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', self.gmail_user)
        self.admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@eatfast.cm')
        
        # Initialize yagmail
        self.yag = None
        if self.gmail_user and self.gmail_password:
            try:
                self.yag = yagmail.SMTP(self.gmail_user, self.gmail_password)
                logger.info("Email service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize email service: {str(e)}")
    
    def test_connection(self):
        """Test email service connection"""
        try:
            if self.yag:
                # Simple connection test
                return True
            return False
        except Exception as e:
            logger.error(f"Email connection test failed: {str(e)}")
            return False
    
    def send_contact_confirmation(self, contact_inquiry):
        """Send confirmation email to user who submitted contact form"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            subject = "Confirmation de réception - EatFast"
            
            # Prepare email context
            context = {
                'name': contact_inquiry.name,
                'subject_display': contact_inquiry.get_subject_display(),
                'message': contact_inquiry.message,
                'created_at': contact_inquiry.created_at,
                'company_name': 'EatFast',
                'support_email': self.admin_email,
                'support_phone': '+237 698 765 432'
            }
            
            # Render HTML email
            html_content = render_to_string('emails/contact_confirmation.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            self.yag.send(
                to=contact_inquiry.email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Contact confirmation email sent to {contact_inquiry.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send contact confirmation email: {str(e)}")
            return False
    
    def send_contact_notification(self, contact_inquiry):
        """Send notification email to admin about new contact inquiry"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            subject = f"Nouvelle demande de contact - {contact_inquiry.get_subject_display()}"
            
            context = {
                'inquiry': contact_inquiry,
                'admin_url': f"{getattr(settings, 'ADMIN_BASE_URL', 'http://localhost:8000')}/admin/backend/contactinquiry/{contact_inquiry.id}/change/"
            }
            
            html_content = render_to_string('emails/contact_notification.html', context)
            text_content = strip_tags(html_content)
            
            self.yag.send(
                to=self.admin_email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Contact notification email sent to admin")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send contact notification email: {str(e)}")
            return False
    
    def send_partner_application_confirmation(self, application):
        """Send confirmation email to partner applicant"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            subject = "Candidature reçue - EatFast Partenaire"
            
            context = {
                'application': application,
                'partner_type_display': application.get_partner_type_display(),
                'application_id': str(application.application_id),
                'company_name': 'EatFast',
                'support_email': self.admin_email,
                'expected_response_days': '3-5 jours ouvrables'
            }
            
            html_content = render_to_string('emails/partner_confirmation.html', context)
            text_content = strip_tags(html_content)
            
            self.yag.send(
                to=application.email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Partner application confirmation sent to {application.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send partner confirmation email: {str(e)}")
            return False
    
    def send_partner_application_notification(self, application):
        """Send notification email to admin about new partner application"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            subject = f"Nouvelle candidature partenaire - {application.get_partner_type_display()}"
            
            context = {
                'application': application,
                'admin_url': f"{getattr(settings, 'ADMIN_BASE_URL', 'http://localhost:8000')}/admin/backend/partnerapplication/{application.id}/change/",
                'documents_count': application.documents.count()
            }
            
            html_content = render_to_string('emails/partner_notification.html', context)
            text_content = strip_tags(html_content)
            
            self.yag.send(
                to=self.admin_email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Partner application notification sent to admin")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send partner notification email: {str(e)}")
            return False
    
    def send_newsletter_welcome(self, subscription):
        """Send welcome email for newsletter subscription"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            subject = "Bienvenue dans la communauté EatFast !"
            
            context = {
                'subscription': subscription,
                'company_name': 'EatFast',
                'website_url': 'https://eatfast.cm',
                'unsubscribe_url': f"{getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173')}/unsubscribe?email={subscription.email}",
                'support_email': self.admin_email
            }
            
            html_content = render_to_string('emails/newsletter_welcome.html', context)
            text_content = strip_tags(html_content)
            
            self.yag.send(
                to=subscription.email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Newsletter welcome email sent to {subscription.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send newsletter welcome email: {str(e)}")
            return False
    
    def send_partner_status_update(self, application, old_status, new_status):
        """Send email when partner application status changes"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            status_messages = {
                'under_review': 'Votre candidature est maintenant en cours d\'examen.',
                'approved': 'Félicitations ! Votre candidature a été approuvée.',
                'rejected': 'Nous regrettons de vous informer que votre candidature n\'a pas été retenue.',
                'on_hold': 'Votre candidature est temporairement en suspens.',
                'additional_info_required': 'Des informations supplémentaires sont requises pour votre candidature.'
            }
            
            subject = f"Mise à jour de votre candidature EatFast - {application.get_status_display()}"
            
            context = {
                'application': application,
                'old_status': old_status,
                'new_status': new_status,
                'status_message': status_messages.get(new_status, 'Statut mis à jour.'),
                'application_id': str(application.application_id),
                'company_name': 'EatFast',
                'support_email': self.admin_email
            }
            
            html_content = render_to_string('emails/partner_status_update.html', context)
            text_content = strip_tags(html_content)
            
            self.yag.send(
                to=application.email,
                subject=subject,
                contents=[text_content, html_content]
            )
            
            logger.info(f"Partner status update email sent to {application.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send partner status update email: {str(e)}")
            return False
    
    def send_bulk_newsletter(self, recipients, subject, content):
        """Send newsletter to multiple recipients"""
        try:
            if not self.yag:
                logger.warning("Email service not available")
                return False
            
            success_count = 0
            failed_count = 0
            
            for recipient in recipients:
                try:
                    self.yag.send(
                        to=recipient.email,
                        subject=subject,
                        contents=content
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send newsletter to {recipient.email}: {str(e)}")
                    failed_count += 1
            
            logger.info(f"Newsletter sent: {success_count} success, {failed_count} failed")
            return {'success': success_count, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Failed to send bulk newsletter: {str(e)}")
            return False