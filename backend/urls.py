# backend/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'contact', views.ContactMessageViewSet)
router.register(r'partner', views.PartnerApplicationViewSet)
router.register(r'contact-analytics', views.ContactAnalyticsViewSet)
router.register(r'partner-analytics', views.PartnerAnalyticsViewSet)
router.register(r'partner-documents', views.PartnerDocumentViewSet)

urlpatterns = [
    # Basic API endpoints
    path('', views.api_root, name='api-root'),
    path('health/', views.health_check, name='health-check'),
    
    # ViewSet URLs
    path('', include(router.urls)),
    
    # Configuration endpoints
    path('contact/config/', views.contact_form_config, name='contact-form-config'),
    path('partner/config/', views.partner_form_config, name='partner-form-config'),
    
    # Export endpoints
    path('contact/export/', views.export_contact_messages, name='export-contact-messages'),
    path('partner/export/', views.export_partner_applications, name='export-partner-applications'),
    
    # Search and analytics
    path('search/', views.global_search, name='global-search'),
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
]