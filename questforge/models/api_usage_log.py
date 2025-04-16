from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, Numeric

class ApiUsageLog(db.Model):
    __tablename__ = 'api_usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    prompt_tokens = db.Column(db.Integer, nullable=False)
    completion_tokens = db.Column(db.Integer, nullable=False)
    total_tokens = db.Column(db.Integer, nullable=False)
    # Using Numeric for cost to handle potential decimal values accurately
    # Precision and scale can be adjusted as needed (e.g., 10 total digits, 6 after decimal)
    cost = db.Column(db.Numeric(10, 6), nullable=True) 

    # Relationship to Game (optional, but can be useful)
    game = db.relationship('Game', backref=db.backref('api_usage_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<ApiUsageLog id={self.id} game_id={self.game_id} model={self.model_name} tokens={self.total_tokens} cost={self.cost}>'
