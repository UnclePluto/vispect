import re
from apps.core.errors import ApiError

def normalize_phone(raw: str) -> str:
    if isinstance(raw,str):
        value=re.sub(r'[\s-]','',raw)
        if value.startswith('0086'):value=value[4:]
        elif value.startswith('+86'):value=value[3:]
        if re.fullmatch(r'1[3-9][0-9]{9}',value):return '+86'+value
    raise ApiError('validation_error','请填写有效的中国大陆手机号',{'phone':['请输入有效的 11 位手机号']},400)
