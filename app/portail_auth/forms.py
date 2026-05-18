"""
Formulaires pour authentification.
Validation robuste avec:
- Email unique et valide
- Username unique (3-20 caractères)
- Mot de passe fort (min 8 caractères, majuscule, minuscule, chiffre, caractère spécial)
"""

import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app.portail_auth.models_auth import User


class StrongPasswordValidator:
    """
    Valide qu'un mot de passe est fort:
    - Min 8 caractères
    - Au moins une majuscule
    - Au moins une minuscule
    - Au moins un chiffre
    - Au moins un caractère spécial (!@#$%^&*)
    """
    def __call__(self, form, field):
        password = field.data
        errors = []
        
        if len(password) < 8:
            errors.append('minimum 8 caractères')
        if not re.search(r'[A-Z]', password):
            errors.append('au moins une majuscule (A-Z)')
        if not re.search(r'[a-z]', password):
            errors.append('au moins une minuscule (a-z)')
        if not re.search(r'\d', password):
            errors.append('au moins un chiffre (0-9)')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            errors.append('au moins un caractère spécial (!@#$%^&* etc.)')
        
        if errors:
            raise ValidationError(f'Mot de passe faible. Requis: {", ".join(errors)}')


class RegisterForm(FlaskForm):
    """Formulaire d'enregistrement sécurisé"""
    
    username = StringField(
        'Nom d\'utilisateur',
        validators=[
            DataRequired('Champ obligatoire'),
            Length(min=3, max=20, message='Entre 3 et 20 caractères')
        ]
    )
    
    email = StringField(
        'Email',
        validators=[
            DataRequired('Champ obligatoire'),
            Email('Email invalide')
        ]
    )
    
    password = PasswordField(
        'Mot de passe',
        validators=[
            DataRequired('Champ obligatoire'),
            StrongPasswordValidator()
        ]
    )
    
    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[
            DataRequired('Champ obligatoire'),
            EqualTo('password', message='Les mots de passe ne correspondent pas')
        ]
    )
    
    prenom = StringField('Prénom')
    nom = StringField('Nom')
    submit = SubmitField('S\'inscrire')
    
    def validate_email(self, email):
        """Vérifier unicité de l'email"""
        if User.query.filter_by(email=email.data.lower()).first():
            raise ValidationError('Cet email est déjà associé à un compte')
    
    def validate_username(self, username):
        """Vérifier unicité du username"""
        if User.query.filter_by(username=username.data.lower()).first():
            raise ValidationError('Ce nom d\'utilisateur n\'est pas disponible')
