from flask import Blueprint, render_template
from flask_login import login_required
from ..models.user import User

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def home():
    return render_template('main/home.html')


