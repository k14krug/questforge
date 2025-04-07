from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from questforge.models.user import User
from questforge.models.template import Template
from questforge.extensions import db

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                         validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                            validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                            validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class GameForm(FlaskForm):
    name = StringField('Game Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    template = SelectField('Template', coerce=int, choices=[])
    submit = SubmitField('Create Game')

    def __init__(self, *args, **kwargs):
        super(GameForm, self).__init__(*args, **kwargs)
        self.template.choices = [(template.id, template.name) for template in Template.query.all()]

import json

def validate_question_flow(form, field):
    try:
        question_flow = json.loads(field.data)
        template = Template(question_flow=question_flow)
        if not template.validate_question_flow():
            raise ValidationError('Invalid question flow structure.')
    except json.JSONDecodeError:
        raise ValidationError('Invalid JSON format for Question Flow.')

class TemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    category = StringField('Category')
    question_flow = TextAreaField('Question Flow (JSON)', validators=[validate_question_flow])
    default_rules = TextAreaField('Default Rules (JSON)')
    ai_service_endpoint = StringField('AI Service Endpoint')
    
    # Initial State Fields
    campaign_data = TextAreaField('Campaign Data (JSON)')
    objectives = TextAreaField('Objectives (JSON)')
    conclusion_conditions = TextAreaField('Conclusion Conditions (JSON)')
    key_locations = TextAreaField('Key Locations (JSON)')
    key_characters = TextAreaField('Key Characters (JSON)')
    major_plot_points = TextAreaField('Major Plot Points (JSON)')
    possible_branches = TextAreaField('Possible Branches (JSON)')
    
    submit = SubmitField('Save Template')
