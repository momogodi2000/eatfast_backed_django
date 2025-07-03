
# backend/management/commands/send_daily_reports.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from backend.models import ContactMessage, PartnerApplication
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send daily reports to administrators'
    
    def handle(self, *args, **options):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get yesterday's stats
        new_contacts = ContactMessage.objects.filter(
            created_at__date=yesterday
        ).count()
        
        new_partners = PartnerApplication.objects.filter(
            created_at__date=yesterday
        ).count()
        
        pending_contacts = ContactMessage.objects.filter(
            status__in=['new', 'in_progress']
        ).count()
        
        pending_partners = PartnerApplication.objects.filter(
            status='pending'
        ).count()
        
        # Compose email
        subject = f'EatFast Daily Report - {yesterday.strftime("%Y-%m-%d")}'
        message = f"""
        Rapport quotidien EatFast - {yesterday.strftime('%d/%m/%Y')}
        
        NOUVEAUX HIER:
        • Messages de contact: {new_contacts}
        • Candidatures partenaires: {new_partners}
        
        EN ATTENTE:
        • Messages de contact: {pending_contacts}
        • Candidatures partenaires: {pending_partners}
        
        Tableau de bord: {settings.SITE_URL}/admin/
        
        --
        Système EatFast
        """
        
        # Send to admins
        admin_emails = [email for name, email in settings.ADMINS]
        
        if admin_emails:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                    fail_silently=False,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Daily report sent to {len(admin_emails)} admins")