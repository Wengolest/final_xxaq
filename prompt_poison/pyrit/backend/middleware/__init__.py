"""Middleware module for backend."""

from pyrit.backend.middleware.error_handlers import register_error_handlers

__all__ = ["register_error_handlers"]
