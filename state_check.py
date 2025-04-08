from flask import Flask
from questforge.models import Game, GameState
from questforge.extensions import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/kkrug/projects/questforge/instance/questforge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    g = Game.query.first()
    print(f'Game exists: {bool(g)}')
    if g:
        s = GameState.query.filter_by(game_id=g.id).first()
        print(f'State exists: {bool(s)}')
        print(f'State data: {s.state_data if s else None}')
    else:
        print('No game records found')