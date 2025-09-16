from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, FileField, SelectField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed


class PortfolioForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    year = StringField('Год и месяц достижения (Формат месяц:год)', validators=[DataRequired()])
    photo = FileField('Фото диплома (png, jpg, jpeg)', validators=[FileAllowed(['jpg', 'png', 'jpeg']), DataRequired()])
    type = SelectField('Тип достижения', coerce=int, choices=[
        (1, 'Олимпиады'),
        (2, 'Наука'),
        (3, 'Творчество'),
        (4, 'Спорт'),
        (5, 'Волонтерство'),
        (6, 'Академические'),
    ])
    predmet = SelectField('Предмет', coerce=int, choices=[
        (1, 'Математика'),
        (2, 'Информатика'),
        (3, 'Физика'),
        (4, 'Биология'),
        (5, 'Астрономия'),
        (6, 'История'),
        (7, 'География'),
        (8, 'Обществознание'),
        (9, 'Спорт'),
        (10, 'Русский язык'),
        (11, 'Литература'),
        (12, 'Иностранные языки'),
        (13, 'Химия'),
        (14, 'Без предмета'),
    ])

    result = SelectField('Результат', coerce=int, choices=[
        (0, 'Победитель'),
        (1, 'Призер'),
        (2, 'Участник'),
    ])
    categories = SelectField('Уровень', coerce=int, choices=[
        (0, 'Всероссийский'),
        (1, 'Региональный'),
        (2, 'Городской'),
        (3, 'Школьный'),
    ])
    ssilka = StringField("Ссылка на мероприятие (если есть)")
    submit = SubmitField('Добавить')
