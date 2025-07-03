
# backend/management/commands/generate_analytics.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from backend.utils import generate_contact_analytics, generate_partner_analytics

class Command(BaseCommand):
    help = 'Generate analytics for contact and partner data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to generate analytics for (default: 7)'
        )
        parser.add_argument(
            '--type',
            choices=['contact', 'partner', 'all'],
            default='all',
            help='Type of analytics to generate (default: all)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        analytics_type = options['type']
        
        today = timezone.now().date()
        
        self.stdout.write(f"Generating analytics for the last {days} days...")
        
        for i in range(days):
            date = today - timedelta(days=i)
            
            if analytics_type in ['contact', 'all']:
                contact_analytics = generate_contact_analytics(date)
                if contact_analytics:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Contact analytics generated for {date}")
                    )
            
            if analytics_type in ['partner', 'all']:
                partner_analytics = generate_partner_analytics(date)
                if partner_analytics:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Partner analytics generated for {date}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"Analytics generation completed for {days} days!")
        )
