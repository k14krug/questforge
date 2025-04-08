from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    campaign_data = db.Column(db.JSON, nullable=False)
    objectives = db.Column(db.JSON, nullable=False)
    conclusion_conditions = db.Column(db.JSON, nullable=False)
    key_locations = db.Column(db.JSON, nullable=False)
    key_characters = db.Column(db.JSON, nullable=False)
    major_plot_points = db.Column(db.JSON, nullable=False)
    possible_branches = db.Column(db.JSON, nullable=False)
    
    game = db.relationship('Game', back_populates='campaign')
    template = db.relationship('Template', backref='campaign_structures')
    # Removed game_states relationship as it's accessed via game
    
    def __init__(self, game_id, template_id, campaign_data, objectives, 
                 conclusion_conditions, key_locations, key_characters,
                 major_plot_points, possible_branches):
        self.game_id = game_id
        self.template_id = template_id
        self.campaign_data = campaign_data
        self.objectives = objectives
        self.conclusion_conditions = conclusion_conditions
        self.key_locations = key_locations
        self.key_characters = key_characters
        self.major_plot_points = major_plot_points
        self.possible_branches = possible_branches
        
    def __repr__(self):
        return f'<Campaign {self.id}>'

    @property
    def current_state(self):
        """Get current game state from latest GameState record"""
        if not self.game_states:
            return None
        # This property might be incorrect now, as game_states relationship was removed.
        # Access via campaign.game.game_states instead.
        # if not self.game_states:
        #     return None
        # return self.game_states[-1].state_data
        latest_state = GameState.query.filter_by(game_id=self.game_id).order_by(GameState.last_updated.desc()).first()
        return latest_state.state_data if latest_state else None


    # This method seems incorrect - state updates should happen via GameStateService
    # def update_state(self, state_data):
    #     """Update game state by creating new GameState record"""
    #     # This logic is flawed, GameState needs game_id, not campaign_id
    #     # State updates should be handled by GameStateService
    #     pass

    # This method also seems out of place, actions are processed via SocketService/AIService
    # def process_action(self, player_id, action, payload):
    #     """Process player action and return result"""
    #     # Basic implementation - should be expanded based on game rules
    #     # ... (original implementation commented out) ...
    #     pass # Placeholder if needed, or just remove the method definition entirely if preferred
