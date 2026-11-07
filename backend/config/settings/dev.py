"""Development settings."""

from .base import *  # noqa: F401,F403

DEBUG = True

# Convenient local defaults when DJANGO_DEBUG is unset in .env.
if env("DJANGO_DEBUG") is None:  # noqa: F405
    DEBUG = True
