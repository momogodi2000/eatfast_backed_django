from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

@api_view(['GET'])
def api_root(request):
    """
    API root endpoint for Eat Fast backend
    """
    return Response({
        'message': 'Welcome to Eat Fast API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/v1/health/',
            'admin': '/admin/',
        }
    })

@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint
    """
    return Response({
        'status': 'healthy',
        'service': 'eatfast-backend',
        'timestamp': '2025-01-01T00:00:00Z'
    }, status=status.HTTP_200_OK)