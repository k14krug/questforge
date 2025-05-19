from datetime import datetime, timezone
from questforge.extensions import db
from sqlalchemy import ForeignKey, Table, Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship

# Association object for the many-to-many relationship between Game and User
class GamePlayer(db.Model):
    __tablename__ = 'game_players'
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    character_description = db.Column(db.Text, nullable=True) # Added field for player character description
    character_name = db.Column(db.String(100), nullable=True) # Optional player-provided or AI-generated name
    is_ready = db.Column(db.Boolean, default=False, nullable=False)
    join_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships to access Game and User objects directly from GamePlayer
    game = relationship("Game", back_populates="player_associations")
    user = relationship("User", back_populates="game_associations")

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, ForeignKey('templates.id'))
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, ForeignKey('users.id'))
    status = db.Column(db.String(20), default='active')
    creator_customizations = db.Column(db.JSON, nullable=True) # Creator-provided additions/changes
    template_overrides = db.Column(db.JSON, nullable=True) # Creator-provided overrides for base template fields
    current_difficulty = db.Column(db.String(20), default='Normal', nullable=False)

    template = relationship('Template', backref='games')
    creator = relationship('User', foreign_keys=[created_by]) # Specify foreign key for creator
    campaign = relationship('Campaign', back_populates='game', uselist=False)
    game_states = relationship('GameState', back_populates='game', order_by='desc(GameState.created_at)')

    # Use the association object for the players relationship
    player_associations = relationship('GamePlayer', back_populates='game', cascade="all, delete-orphan")

    # Helper property to easily get the list of User objects
    @property
    def players(self):
        return [assoc.user for assoc in self.player_associations]

    def __init__(self, name, template_id, created_by, difficulty='Normal'):
        self.name = name
        self.template_id = template_id
        self.created_by = created_by
        self.current_difficulty = difficulty
        
    def __repr__(self):
        return f'<Game {self.name}>'

    def to_dict(self):
        """Convert game to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'template_id': self.template_id,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'status': self.status,
            'state': self.campaign.current_state if self.campaign else None
        }

    def update_state(self, state_data):
        """Update game state"""
        if not self.campaign:
            raise ValueError("Game has no associated campaign")
        self.campaign.update_state(state_data)

    def process_action(self, player_id, action, payload):
        """Process player action and return result"""
        if not self.campaign:
            raise ValueError("Game has no associated campaign")
        return self.campaign.process_action(player_id, action, payload)
