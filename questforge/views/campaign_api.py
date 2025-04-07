from flask import Blueprint, request, jsonify, url_for, redirect
from flask_login import login_required, current_user
from ..models.template import Template
from ..models.game import Game, GamePlayer # Import GamePlayer
from ..models.campaign import Campaign
from ..extensions import db, socketio
from ..services.campaign_service import create_campaign as create_campaign_service # Alias import
import json

campaign_api_bp = Blueprint('campaign_api', __name__)

@campaign_api_bp.route('/api/templates/<int:template_id>/questions', methods=['GET'])
@login_required
def get_template_questions_for_frontend(template_id):
    """Get the questions for a template"""
    template = Template.query.get_or_404(template_id)
    # Transform question_flow to match frontend expectations
    questions = []
    try:
        if template.question_flow and isinstance(template.question_flow, dict):
            if "questions" in template.question_flow and isinstance(template.question_flow["questions"], list):
                questions = [
                    {
                        'text': q.get('text', 'Question'),
                        'type': q.get('type', 'text'),
                        'key': q.get('key')
                    }
                    for q in template.question_flow["questions"]
                ]
            else:
                questions = [
                    {
                        'text': q.get('prompt', 'Question'),
                        'type': q.get('input_type', 'text'),
                        'key': key
                    }
                    for key, q in template.question_flow.items()
                ]
    except (TypeError, json.JSONDecodeError):
        # Handle cases where question_flow is None or not a valid JSON string
        questions = []
    
    return jsonify({
        'questions': questions,
        'template_name': template.name,
        'template_description': template.description
    })

