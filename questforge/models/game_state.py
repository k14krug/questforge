from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, Text
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
    campaign_structure_id = db.Column(db.Integer, db.ForeignKey('campaign_structures.id'))
    current_location = db.Column(db.String(100), nullable=True)
    completed_objectives = db.Column(JSONEncodedDict, default=list)
    discovered_locations = db.Column(JSONEncodedDict, default=list)
    encountered_characters = db.Column(JSONEncodedDict, default=list)
    completed_plot_points = db.Column(JSONEncodedDict, default=list)
    current_branch = db.Column(db.String(50), default='main')
    player_decisions = db.Column(JSONEncodedDict, default=list)
    campaign_complete = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    game = db.relationship('Game', back_populates='game_states')
    campaign_structure = db.relationship('CampaignStructure', back_populates='game_states')
    
    def __init__(self, game_id, campaign_structure_id):
        self.game_id = game_id
        self.campaign_structure_id = campaign_structure_id
        
    def __repr__(self):
        return f'<GameState {self.id}>'