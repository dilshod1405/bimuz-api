from django.http import JsonResponse
from django.db import connection


def health_check(request):
    status = {
        'status': 'healthy',
        'database': 'connected',
        'version': '1.0'
    }
    status_code = 200
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        status['status'] = 'unhealthy'
        status['database'] = 'disconnected'
        status_code = 503
    
    return JsonResponse(status, status=status_code)
