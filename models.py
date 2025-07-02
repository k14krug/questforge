from database import db
from datetime import datetime
from sqlalchemy.dialects.mysql import JSON # Import JSON for MySQL specific JSON type
import uuid

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    character_backstories = db.Column(JSON, nullable=False, default=lambda: []) # Store as JSON array of strings

    # Relationships
    templates = db.relationship('Template', backref='creator', lazy=True)
    games_created = db.relationship('Game', backref='creator', lazy=True, foreign_keys='Game.creator_user_id')
    game_players = db.relationship('GamePlayer', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "character_backstories": self.character_backstories
        }

class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    genre = db.Column(db.Text, nullable=False)
    core_conflict = db.Column(db.Text, nullable=False)
    world_description = db.Column(db.Text, nullable=False)
    ai_gm_persona = db.Column(db.Text, nullable=False)
    core_skills = db.Column(JSON, nullable=False) # JSON array of core skills

    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    games = db.relationship('Game', backref='template', lazy=True)

    def __repr__(self):
        return f"<Template {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "genre": self.genre,
            "core_conflict": self.core_conflict,
            "world_description": self.world_description,
            "ai_gm_persona": self.ai_gm_persona,
            "core_skills": self.core_skills,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat()
        }

class GameState(db.Model):
    __tablename__ = 'game_states'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    current_player_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    turn_number = db.Column(db.Integer, nullable=False, default=1)
    current_story_summary = db.Column(db.Text, nullable=True)
    current_location = db.Column(db.Text, nullable=True)
    active_npcs = db.Column(JSON, nullable=True)
    player_states = db.Column(JSON, nullable=True)
    game_log = db.Column(JSON, nullable=False)
    completed_objectives = db.Column(JSON, nullable=True)
    discovered_lore_items = db.Column(JSON, nullable=True)
    last_ai_exchange = db.Column(JSON, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    game = db.relationship('Game', back_populates='game_states', foreign_keys='GameState.game_id')
    current_game = db.relationship('Game', back_populates='current_game_state', foreign_keys='Game.current_game_state_id', uselist=False)

    def __repr__(self):
        return f"<GameState {self.id} for Game {self.game_id} Turn {self.turn_number}>"

    def to_dict(self):
        return {
            "id": self.id,
            "game_id": self.game_id,
            "current_player_id": self.current_player_id,
            "turn_number": self.turn_number,
            "current_story_summary": self.current_story_summary,
            "current_location": self.current_location,
            "active_npcs": self.active_npcs,
            "player_states": self.player_states,
            "game_log": self.game_log,
            "completed_objectives": self.completed_objectives,
            "discovered_lore_items": self.discovered_lore_items,
            "last_ai_exchange": self.last_ai_exchange,
            "updated_at": self.updated_at.isoformat()
        }

class GamePlayer(db.Model):
    __tablename__ = 'game_players'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    character_name = db.Column(db.Text, nullable=False)
    character_description = db.Column(db.Text, nullable=True)
    ai_generated_backstory = db.Column(db.Text, nullable=True)
    character_portrait_url = db.Column(db.Text, nullable=True)
    ready_status = db.Column(db.Boolean, nullable=False, default=False)
    character_sheet = db.Column(JSON, nullable=False)
    joined_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<GamePlayer {self.character_name} in Game {self.game_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "game_id": self.game_id,
            "user_id": self.user_id,
            "user": self.user.to_dict() if self.user else None,
            "character_name": self.character_name,
            "character_description": self.character_description,
            "ai_generated_backstory": self.ai_generated_backstory,
            "character_portrait_url": self.character_portrait_url,
            "ready_status": self.ready_status,
            "character_sheet": self.character_sheet,
            "joined_at": self.joined_at.isoformat()
        }

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_name = db.Column(db.Text, nullable=False) # Added game_name field
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'), nullable=False)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_game_state_id = db.Column(db.Integer, db.ForeignKey('game_states.id'), nullable=True)
    settings = db.Column(JSON, nullable=False)
    campaign_charter = db.Column(JSON, nullable=False)
    cumulative_cost = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    game_players = db.relationship('GamePlayer', backref='game', lazy='joined')
    # Relationship for all game states belonging to this game
    game_states = db.relationship('GameState', foreign_keys='GameState.game_id', lazy=True, back_populates='game')
    # Relationship for the current game state, explicitly linking via current_game_state_id
    current_game_state = db.relationship('GameState', foreign_keys='Game.current_game_state_id', lazy=True, post_update=True, uselist=False, back_populates='current_game')

    def __repr__(self):
        return f"<Game {self.id} from Template {self.template_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "game_name": self.game_name, # Include game_name in to_dict
            "template_id": self.template_id,
            "creator_user_id": self.creator_user_id,
            "current_game_state_id": self.current_game_state_id,
            "settings": self.settings,
            "campaign_charter": self.campaign_charter,
            "cumulative_cost": self.cumulative_cost,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "game_players": [player.to_dict() for player in self.game_players]
        }
