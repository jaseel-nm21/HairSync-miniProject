"""
Routes Package
Registers Blueprints for Authentication, Admin, Donor, NGO, and Recipient modules.
"""

from .auth import auth_bp
from .admin import admin_bp
from .donor import donor_bp
from .ngo import ngo_bp
from .recipient import recipient_bp

__all__ = ['auth_bp', 'admin_bp', 'donor_bp', 'ngo_bp', 'recipient_bp']
