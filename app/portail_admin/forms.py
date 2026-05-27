"""
Formulaires admin : création/édition vol, avion, configuration tarifaire, gestion utilisateurs.
Validation stricte des données critiques (horaires, capacités).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError, NumberRange, Optional
from app.portail_admin.modele_admin import Avion

class FormAjouterAvion(FlaskForm):
    """Ajouter/Modif avion"""
    def __init__(self, original_immatriculation=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_immatriculation = original_immatriculation
    
    # Immatriculation format français
    immatriculation = StringField(
        'Immatriculation',
        validators=[
            DataRequired(message='L\'immatriculation requise'),
            Length(min=5, max=10, message='L\'immatriculation = 5 à 10 caractères'),
            Regexp(r'^[A-Z]{1,2}-[A-Z0-9]{3,5}$', message='Format invalide (ex: F-ABCD ou F-OBUF3)')
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
    
    nb_rangees = IntegerField(
        'Nombre de rangées',
        validators=[
            DataRequired(message='Le nombre de rangées est requis'),
            NumberRange(min=1, message='Le nombre de rangées doit être supérieur ou égal à 1')
        ]
    )

    largeur_rangee = IntegerField(
        'Largeur de rangée',
        validators=[
            DataRequired(message='La largeur de rangée est requise'),
            NumberRange(min=1, message='La largeur de rangée doit être supérieure ou égale à 1')
        ]
    )

    eco_rang_de = IntegerField(
        'Éco - rangée début',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )

    eco_rang_a = IntegerField(
        'Éco - rangée fin',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )

    bus_rang_de = IntegerField(
        'Business - rangée début',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )

    bus_rang_a = IntegerField(
        'Business - rangée fin',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )

    first_rang_de = IntegerField(
        'First - rangée début',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )

    first_rang_a = IntegerField(
        'First - rangée fin',
        validators=[
            Optional(),
            NumberRange(min=0, message='La rangée doit être supérieure ou égale à 0')
        ]
    )
    
    actif = BooleanField('Avion actif')
    
    soumettre = SubmitField('Ajouter/Modifier')
    
    def validate_immatriculation(self, field):
        """Valide que l'immatriculation n'existe pas déjà (pour l'ajout)"""
        # Si on est en édition et que l'immatriculation n'a pas changé, ne pas lever d'erreur
        if self._original_immatriculation and field.data.upper() == self._original_immatriculation:
            return

        avion_existant = Avion.query.filter_by(immatriculation=field.data.upper()).first()
        if avion_existant:
            raise ValidationError('Cette immatriculation existe déjà dans la base de données')
    
    def validate_eco_rang_de(self, field):
        if self.bus_rang_a.data and field.data and field.data <= self.bus_rang_a.data:
            raise ValidationError('La rangée de début de l’éco doit se trouver après le business')
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de début de l’éco doit être inférieure ou égale au nombre total de rangées')

    def validate_eco_rang_a(self, field):
        if self.eco_rang_de.data and field.data and field.data < self.eco_rang_de.data:
            raise ValidationError('La rangée de fin de l’éco doit être supérieure ou égale à la rangée de début')
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de fin de l’éco doit être inférieure ou égale au nombre total de rangées')

    def validate_bus_rang_de(self, field):
        if self.first_rang_a.data and field.data and field.data <= self.first_rang_a.data:
            raise ValidationError('La rangée de début du business doit se trouver après le first')
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de début du business doit être inférieure ou égale au nombre total de rangées')

    def validate_bus_rang_a(self, field):
        if self.bus_rang_de.data and field.data and field.data < self.bus_rang_de.data:
            raise ValidationError('La rangée de fin du business doit être supérieure ou égale à la rangée de début')
        if self.eco_rang_de.data and field.data and field.data >= self.eco_rang_de.data:
            raise ValidationError('La rangée de fin du business doit se trouver avant l’éco')
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de fin du business doit être inférieure ou égale au nombre total de rangées')

    def validate_first_rang_de(self, field):
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de début du first doit être inférieure ou égale au nombre total de rangées')

    def validate_first_rang_a(self, field):
        if self.first_rang_de.data and field.data and field.data < self.first_rang_de.data:
            raise ValidationError('La rangée de fin du first doit être supérieure ou égale à la rangée de début')
        if self.bus_rang_de.data and field.data and field.data >= self.bus_rang_de.data:
            raise ValidationError('La rangée de fin du first doit se trouver avant le business')
        if self.nb_rangees.data and field.data and field.data > self.nb_rangees.data:
            raise ValidationError('La rangée de fin du first doit être inférieure ou égale au nombre total de rangées')
