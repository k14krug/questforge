# Template Model Documentation

## Overview
The Template model (`questforge/models/template.py`) provides the foundation for game template management in QuestForge. Templates define reusable structures for game creation and AI-generated content.

## Model Structure
```python
class Template(db.Model):
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, ForeignKey('users.id'))
    category = db.Column(db.String(50))
    question_flow = db.Column(db.JSON)  # Defines the setup questions for this template
    default_rules = db.Column(db.JSON)  # Template-specific game rules
    version = db.Column(db.String(20), default='1.0.0')
    ai_service_endpoint = db.Column(db.String(255))  # Endpoint for AI service
    ai_last_response = db.Column(db.JSON)  # Last response from AI service
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
```

## Key Relationships
- Many-to-One with User (creator via created_by)
- One-to-Many with Game (instances)

## Core Methods
1. `generate_ai_content(prompt, parameters)` - Generates content using the AI service with retry logic
2. `validate_ai_response(response)` - Validates the structure of AI responses

## Usage Patterns
1. **Template Creation**:
   - Accessed via `/templates/create`
   - Uses Flask-WTF forms for input
   - JSON structures validated before save

2. **Template Editing**:
   - Accessed via `/templates/edit/<id>`
   - Maintains version history
   - Validates changes before applying

3. **Game Instantiation**:
   - Selected during game creation
   - Provides initial game structure via initial_state
   - Defines question flow for setup

## AI Integration
- Templates guide AI-generated content through:
  - question_flow (setup questions)
  - default_rules (constraints)
  - initial_state (structure)
- Uses retry logic (max_retries, retry_delay)
- Stores last response for debugging

## Best Practices
1. Keep question_flow JSON well-structured
2. Use descriptive names and documentation
3. Validate all template operations
4. Maintain backward compatibility
5. Document expected AI response format

## Related Documentation
- See [game_creation_process.md](./game_creation_process.md) for how templates are used in game creation