@campaign_api_bp.route('/api/campaigns/generate', methods=['POST'])
@login_required
def generate_campaign():
    """Generate a new campaign using AI templates"""
    data = request.get_json()
    
    if not data or 'template_id' not in data:
        return jsonify({'error': 'Missing template_id'}), 400
    
    template = Template.query.get(data['template_id'])
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    try:
        # Generate campaign content using template's AI integration
        prompt = data.get('prompt', 'Generate a new campaign')
        parameters = data.get('parameters', {})
        
        ai_response = template.generate_ai_content(prompt, parameters)
        if not template.validate_ai_response(ai_response):
            return jsonify({'error': 'Invalid AI response format'}), 500
            
        # Create new campaign
        campaign = Campaign(
            name=data.get('name', 'New Campaign'),
            description=ai_response['content'].get('description', ''),
            template_id=template.id,
            created_by=current_user.id,
            content=ai_response['content']
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        return jsonify({
            'message': 'Campaign generated successfully',
            'campaign_id': campaign.id,
            'content': campaign.content
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@campaign_api_bp.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
@login_required
def get_campaign(campaign_id):
    """Get a generated campaign"""
    campaign = Campaign.query.get_or_404(campaign_id)
    return jsonify(campaign.to_dict())

@campaign_api_bp.route('/api/campaigns/<int:campaign_id>', methods=['PUT'])
@login_required
def update_campaign(campaign_id):
    """Update a generated campaign"""
    campaign = Campaign.query.get_or_404(campaign_id)
    data = request.get_json()
    
    if 'name' in data:
        campaign.name = data['name']
    if 'description' in data:
        campaign.description = data['description']
    if 'content' in data:
        campaign.content = data['content']
        
    db.session.commit()
    return jsonify({'message': 'Campaign updated successfully'})

@campaign_api_bp.route('/api/games/create', methods=['POST'])
@login_required
def create_game_api():
    """
    Creates a new game record and then generates the associated
    campaign structure and initial game state using the campaign service.
    """
    print("--- DEBUG: campaign_api_bp create_game_api route registered ---")
    data = request.get_json()

    print(f"--- DEBUG: Incoming request data: {data} ---")
    if not data or 'template_id' not in data or 'user_inputs' not in data:
        return jsonify({'error': 'Missing template_id or user_inputs'}), 400

    template_id = data['template_id']
    user_inputs = data['user_inputs']
    game_name = data.get('name', 'New Game') # Optional game name

    if not isinstance(user_inputs, dict):
        return jsonify({'error': 'Invalid format for user_inputs, expected a dictionary'}), 400

    template = db.session.get(Template, template_id)
    if not template:
        return jsonify({'error': 'Template not found'}), 404

    # Validate the question flow structure
    if not template.validate_question_flow():
        return jsonify({'error': 'Invalid question flow structure in template'}), 400

   # Validate user inputs against the template's question_flow
    if template.question_flow and isinstance(template.question_flow, dict) and "questions" in template.question_flow["questions"] and isinstance(template.question_flow["questions"], list):
        for question in template.question_flow["questions"]:
            key = question.get('key')
            if key not in user_inputs:
                return jsonify({'error': f'Missing input for question: {question["text"]}'}), 400

            input_type = question.get('type', 'text')
            if input_type == 'number':
                try:
                    float(user_inputs[key])
                except ValueError:
                    return jsonify({'error': f'Invalid input for question: {question["text"]}, expected a number'}), 400
                # Add more specific validation based on question type
                if input_type == 'select':
                    if 'options' not in question or not isinstance(question['options'], list):
                        return jsonify({'error': f'Invalid options for question: {question["text"]}'}), 400
                    if user_inputs[key] not in question['options']:
                        return jsonify({'error': f'Invalid selection for question: {question["text"]}'}), 400
                elif input_type == 'textarea':
                    if not isinstance(user_inputs[key], str):
                        return jsonify({'error': f'Invalid input for question: {question["text"]}, expected text'}), 400
                elif input_type == 'checkbox':
                    if not isinstance(user_inputs[key], bool):
                        return jsonify({'error': f'Invalid input for question: {question["text"]}, expected true or false'}), 400

    try:
        # 1. Create the Game record
        print(f"--- API: Creating Game object for template {template_id} ---")
        game = Game(
            name=game_name,
            template_id=template.id,
            created_by=current_user.id
            # state field is deprecated/unused now, managed by GameState model
        )
        db.session.add(game)
        # Flush to get game.id before creating association
        db.session.flush()

        print(f"--- DEBUG: Preparing to create GamePlayer association for game_id={game.id}, user_id={current_user.id} ---")
        # Create the association object to link the creator (current_user) to the game
        game_player_assoc = GamePlayer(game_id=game.id, user_id=current_user.id, is_ready=True) # Mark creator as ready?
        db.session.add(game_player_assoc)
        print(f"--- DEBUG: Successfully created GamePlayer association for game_id={game.id}, user_id={current_user.id} ---")
        # No need to flush again here, association will be committed with the rest

        print(f"--- API: Created Game object (ID: {game.id}) and staged creator association (User ID: {current_user.id}) ---")
        print(f"--- API: Calling create_campaign_service for game {game.id} ---")

        # 2. Call Campaign Service to generate Campaign and initial GameState
        print(f"--- API: Before calling create_campaign_service ---")
        campaign = create_campaign_service(
            game_id=game.id,
            template_id=template.id,
            user_inputs=user_inputs
        )
        print(f"--- API: After calling create_campaign_service ---")

        if not campaign:
            # Service function handles logging errors, rollback needed here
            print(f"--- API: Campaign service failed for game {game.id}. Rolling back. ---")
            db.session.rollback()
            return jsonify({'error': 'Failed to generate campaign content. Please try again or contact support.'}), 500

        # 3. Commit the transaction (includes Game, Campaign, GameState)
        db.session.commit()
        print(f"--- API: Successfully committed Game, Campaign, GameState, and GamePlayer for game {game.id} ---")
        print(f"--- API: Finished create_game route for game {game.id} ---")

        # 4. Emit socket event (optional, maybe move to service or specific game logic)
        socketio.emit('game_created', {
            'game_id': game.id,
            'game_name': game.name,
            'created_by': current_user.username # Send username instead of ID?
        })

        return jsonify({
            'data': {
                'created_at': game.created_at.isoformat() if game.created_at else None,
                'created_by': game.created_by,
                'id': game.id,
                'name': game.name,
                'state': None,  # Will be populated by GameState
                'status': 'active', # Ensure status is set correctly
                'template_id': template.id
            },
            'redirect_url': url_for('game.lobby', game_id=game.id),
            'status': 'success'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"--- API: Unexpected error during game creation: {e} ---") # Log the exception
        return jsonify({'error': 'An unexpected error occurred during game creation.'}), 500
