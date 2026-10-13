from .errors import ApiError

def paginate(queryset,request,serialize):
    try:
        page=int(request.query_params.get('page',1));size=int(request.query_params.get('page_size',20))
        if page<1 or not 1<=size<=100:raise ValueError()
    except ValueError:raise ApiError('validation_error','分页参数不正确',status=400)
    count=queryset.count()
    return {'count':count,'results':[serialize(obj) for obj in queryset[(page-1)*size:page*size]]}
