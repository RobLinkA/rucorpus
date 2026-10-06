"""HTTP API (django-ninja). Interactive docs at /api/docs.

Auth is the Django session; state-changing endpoints require the X-CSRFToken header
(enforced by ninja's django_auth). Roles: admin > editor (标注员) > user.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja.security import django_auth

from ..search import QueryError

api = NinjaAPI(title='Rucorpus API', version='2.0', urls_namespace='api')


@api.exception_handler(QueryError)
def _query_error(request, exc):
    return api.create_response(request, {'detail': str(exc)}, status=400)


@api.exception_handler(DjangoValidationError)
def _validation_error(request, exc):
    return api.create_response(request, {'detail': '；'.join(exc.messages)}, status=400)


def require_editor(request):
    if not request.user.is_authenticated or not request.user.can_edit:
        raise HttpError(403, '需要标注员或管理员权限')


def require_admin(request):
    if not request.user.is_authenticated or not request.user.is_admin:
        raise HttpError(403, '需要管理员权限')


def audit(request, action, target='', summary='', **data):
    from ..models import AuditLog
    AuditLog.objects.create(user=request.user if request.user.is_authenticated else None,
                            action=action, target=target, summary=summary[:500], data=data)


from . import auth, manage, me, public, transfer  # noqa: E402,F401

api.add_router('/auth', auth.router)
api.add_router('/', public.router)
api.add_router('/me', me.router, auth=django_auth)
api.add_router('/manage', manage.router, auth=django_auth)
api.add_router('/manage/transfer', transfer.router, auth=django_auth)
