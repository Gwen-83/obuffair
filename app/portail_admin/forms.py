"""
Formulaires admin : création/édition vol, avion, configuration tarifaire, gestion utilisateurs.
Validation stricte des données critiques (horaires, capacités).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError
from app.portail_admin.modele_admin import Avion

class FormAjouterAvion(FlaskForm):
    """Ajouter/Modif avion"""
    
    # Immatriculation format français
    immatriculation = StringField(
        'Immatriculation',
        validators=[
            DataRequired(message='L\'immatriculation requise'),
            Length(min=5, max=10, message='L\'immatriculation = 5 à 10 caractères'),
            Regexp(r'^[A-Z]{1,2}-[A-Z0-9]{3,4}$', message='Format invalide (ex: F-ABCD)')
        ]
    )
    
    # Modèle
    modele = StringField(
        'Modèle d\'avion',
        validators=[
            DataRequired(message='Le modèle est requis'),
            Length(min=3, max=50, message='Le modèle doit avoir entre 3 et 50 caractères'),
            Regexp(r'[A-Z][0-9]{3}$', message='Format invalide (A111)')
        ]
    )
    
    # Capacités (nombres strictement positifs)
    capacite_eco = IntegerField(
        'Capacité Économique',
        validators=[DataRequired(message='La capacité économique est requise')]
    )
    
    capacite_business = IntegerField(
        'Capacité Business',
        validators=[DataRequired(message='La capacité business est requise')]
    )
    
    capacite_first = IntegerField(
        'Capacité First',
        validators=[DataRequired(message='La capacité first est requise')]
    )
    
    actif = BooleanField('Avion actif')
    
    soumettre = SubmitField('Ajouter/Modifier')
    
    def validate_immatriculation(self, field):
        """Valide que l'immatriculation n'existe pas déjà (pour l'ajout)"""
        avion_existant = Avion.query.filter_by(immatriculation=field.data.upper()).first()
        if avion_existant:
            raise ValidationError('Cette immatriculation existe déjà dans la base de données')
    
    def validate_capacite_eco(self, field):
        """Valide que la capacité économique est positive"""
        if field.data and field.data <= 0:
            raise ValidationError('La capacité doit être supérieure à 0')
    
    def validate_capacite_business(self, field):
        """Valide que la capacité business est positive"""
        if field.data and field.data <= 0:
            raise ValidationError('La capacité doit être supérieure à 0')
    
    def validate_capacite_first(self, field):
        """Valide que la capacité first est positive"""
        if field.data and field.data <= 0:
            raise ValidationError('La capacité doit être supérieure à 0')
