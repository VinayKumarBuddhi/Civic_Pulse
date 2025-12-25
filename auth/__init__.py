"""
Authentication package for Civic Pulse
"""
from .authentication import (
    hash_password,
    verify_password,
    login,
    register_user
)
from .session import (
    login_user,
    logout_user,
    is_authenticated,
    get_current_user,
    get_current_role,
    require_role
)

__all__ = [
    'hash_password',
    'verify_password',
    'login',
    'register_user',
    'login_user',
    'logout_user',
    'is_authenticated',
    'get_current_user',
    'get_current_role',
    'require_role'
]

