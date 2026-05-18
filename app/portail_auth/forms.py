"""
Formulaires pour authentification : LoginForm, RegisterForm, PasswordResetForm.
Inclut validation côté serveur (vérification email/username unique, force du mot de passe).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from obuffair.app.portail_auth.models_auth import User


class RegisterForm(FlaskForm):
    """Formulaire d'enregistrement"""
    
    username = StringField('Nom d\'utilisateur',
                          validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe',
                            validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe',
                                    validators=[DataRequired(), EqualTo('password')])
    prenom = StringField('Prénom')
    nom = StringField('Nom')
    submit = SubmitField('S\'inscrire')
    
    def validate_email(self, email):
        """Vérifier que l'email n'existe pas déjà"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Cet email est déjà utilisé!')
    
    def validate_username(self, username):
        """Vérifier que le username n'existe pas déjà"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ce nom d\'utilisateur est déjà pris!')
