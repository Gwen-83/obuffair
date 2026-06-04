"""
Formulaires admin : création/édition vol, avion, configuration tarifaire, gestion utilisateurs.
Validation stricte des données critiques (horaires, capacités).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, BooleanField, SubmitField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError, NumberRange, Optional, Email
from app.portail_admin.modele_admin import Avion
from app import db
from sqlalchemy import text

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

        avion_existant = db.session.execute(
            text("SELECT immatriculation FROM avions WHERE immatriculation = :immat LIMIT 1"),
            {"immat": field.data.upper()}
        ).fetchone()
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


class FormAeroport(FlaskForm):
    def __init__(self, original_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_id = original_id

    original_id = HiddenField()

    id_aeroport = StringField(
        'Code aéroport',
        validators=[
            DataRequired(message='Le code de l’aéroport est requis'),
            Length(min=3, max=4, message='Le code doit faire entre 3 et 4 caractères'),
            Regexp(r'^[A-Z]{3,4}$', message='Utilisez uniquement des lettres majuscules, ex: CDG')
        ]
    )

    nom = StringField(
        'Nom de l’aéroport',
        validators=[
            DataRequired(message='Le nom est requis'),
            Length(min=3, max=120, message='Le nom doit comporter entre 3 et 120 caractères')
        ]
    )

    ville = StringField(
        'Ville',
        validators=[
            DataRequired(message='La ville est requise'),
            Length(min=2, max=100)
        ]
    )

    pays = StringField(
        'Pays',
        validators=[
            DataRequired(message='Le pays est requis'),
            Length(min=2, max=100)
        ]
    )

    decalage_utc = StringField(
        'Décalage UTC',
        validators=[
            DataRequired(message='Le décalage UTC est requis'),
            Regexp(r'^[+-](0\d|1[0-2])(:[0-5][0-9])?$', message='Format UTC invalide, ex: +01:00 ou -05:00')
        ]
    )

    latitude = StringField(
        'Latitude',
        validators=[
            Optional(),
            Regexp(r'^-?\d{1,2}(\.\d+)?$', message='La latitude doit être un nombre valide')
        ]
    )

    longitude = StringField(
        'Longitude',
        validators=[
            Optional(),
            Regexp(r'^-?\d{1,3}(\.\d+)?$', message='La longitude doit être un nombre valide')
        ]
    )

    terminals_count = IntegerField(
        'Terminaux',
        validators=[Optional(), NumberRange(min=0, message='Valeur positive requise')]
    )

    gates_total = IntegerField(
        'Nombre de gates',
        validators=[Optional(), NumberRange(min=0, message='Valeur positive requise')]
    )

    lounges_count = IntegerField(
        'Salons',
        validators=[Optional(), NumberRange(min=0, message='Valeur positive requise')]
    )

    parkings_count = IntegerField(
        'Parkings',
        validators=[Optional(), NumberRange(min=0, message='Valeur positive requise')]
    )

    services = StringField(
        'Services disponibles',
        validators=[Optional(), Length(max=200)]
    )

    contact_phone = StringField(
        'Contact téléphone',
        validators=[Optional(), Length(max=50)]
    )

    contact_email = StringField(
        'Contact email',
        validators=[Optional(), Email(message='Adresse email invalide')]
    )

    description = TextAreaField(
        'Description & infrastructure',
        validators=[Optional(), Length(max=500)]
    )

    model_3d_url = StringField(
        'URL modèle 3D',
        validators=[Optional(), Length(max=255)]
    )

    soumettre = SubmitField('Enregistrer l’aéroport')

    def validate_id_aeroport(self, field):
        if self._original_id and field.data == self._original_id:
            return

        aeroport_existant = db.session.execute(
            text('SELECT id_aeroport FROM aeroports WHERE id_aeroport = :code LIMIT 1'),
            {'code': field.data}
        ).fetchone()
        if aeroport_existant:
            raise ValidationError('Ce code d’aéroport existe déjà')
