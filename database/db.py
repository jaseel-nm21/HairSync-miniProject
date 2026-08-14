"""
HairSync Database Connection Helper
Provides secure parameterized queries and dictionary cursor support via Python's built-in sqlite3.
"""

import os
import sqlite3
from flask import current_app, g
from config import Config


from datetime import datetime


class DateTimeStr(str):
    """String subclass that supports .strftime() for seamless Jinja2 template formatting."""
    def strftime(self, fmt):
        for parse_fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'):
            try:
                return datetime.strptime(self, parse_fmt).strftime(fmt)
            except ValueError:
                pass
        return self


def dict_factory(cursor, row):
    """Convert sqlite3 row tuple to a dictionary with DateTimeStr formatting support."""
    fields = [column[0] for column in cursor.description]
    res = {}
    for key, value in zip(fields, row):
        if isinstance(value, str) and (key.endswith('_at') or 'date' in key or key.endswith('_joined') or key.endswith('_on')):
            res[key] = DateTimeStr(value)
        else:
            res[key] = value
    return res


def get_db():
    """
    Open a new SQLite database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        db_path = Config.DATABASE
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        try:
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = dict_factory
            # Enable Foreign Key enforcement in SQLite
            g.db.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as err:
            current_app.logger.error(f"Database connection error: {err}")
            raise err
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def _prepare_sql(query):
    """
    Normalize parameter placeholders from MySQL (%s) to SQLite (?).
    """
    return query.replace('%s', '?')


def query_db(query, args=(), one=False):
    """
    Executes a SELECT query with parameterized inputs to prevent SQL injection.
    
    :param query: SQL query string with %s or ? placeholders
    :param args: Tuple or list of parameters
    :param one: If True, returns a single dictionary row or None
    :return: List of dicts or single dict
    """
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(_prepare_sql(query), args)
        result = cursor.fetchall()
        return (result[0] if result else None) if one else result
    finally:
        cursor.close()


def execute_db(query, args=(), commit=True):
    """
    Executes an INSERT, UPDATE, or DELETE query with parameterized inputs.
    
    :param query: SQL statement with %s or ? placeholders
    :param args: Tuple or list of parameters
    :param commit: If True, commits the transaction immediately
    :return: dict with 'lastrowid' and 'rowcount'
    """
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(_prepare_sql(query), args)
        last_id = cursor.lastrowid
        affected = cursor.rowcount
        if commit:
            db.commit()
        return {'lastrowid': last_id, 'rowcount': affected}
    except sqlite3.Error as err:
        db.rollback()
        current_app.logger.error(f"SQL execution error on [{query}]: {err}")
        raise err
    finally:
        cursor.close()


def init_app(app):
    """Register database teardown hook with the Flask app."""
    app.teardown_appcontext(close_db)
