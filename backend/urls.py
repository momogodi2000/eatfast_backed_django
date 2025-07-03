# backend/urls.py
from django.urls import path
from . import views

app_name = 'backend'

urlpatterns = [
    # API Root and Health
    path('', views.api_root, name='api-root'),
    path('health/', views.health_check, name='health-check'),
    path('service-health/', views.service_health, name='service-health'),
    
    # Contact endpoints
    path('contact/', views.submit_contact_inquiry, name='contact-submit'),
    
    # Partner application endpoints
    path('partner-application/', views.submit_partner_application, name='partner-application-submit'),
    path('partner-status/', views.check_application_status, name='partner-status-check'),
    
    # Newsletter endpoints
    path('newsletter/', views.subscribe_newsletter, name='newsletter-subscribe'),
]