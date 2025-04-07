from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from ..models.user import User
from .forms import GameForm

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('main/home.html')

@main_bp.route('/about')
def about():
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html')

@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html')
