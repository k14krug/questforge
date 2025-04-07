from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, Text
import sqlalchemy as sa
import json

class JSONEncodedDict(TypeDecorator):
    """Custom JSON type to handle JSON fields in SQLite."""
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

class GameState(db.Model):
    __tablename__ = 'game_states'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'))
    current_location = db.Column(db.String(100), nullable=True)
    completed_objectives = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        default=list
    )
    discovered_locations = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        default=list
    )
    encountered_characters = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        default=list
    )
    completed_plot_points = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        default=list
    )
    player_decisions = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        default=list
    )
    state_data = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'),
        nullable=False
    )
    current_branch = db.Column(db.String(50), default='main')
    campaign_complete = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    game = db.relationship('Game', back_populates='game_states')
    campaign = db.relationship('Campaign', back_populates='game_states')
    
    def __init__(self, game_id, campaign_id, state_data=None):
        self.game_id = game_id
        self.campaign_id = campaign_id
        self.state_data = state_data or {
            'current_location': None,
            'completed_objectives': [],
            'discovered_locations': [],
            'encountered_characters': [],
            'completed_plot_points': [],
            'player_decisions': [],
            'current_branch': 'main',
            'campaign_complete': False
        }
        
    def __repr__(self):
        return f'<GameState {self.id}>'
