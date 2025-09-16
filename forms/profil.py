from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, EmailField, FileField
from flask_wtf.file import FileAllowed
from wtforms.validators import DataRequired


class ProfilForm(FlaskForm):
    PROFIL = StringField('Профиль')

