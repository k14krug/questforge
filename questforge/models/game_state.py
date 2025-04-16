from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, Text
import sqlalchemy as sa
import json
from sqlalchemy.dialects.sqlite import JSON # Import JSON specifically for SQLite if needed

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
    """Tracks live campaign state according to questforge-spec.md v1.2
    Attributes:
        state_data (JSON): Main state storage containing:
            - current_location (str)
            - completed_objectives (list)
            - discovered_locations (list)  
            - encountered_characters (list)
            - completed_plot_points (list)
            - player_decisions (list)
            - current_branch (str)
            - campaign_complete (bool)
    Relationships:
        - game: Parent Game record
        - campaign: Associated Campaign template
    Spec Reference: Section 4.3 (Campaign State Management)
    Last Updated: 2025-07-04"""
    __tablename__ = 'game_states'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False) # Ensure game_id is not nullable
    # Removed campaign_id
    current_location = db.Column(db.String(100), nullable=True) # This might belong in state_data?
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
    game_log = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'), 
        default=list, 
        nullable=False
    )
    available_actions = db.Column(
        sa.JSON().with_variant(JSONEncodedDict(), 'sqlite'), 
        default=list, 
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to the Game
    game = db.relationship('Game', back_populates='game_states')
    # Removed campaign relationship

    def __init__(self, game_id, state_data=None): # Removed campaign_id parameter
        self.game_id = game_id
        # self.campaign_id = campaign_id # Removed
        self.state_data = state_data or {
            'current_location': None,
            'completed_objectives': [],
            'discovered_locations': [],
            'encountered_characters': [],
            'completed_plot_points': [],
            'player_decisions': [],
            'current_branch': 'main',
            'campaign_complete': False,
            'game_log': [], # Add to default state data if needed, though DB default is usually sufficient
            'available_actions': [] # Add to default state data if needed
        }
        # Initialize DB columns directly if not relying solely on state_data
        self.game_log = []
        self.available_actions = []
        
    def __repr__(self):
        return f'<GameState {self.id}>'
