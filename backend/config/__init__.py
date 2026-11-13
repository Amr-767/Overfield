"""Overfield project package.

Importing the Celery app here guarantees it is loaded when Django starts, so
``@shared_task`` decorators bind to the correct application.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
