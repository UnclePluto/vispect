from .models import Tenant

def lookup_tenant(slug):
    return Tenant.objects.using('control').filter(slug=slug,enabled=True).first()
