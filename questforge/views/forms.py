from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from questforge.models.user import User
from questforge.models.template import Template
from questforge.extensions import db
import json # Import json for validation

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

# Removed unused validate_question_flow function and json import

class TemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    description = TextAreaField('Description (Optional)')
    category = StringField('Category (Optional)')

    # New High-Level Guidance Fields
    genre = SelectField('Genre', 
                        choices=[
                            ('', '-- Select Genre --'), 
                            ('Fantasy', 'Fantasy'), 
                            ('Sci-Fi', 'Sci-Fi'), 
                            ('Mystery', 'Mystery'), 
                            ('Horror', 'Horror'), 
                            ('Adventure', 'Adventure')
                        ], 
                        validators=[DataRequired(message="Please select a genre.")])
    core_conflict = TextAreaField('Core Conflict / Goal', 
                                  validators=[DataRequired(message="Please describe the core conflict or goal.")],
                                  render_kw={"placeholder": "e.g., Overthrow the evil king, Find the lost artifact, Solve the murder mystery"})
    theme = StringField('Theme (Optional)', render_kw={"placeholder": "e.g., Exploration, Intrigue, Survival"})
    desired_tone = SelectField('Desired Tone (Optional)', 
                               choices=[
                                   ('', '-- Select Tone --'), 
                                   ('Serious', 'Serious'), 
                                   ('Humorous', 'Humorous'), 
                                   ('Gritty', 'Gritty'), 
                                   ('Epic', 'Epic'), 
                                   ('Lighthearted', 'Lighthearted')
                               ])
    world_description = TextAreaField('World Description (Optional)', render_kw={"placeholder": "Brief notes on the setting, magic system, key factions, etc."})
    scene_suggestions = TextAreaField('Scene Suggestions (Optional)', render_kw={"placeholder": "Ideas for specific scenes, encounters, or locations (e.g., A chase through the market, A tense negotiation, A puzzle room)"})
    player_character_guidance = TextAreaField('Player Character Guidance (Optional)', render_kw={"placeholder": "Suggestions or restrictions for players creating characters (e.g., 'All characters should be members of the resistance', 'Magic users are rare')"})
    difficulty = SelectField('Difficulty (Optional)', 
                             choices=[
                                 ('', '-- Select Difficulty --'), 
                                 ('Easy', 'Easy'), 
                                 ('Medium', 'Medium'), 
                                 ('Hard', 'Hard')
                             ])
    estimated_length = SelectField('Estimated Length (Optional)', 
                                   choices=[
                                       ('', '-- Select Length --'), 
                                       ('Short', 'Short (1-2 sessions)'), 
                                       ('Medium', 'Medium (3-5 sessions)'), 
                                       ('Long', 'Long (6+ sessions)')
                                   ])

    # Kept Fields
    ai_service_endpoint = StringField('AI Service Endpoint (Optional)')
    
    submit = SubmitField('Save Template')

    def validate_questions(self, field):
        """Validate that the questions field contains valid JSON."""
        if field.data: # Only validate if data is provided
            try:
                parsed_json = json.loads(field.data)
                if not isinstance(parsed_json, list):
                     raise ValidationError('Questions must be a valid JSON list.')
                # Optional: Add more specific validation for the structure of each object in the list
                for item in parsed_json:
                    if not isinstance(item, dict) or not all(k in item for k in ['key', 'text']):
                         raise ValidationError('Each question object must be a dictionary with at least "key" and "text" fields.')
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format for questions.')
            except Exception as e: # Catch other potential errors during validation
                 raise ValidationError(f'Error validating questions JSON: {e}')
