from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey, Text, String, Integer, DateTime, JSON # Added Text, String, Integer, DateTime, JSON explicitly
from sqlalchemy.orm import relationship
import requests
import json
from typing import Optional, Dict, Any
from time import sleep

class Template(db.Model):
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text) # Optional: General description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, ForeignKey('users.id'))
    category = db.Column(db.String(50)) # Optional: For organization

    # High-level Guidance Fields (New)
    genre = db.Column(db.String(50), nullable=False) # Required: e.g., Fantasy, Sci-Fi
    core_conflict = db.Column(db.Text, nullable=False) # Required: Short description of main goal/problem
    theme = db.Column(db.Text) # Optional: e.g., Exploration, Mystery
    desired_tone = db.Column(db.String(50)) # Optional: e.g., Humorous, Grim
    world_description = db.Column(db.Text) # Optional: Freeform notes on world, magic, tech
    scene_suggestions = db.Column(db.Text) # Optional: Ideas for scene types/encounters
    player_character_guidance = db.Column(db.Text) # Optional: Notes for players creating characters
    difficulty = db.Column(db.String(20)) # Optional: e.g., Easy, Medium, Hard
    estimated_length = db.Column(db.String(20)) # Optional: e.g., Short, Medium, Long
    default_rules = db.Column(db.JSON) # New: Default rules for campaign generation

    # AI Interaction Fields (Kept)
    version = db.Column(db.String(20), default='1.0.0') # Metadata
    ai_service_endpoint = db.Column(db.String(255)) # Endpoint for AI service
    ai_last_response = db.Column(db.JSON) # For debugging/logging
    ai_last_updated = db.Column(db.DateTime) # For debugging/logging
    ai_retry_count = db.Column(db.Integer, default=0) # For debugging/logging
    ai_max_retries = db.Column(db.Integer, default=3) # Configurable retry logic
    ai_retry_delay = db.Column(db.Integer, default=5) # Configurable retry logic (seconds)

    # Metadata (Kept) - Note: version moved up earlier
    
    creator = relationship('User', backref='created_templates')

    # Updated __init__ to reflect new fields
    def __init__(self, name, description, created_by, category=None, genre=None, core_conflict=None,
                 theme=None, desired_tone=None, world_description=None, scene_suggestions=None,
                 player_character_guidance=None, difficulty=None, estimated_length=None,
                 default_rules=None, # Added default_rules
                 version='1.0.0', ai_service_endpoint=None, **kwargs): # Added **kwargs for flexibility
        self.name = name
        self.description = description
        self.created_by = created_by
        self.category = category
        self.genre = genre
        self.core_conflict = core_conflict
        self.theme = theme
        self.desired_tone = desired_tone
        self.world_description = world_description
        self.scene_suggestions = scene_suggestions
        self.player_character_guidance = player_character_guidance
        self.difficulty = difficulty
        self.estimated_length = estimated_length
        self.default_rules = default_rules # Added default_rules assignment
        self.version = version
        self.ai_service_endpoint = ai_service_endpoint
        # Handle potential extra arguments if needed, or remove **kwargs if strict matching is desired
        super().__init__(**kwargs) 
        
    def __repr__(self):
        return f'<Template {self.name}>'

    # Removed validate_question_flow method as question_flow is removed

    # TODO: Review if this method is still needed given the central ai_service.py
    # def generate_ai_content(self, prompt: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    #     """Generate content using the AI service with retry logic"""
    #     ... (Original implementation commented out for now) ...

    def validate_ai_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate the structure of the AI response specifically for campaign generation.
        Checks for required keys and basic types.
        NOTE: This validation might need significant updates based on the new AI prompt
              and expected output structure for the full campaign generation.
        """
        # Placeholder - Current validation checks for fields that might change
        required_fields = ['initial_description', 'initial_state', 'goals'] 
        # ^^^ These fields are likely to change with the new prompt structure
        
        if not isinstance(response, dict):
            print("Error: AI response is not a dictionary.")
            return False

        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            print(f"Warning: AI response missing potentially outdated required fields: {missing_fields}")
            # Consider if this should be a failure later

        # Example checks (adjust based on actual new structure)
        if 'campaign_summary' not in response or not isinstance(response.get('campaign_summary'), str):
             print("Warning: AI response missing expected 'campaign_summary' or it's not a string.")
        
        if 'initial_scene' not in response or not isinstance(response.get('initial_scene'), dict):
             print("Warning: AI response missing expected 'initial_scene' or it's not a dictionary.")

        # Add more checks based on the revised prompt's expected output (locations, characters, plot points etc.)

        return True # Return True for now, needs refinement in Phase 3
