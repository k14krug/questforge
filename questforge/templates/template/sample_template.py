from questforge.models.template import Template
from questforge.extensions import db
from questforge.models.user import User

def create_sample_template(user: User):
    """Creates a sample template with a question flow for testing."""

    question_flow = {
        "questions": [
            {
                "key": "protagonist_name",
                "text": "What is the protagonist's name?",
                "type": "text",
                "required": True,
                "options": []
            },
            {
                "key": "difficulty",
                "text": "Choose the difficulty level:",
                "type": "select",
                "required": True,
                "options": ["easy", "medium", "hard"]
            },
            {
                "key": "enable_magic",
                "text": "Enable magic in the game?",
                "type": "checkbox",
                "required": False,
                "options": []
            },
            {
                "key": "backstory",
                "text": "Provide a brief backstory for the protagonist:",
                "type": "textarea",
                "required": True,
                "options": []
            },
            {
                "key": "starting_location_number",
                "text": "Enter a number for the starting location:",
                "type": "number",
                "required": True,
                "options": []
            }
        ]
    }

    template = Template(
        name="Test Template with Validation",
        description="A template for testing question flow validation.",
        created_by=user.id,
        category="Test",
        question_flow=question_flow,
        ai_service_endpoint="http://localhost:5000/ai"  # Replace with your AI service endpoint
    )

    db.session.add(template)
    db.session.commit()

    return template

if __name__ == '__main__':
    # This is just an example and won't work directly without a Flask app context
    # You'd typically call this from within a Flask shell or route
    from questforge.extensions import db
    from questforge import create_app
    app = create_app()
    with app.app_context():
        # Create a default user if one doesn't exist
        user = User.query.filter_by(username='testuser').first()
        if not user:
            print("Creating default user: testuser")
            user = User(username='testuser', email='test@example.com', password='password')
            db.session.add(user)
            db.session.commit()
        
        template = create_sample_template(user)
        print(f"Created template: {template.name} with id {template.id}")
