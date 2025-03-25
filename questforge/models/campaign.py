from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class CampaignStructure(db.Model):
    __tablename__ = 'campaign_structures'
    
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
    
    game = db.relationship('Game', back_populates='campaign_structure')
    template = db.relationship('Template', backref='campaign_structures')
    game_states = db.relationship('GameState', back_populates='campaign_structure')
    
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
        return f'<CampaignStructure {self.id}>'
