from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, ForeignKey('templates.id'))
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, ForeignKey('users.id'))
    status = db.Column(db.String(20), default='active')
    
    template = relationship('Template', backref='games')
    creator = relationship('User', backref='created_games')
    campaign_structure = relationship('CampaignStructure', back_populates='game', uselist=False)
    game_states = relationship('GameState', back_populates='game')
    
    def __init__(self, name, template_id, created_by):
        self.name = name
        self.template_id = template_id
        self.created_by = created_by
        
    def __repr__(self):
        return f'<Game {self.name}>'
