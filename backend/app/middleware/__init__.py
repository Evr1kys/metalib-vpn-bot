"""
Middleware package
"""
from app.middleware.bot_access import add_bot_access_middleware

__all__ = ['add_bot_access_middleware']
