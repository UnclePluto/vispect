from django.db import connection, DatabaseError
from django.http import JsonResponse

def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({'code':'database_unavailable','message':'数据库暂不可用','fields':{}}, status=503)
    return JsonResponse({'status':'ok','database':'postgresql'})
