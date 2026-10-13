from rest_framework.response import Response

class ApiError(Exception):
    def __init__(self, code: str, message: str, fields: dict[str,list[str]] | None = None, status: int = 409):
        super().__init__(message)
        self.code, self.message, self.fields, self.status = code, message, fields or {}, status

def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_exception_handler
    from django.db import IntegrityError
    from rest_framework.exceptions import ValidationError,APIException
    if isinstance(exc, ApiError):
        return Response({'code':exc.code,'message':exc.message,'fields':exc.fields}, status=exc.status)
    if isinstance(exc,IntegrityError):
        return Response({'code':'constraint_conflict','message':'数据冲突，请检查编号及关联','fields':{}},status=409)
    if isinstance(exc,ValidationError):
        def flatten(value):
            if isinstance(value,dict):return [f'{key}：{item}' for key,values in value.items() for item in flatten(values)]
            if isinstance(value,list):return [item for part in value for item in flatten(part)]
            return [str(value)]
        fields={str(key):flatten(value) for key,value in exc.detail.items()} if isinstance(exc.detail,dict) else {'non_field_errors':flatten(exc.detail)}
        return Response({'code':'validation_error','message':'请检查填写内容','fields':fields},status=400)
    if isinstance(exc,APIException):
        return Response({'code':exc.default_code,'message':str(exc.detail),'fields':{}},status=exc.status_code)
    return drf_exception_handler(exc, context)
