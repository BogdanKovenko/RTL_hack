from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, BooleanField, EmailField, FileField, SelectMultipleField, SelectField
from flask_wtf.file import FileAllowed
from wtforms.validators import DataRequired, ValidationError, Email, Length
from wtforms.widgets import CheckboxInput, ListWidget


class RegisterForm(FlaskForm):
    email = EmailField('Электронная почта', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8, max=64)])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired(), Length(min=8, max=64)])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = EmailField('Электронная почта', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(max=64)])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class ChangePasswordForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired(), Length(max=100)])
    now_password = PasswordField('Текущий пароль', validators=[DataRequired(), Length(max=64)])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=8, max=64)])
    submit = SubmitField('Изменить')

class ChangePasswordEmailForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Отправить код')

class CodeForm(FlaskForm):
    code = StringField('Код с почты', validators=[DataRequired(), Length(min=5, max=5)])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=8, max=64)])
    submit = SubmitField('Проверить код')

