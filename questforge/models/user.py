from questforge.extensions.database import db
from questforge.extensions.bcrypt import bcrypt
from flask_login import UserMixin
from sqlalchemy.orm import relationship

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship to the GamePlayer association object
    game_associations = relationship("GamePlayer", back_populates="user", cascade="all, delete-orphan")

    # Helper property to easily get the list of Game objects the user joined
    @property
    def games_joined(self):
        return [assoc.game for assoc in self.game_associations]

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
