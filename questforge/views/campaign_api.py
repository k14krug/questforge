from flask import Blueprint, request, jsonify, url_for, redirect
from flask_login import login_required, current_user
from ..models.template import Template
from ..models.game import Game, GamePlayer # Import GamePlayer
from ..extensions import db 

campaign_api_bp = Blueprint('campaign_api', __name__)

# Removed obsolete get_template_questions_for_frontend route as question_flow is removed

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
    Creates a new game record and the creator's player association.
    Campaign generation is now handled later via SocketIO in the lobby.
    """
    print("--- DEBUG: campaign_api_bp create_game_api route registered ---")
    data = request.get_json()

    print(f"--- DEBUG: Incoming request data: {data} ---")
    # Simplified validation: Only need template_id and optional name
    if not data or 'template_id' not in data:
        return jsonify({'error': 'Missing template_id'}), 400

    template_id = data['template_id']
    game_name = data.get('name', 'New Game') # Optional game name

    template = db.session.get(Template, template_id)
    if not template:
        return jsonify({'error': 'Template not found'}), 404

    # Removed validation for user_inputs and question_flow

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
        db.session.flush() # Flush to get game.id before creating association

        print(f"--- DEBUG: Preparing to create GamePlayer association for game_id={game.id}, user_id={current_user.id} ---")
        # 2. Create the association object to link the creator (current_user) to the game
        # Mark creator as ready by default? Or handle readiness purely in lobby? Let's default to False.
        game_player_assoc = GamePlayer(game_id=game.id, user_id=current_user.id, is_ready=False) 
        db.session.add(game_player_assoc)
        print(f"--- DEBUG: Successfully staged GamePlayer association for game_id={game.id}, user_id={current_user.id} ---")

        # Removed call to create_campaign_service

        # 3. Commit the transaction (only Game and GamePlayer)
        db.session.commit()
        print(f"--- API: Successfully committed Game and GamePlayer for game {game.id} ---")
        print(f"--- API: Finished create_game route for game {game.id} ---")

        # Removed socketio.emit('game_created', ...)

        # 4. Return success response with redirect URL to lobby
        return jsonify({
            'data': { # Keep basic game info in response
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
