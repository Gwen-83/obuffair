"""
Formulaires pour authentification.
Validation robuste avec:
- Email unique et valide
- Mot de passe fort (min 8 caractères, majuscule, minuscule, chiffre, caractère spécial)
- Nom et prénom requis
"""

import re  # Pour les regex (pattern dans string)
from flask_wtf import FlaskForm  # Forms securisées avec CSRF token
from wtforms import StringField, PasswordField, SubmitField, DateField  # Types de champs
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError  # Validateurs prédéfinis
from app.portail_auth.models_auth import User  # Model pour vérifier si l'email existe déjà


class StrongPasswordValidator:
    """
    Validateur custom pour vérifier que le password est fort.
    On l'utilise dans RegisterForm pour forcer les users à utiliser des bons passwords.
    """
    def __call__(self, form, field):
        # field.data = password utilisateur
        password = field.data
        errors = []
        
        # password = 8 caractères
        if len(password) < 8:
            errors.append('minimum 8 caractères')
        
        # au - 1 majuscules
        if not re.search(r'[A-Z]', password):
            errors.append('au moins une majuscule (A-Z)')
        
        # au - une miniscule
        if not re.search(r'[a-z]', password):
            errors.append('au moins une minuscule (a-z)')
        
        # au - 1 chiffres /d digit
        if not re.search(r'\d', password):
            errors.append('au moins un chiffre (0-9)')
        
        # au - un caract spécial
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.< >?/\\|`~]', password):
            errors.append('au moins un caractère spécial (!@#$%^&* etc.')
        
        # Si error!=[] alors il y a erreur et l'afficher
        if errors:
            raise ValidationError(f'Mot de passe faible. Requis: {", ".join(errors)}')


class RegisterForm(FlaskForm):
    """formulaire affiché à l'utilisateir"""
    
    email = StringField(
        'Email',  # Label
        validators=[ 
            DataRequired('Champ obligatoire'),
            Email('Email invalide')  # Format email valide
        ]
    )
    
    prenom = StringField(
        'Prénom',
        validators=[DataRequired('Champ obligatoire')]
    )
    
    nom = StringField(
        'Nom',
        validators=[DataRequired('Champ obligatoire')]
    )
    
    date_naissance = DateField(
        'Date de naissance',
        format='%m-%d-%Y',  # MM-JJ-AAAA
        render_kw={'type': 'date'},  # calendrier
        validators=[]
    )
    
    # Mot de passe + validation ci dessus
    password = PasswordField(
        'Mot de passe',
        validators=[
            DataRequired('Champ obligatoire'),
            StrongPasswordValidator()
        ]
    )
    
    # Confirmation du mdp
    confirm_password = PasswordField(
        'Confirmer le mot de passe',
        validators=[
            DataRequired('Champ obligatoire'),
            EqualTo('password', message='Les mots de passe ne correspondent pas')
        ]
    )
    
    # soumettre
    submit = SubmitField('S\'inscrire')
    
    def validate_email(self, email):
        # Chercher en BD si cet email existe déjà
        # .first() retourne le premier résultat ou None
        if User.query.filter_by(email=email.data.lower()).first():
            # L'email existe, on lève une erreur
            raise ValidationError('Cet email est déjà associé à un compte')


class LoginForm(FlaskForm):
    """Formulaire de connexion"""
    
    email = StringField(
        'Email',
        validators=[
            DataRequired('Champ obligatoire'),
            Email('Email invalide')
        ]
    )
    
    password = PasswordField(
        'Mot de passe',
        validators=[DataRequired('Champ obligatoire')]
    )
    
    submit = SubmitField('Se connecter')
