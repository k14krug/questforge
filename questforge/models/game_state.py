from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
# Removed TypeDecorator, Text imports as JSONEncodedDict is removed
import sqlalchemy as sa
# Removed json import as it's implicitly handled by sa.JSON
# Removed dialect-specific JSON import

# Removed JSONEncodedDict class definition

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
    # Removed redundant current_location column - location is stored within state_data JSON
    
    # Using standard sa.JSON, assuming backend DB supports native JSON
    completed_objectives = db.Column(sa.JSON, default=list)
    discovered_locations = db.Column(sa.JSON, default=list)
    encountered_characters = db.Column(sa.JSON, default=list)
    completed_plot_points = db.Column(sa.JSON, default=list)
    player_decisions = db.Column(sa.JSON, default=list)
    state_data = db.Column(sa.JSON, nullable=False)
    
    current_branch = db.Column(db.String(50), default='main')
    campaign_complete = db.Column(db.Boolean, default=False)
    
    # Using standard sa.JSON
    game_log = db.Column(sa.JSON, default=list, nullable=False)
    available_actions = db.Column(sa.JSON, default=list, nullable=False)
    visited_locations = db.Column(sa.JSON, default=list, nullable=False) # Added visited_locations field
    
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
            'turns_since_plot_progress': 0, # Added for narrative guidance
            # Removed game_log and available_actions from here, rely on DB default
        }
        # Initialize DB columns directly if not relying solely on state_data
        # Rely on DB defaults for JSON lists now
        # self.game_log = [] 
        # self.available_actions = []
        
    def __repr__(self):
        return f'<GameState {self.id}>'
