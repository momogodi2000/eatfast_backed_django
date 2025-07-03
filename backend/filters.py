
# backend/filters.py
import django_filters
from django.db.models import Q
from .models import ContactMessage, PartnerApplication

class ContactMessageFilter(django_filters.FilterSet):
    """Filter for contact messages"""
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    resolved_after = django_filters.DateFilter(field_name='resolved_at', lookup_expr='date__gte')
    resolved_before = django_filters.DateFilter(field_name='resolved_at', lookup_expr='date__lte')
    
    # Choice filters
    status = django_filters.ChoiceFilter(choices=ContactMessage.STATUS_CHOICES)
    priority = django_filters.ChoiceFilter(choices=ContactMessage.PRIORITY_CHOICES)
    subject = django_filters.ChoiceFilter(choices=ContactMessage.SUBJECT_CHOICES)
    preferred_contact_method = django_filters.ChoiceFilter(choices=ContactMessage.CONTACT_METHOD_CHOICES)
    
    # Text filters
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    company = django_filters.CharFilter(lookup_expr='icontains')
    message = django_filters.CharFilter(lookup_expr='icontains')
    
    # Boolean filters
    has_phone = django_filters.BooleanFilter(method='filter_has_phone')
    has_company = django_filters.BooleanFilter(method='filter_has_company')
    is_resolved = django_filters.BooleanFilter(method='filter_is_resolved')
    
    # Custom search
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = ContactMessage
        fields = [
            'status', 'priority', 'subject', 'preferred_contact_method',
            'created_after', 'created_before', 'resolved_after', 'resolved_before'
        ]
    
    def filter_has_phone(self, queryset, name, value):
        if value:
            return queryset.exclude(phone__isnull=True).exclude(phone='')
        return queryset.filter(Q(phone__isnull=True) | Q(phone=''))
    
    def filter_has_company(self, queryset, name, value):
        if value:
            return queryset.exclude(company__isnull=True).exclude(company='')
        return queryset.filter(Q(company__isnull=True) | Q(company=''))
    
    def filter_is_resolved(self, queryset, name, value):
        if value:
            return queryset.filter(status='resolved')
        return queryset.exclude(status='resolved')
    
    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(email__icontains=value) |
            Q(company__icontains=value) |
            Q(message__icontains=value)
        )

class PartnerApplicationFilter(django_filters.FilterSet):
    """Filter for partner applications"""
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')
    reviewed_after = django_filters.DateFilter(field_name='reviewed_at', lookup_expr='date__gte')
    reviewed_before = django_filters.DateFilter(field_name='reviewed_at', lookup_expr='date__lte')
    
    # Choice filters
    partner_type = django_filters.ChoiceFilter(choices=PartnerApplication.PARTNER_TYPE_CHOICES)
    status = django_filters.ChoiceFilter(choices=PartnerApplication.APPLICATION_STATUS_CHOICES)
    legal_status = django_filters.ChoiceFilter(choices=PartnerApplication.LEGAL_STATUS_CHOICES)
    vehicle_type = django_filters.ChoiceFilter(choices=PartnerApplication.VEHICLE_TYPE_CHOICES)
    investment_type = django_filters.ChoiceFilter(choices=PartnerApplication.INVESTMENT_TYPE_CHOICES)
    service_type = django_filters.ChoiceFilter(choices=PartnerApplication.SERVICE_TYPE_CHOICES)
    
    # Text filters
    contact_name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    business_name = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    cuisine_type = django_filters.CharFilter(lookup_expr='icontains')
    
    # Numeric filters
    investment_amount_min = django_filters.NumberFilter(field_name='investment_amount', lookup_expr='gte')
    investment_amount_max = django_filters.NumberFilter(field_name='investment_amount', lookup_expr='lte')
    capacity_min = django_filters.NumberFilter(field_name='capacity', lookup_expr='gte')
    capacity_max = django_filters.NumberFilter(field_name='capacity', lookup_expr='lte')
    
    # Boolean filters
    has_business_name = django_filters.BooleanFilter(method='filter_has_business_name')
    has_documents = django_filters.BooleanFilter(method='filter_has_documents')
    is_reviewed = django_filters.BooleanFilter(method='filter_is_reviewed')
    
    # Custom search
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = PartnerApplication
        fields = [
            'partner_type', 'status', 'legal_status', 'vehicle_type',
            'investment_type', 'service_type', 'city',
            'created_after', 'created_before', 'reviewed_after', 'reviewed_before'
        ]
    
    def filter_has_business_name(self, queryset, name, value):
        if value:
            return queryset.exclude(business_name__isnull=True).exclude(business_name='')
        return queryset.filter(Q(business_name__isnull=True) | Q(business_name=''))
    
    def filter_has_documents(self, queryset, name, value):
        if value:
            return queryset.filter(documents__isnull=False).distinct()
        return queryset.filter(documents__isnull=True)
    
    def filter_is_reviewed(self, queryset, name, value):
        if value:
            return queryset.exclude(reviewed_at__isnull=True)
        return queryset.filter(reviewed_at__isnull=True)
    
    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(contact_name__icontains=value) |
            Q(email__icontains=value) |
            Q(business_name__icontains=value) |
            Q(city__icontains=value) |
            Q(cuisine_type__icontains=value)
        )
