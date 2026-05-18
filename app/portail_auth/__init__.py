from flask import Blueprint, render_template, request, redirect, url_rule, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
# Importation de l'instance de votre base de données (si vous utilisez Flask-SQLAlchemy)
# de type : from app import db 
# Pour l'exemple, nous utiliserons des requêtes SQL textuelles compatibles avec votre stack

auth_bp = Blueprint('auth', __name__)