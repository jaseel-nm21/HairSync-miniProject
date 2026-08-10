"""
HairSync: A Web-Based Hair Donor and Recipient Management Platform
Main Application Entry Point
"""

import os
import sqlite3
from flask import Flask, render_template, session, redirect, url_for

from config import Config
from database import db
from routes.auth import auth_bp, get_role_dashboard
from routes.admin import admin_bp
from routes.donor import donor_bp
from routes.ngo import ngo_bp
from routes.recipient import recipient_bp


def create_app(config_class=Config):
    """Application factory for HairSync."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize Database and teardown hooks
    from database.init_db import init_db_if_needed
    init_db_if_needed(app.config.get('DATABASE'))
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(ngo_bp)
    app.register_blueprint(recipient_bp)

    # Context processors (available across all Jinja2 templates)
    @app.context_processor
    def inject_global_vars():
        return {
            'current_user': {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'email': session.get('user_email'),
                'role': session.get('role'),
                'approval_status': session.get('approval_status')
            } if 'user_id' in session else None,
            'role_dashboard_url': get_role_dashboard(session.get('role')) if 'role' in session else 'index'
        }

    # Root Landing Page
    @app.route('/')
    def index():
        return render_template('index.html')

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html', message=getattr(e, 'description', None)), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404


    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html', error=str(e)), 500

    @app.errorhandler(sqlite3.Error)
    def handle_database_error(e):
        app.logger.error(f"Database Error: {e}")
        return render_template('errors/db_error.html', error=str(e)), 500

    # Custom CLI Command: flask init-db
    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database from command line."""
        from database.init_db import run_init
        run_init()

    return app


app = create_app()

if __name__ == '__main__':
    # Run locally on port 5000 in debug mode
    app.run(host='127.0.0.1', port=5000, debug=True)
