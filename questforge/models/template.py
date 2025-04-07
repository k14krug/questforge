from datetime import datetime
from questforge.extensions import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import requests
import json
from typing import Optional, Dict, Any
from time import sleep

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
    ai_service_endpoint = db.Column(db.String(255))
    ai_last_response = db.Column(db.JSON)
    ai_last_updated = db.Column(db.DateTime)
    ai_retry_count = db.Column(db.Integer, default=0)
    ai_max_retries = db.Column(db.Integer, default=3)
    ai_retry_delay = db.Column(db.Integer, default=5)  # seconds
    initial_state = db.Column(db.JSON, nullable=False, default={
        'campaign_data': {},
        'objectives': [],
        'conclusion_conditions': [],
        'key_locations': [],
        'key_characters': [],
        'major_plot_points': [],
        'possible_branches': []
    })
    
    creator = relationship('User', backref='created_templates')
    
    def __init__(self, name, description, created_by, category=None, question_flow=None, 
                 default_rules=None, version='1.0.0', ai_service_endpoint=None):
        self.name = name
        self.description = description
        self.created_by = created_by
        self.category = category
        self.question_flow = question_flow
        self.default_rules = default_rules
        self.version = version
        self.ai_service_endpoint = ai_service_endpoint
        
    def __repr__(self):
        return f'<Template {self.name}>'

    def validate_question_flow(self) -> bool:
        """Validate the structure of the question flow (expects a dict with a 'questions' key)"""
        if not isinstance(self.question_flow, dict) or 'questions' not in self.question_flow:
            print("Error: Question flow is not a dictionary or missing 'questions' key.")
            return False

        if not isinstance(self.question_flow['questions'], list):
            print("Error: Question flow's 'questions' is not a list.")
            return False

        required_fields = ['key', 'text', 'type', 'options']
        for question in self.question_flow['questions']:
            if not all(field in question for field in required_fields):
                print(f"Error: Question {question} is missing required fields.")
                return False

            if not isinstance(question['text'], str):
                print(f"Error: Question text is not a string: {question['text']}")
                return False
            if not isinstance(question['type'], str):
                print(f"Error: Question type is not a string: {question['type']}")
                return False
            if not isinstance(question['options'], list):
                print(f"Error: Question options are not a list: {question['options']}")
                return False

        return True

    # TODO: Review if this method is still needed given the central ai_service.py
    # def generate_ai_content(self, prompt: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    #     """Generate content using the AI service with retry logic"""
    #     if not self.ai_service_endpoint:
    #         raise ValueError("AI service endpoint not configured")
    #
    #     payload = {
    #         "prompt": prompt,
    #         "parameters": parameters or {},
    #         "template_id": self.id
    #     }
    #
    #     for attempt in range(self.ai_max_retries + 1):
    #         try:
    #             response = requests.post(
    #                 self.ai_service_endpoint,
    #                 json=payload,
    #                 headers={'Content-Type': 'application/json'},
    #                 timeout=30
    #             )
    #             response.raise_for_status()
    #
    #             result = response.json()
    #             self.ai_last_response = result
    #             self.ai_last_updated = datetime.utcnow()
    #             self.ai_retry_count = 0
    #             db.session.add(self)
    #             return result
    #
    #         except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
    #             if attempt == self.ai_max_retries:
    #                 raise RuntimeError(f"AI service failed after {self.ai_max_retries} attempts: {str(e)}")
    #
    #             self.ai_retry_count += 1
    #             db.session.add(self)
    #             sleep(self.ai_retry_delay)

    def validate_ai_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate the structure of the AI response specifically for campaign generation.
        Checks for required keys and basic types.
        """
        required_fields = ['initial_description', 'initial_state', 'goals']
        if not isinstance(response, dict):
            print("Error: AI response is not a dictionary.")
            return False

        missing_fields = [field for field in required_fields if field not in response]
        if missing_fields:
            print(f"Error: AI response missing required fields: {missing_fields}")
            return False

        if not isinstance(response['initial_description'], str):
            print("Error: AI response 'initial_description' is not a string.")
            return False
        if not isinstance(response['initial_state'], dict):
            print("Error: AI response 'initial_state' is not a dictionary.")
            return False
        if not isinstance(response['goals'], list):
            print("Error: AI response 'goals' is not a list.")
            return False

        # Optional: Check structure within initial_state
        if 'location' not in response['initial_state'] or not isinstance(response['initial_state']['location'], str):
             print("Warning: AI response 'initial_state' is missing 'location' key or it's not a string.")
             # Decide if this should be a hard failure (return False) or just a warning
             # For now, let's allow it but print a warning.

        # Optional: Check structure for key_npcs if present
        if 'key_npcs' in response and not isinstance(response['key_npcs'], list):
            print("Warning: AI response 'key_npcs' is present but not a list.")
            # Allow this for now

        return True
