from rest_framework.response import Response

class ApiError(Exception):
    def __init__(self, code: str, message: str, fields: dict[str,list[str]] | None = None, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.fields, self.status = code, message, fields or {}, status

def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_exception_handler
    if isinstance(exc, ApiError):
        return Response({'code':exc.code,'message':exc.message,'fields':exc.fields}, status=exc.status)
    return drf_exception_handler(exc, context)
