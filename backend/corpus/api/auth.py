from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth
from ninja.utils import check_csrf

router = Router(tags=['auth'])


def user_payload(user):
    if not user.is_authenticated:
        return None
    return {'id': user.id, 'username': user.username, 'display_name': user.display_name or user.username,
            'role': 'admin' if user.is_admin else user.role, 'institution': user.institution,
            'can_edit': user.can_edit, 'is_admin': user.is_admin}


@router.get('/session')
def session(request):
    """Current user (or null) — also sets the CSRF cookie for the SPA."""
    get_token(request)
    return {'user': user_payload(request.user)}


class LoginIn(Schema):
    username: str
    password: str


@router.post('/login')
def do_login(request, data: LoginIn):
    if check_csrf(request) is not None:
        raise HttpError(403, '页面验证已过期，请刷新后重试')
    user = authenticate(request, username=data.username.strip(), password=data.password)
    if user is None:
        raise HttpError(400, '用户名或密码错误')
    login(request, user)
    return {'user': user_payload(user)}


@router.post('/logout', auth=django_auth)
def do_logout(request):
    logout(request)
    return {'ok': True}


class PasswordIn(Schema):
    old_password: str
    new_password: str


@router.post('/password', auth=django_auth)
def change_password(request, data: PasswordIn):
    if not request.user.check_password(data.old_password):
        raise HttpError(400, '原密码不正确')
    validate_password(data.new_password, request.user)
    request.user.set_password(data.new_password)
    request.user.save()
    update_session_auth_hash(request, request.user)
    return {'ok': True}


class ProfileIn(Schema):
    display_name: str = ''
    institution: str = ''


@router.put('/profile', auth=django_auth)
def update_profile(request, data: ProfileIn):
    request.user.display_name = data.display_name.strip()
    request.user.institution = data.institution.strip()
    request.user.save(update_fields=['display_name', 'institution'])
    return {'user': user_payload(request.user)}
