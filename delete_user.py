from flask import Flask, render_template, redirect, request, abort, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms.user import RegisterForm, LoginForm, ChangePasswordForm, ChangeIcon, ChangePasswordEmailForm, CodeForm
from forms.portfolio import PortfolioForm
from forms.profil import ProfilForm
from data.users import User
from data.portfolio import Portfolio
from data.category import Category
from data.portfolio_TRUE import Portfolio_TRUE
from data import db_session
import smtplib
from email.mime.text import MIMEText
import random
import os
import secrets
from PIL import Image
from flask import current_app
from flask_restful import abort, Api
# from data.APIresource import DostijeniaResource, UserResource
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

db_sess = db_session.create_session()

user = db_sess.query(User).filter(User.id == 3).first()
db_sess.delete(user)
db_sess.commit()
