from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class Template(db.Model):
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, ForeignKey('users.id'))
    category = db.Column(db.String(50))
    question_flow = db.Column(db.JSON)
    default_rules = db.Column(db.JSON)
    version = db.Column(db.String(20), default='1.0.0')
    
    creator = relationship('User', backref='created_templates')
    
    def __init__(self, name, description, created_by, category=None, question_flow=None, default_rules=None, version='1.0.0'):
        self.name = name
        self.description = description
        self.created_by = created_by
        self.category = category
        self.question_flow = question_flow
        self.default_rules = default_rules
        self.version = version
        
    def __repr__(self):
        return f'<Template {self.name}>'
