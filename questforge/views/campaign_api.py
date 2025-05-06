from flask import Blueprint, request, jsonify, url_for, redirect, current_app
from flask_login import login_required, current_user
from ..models.template import Template
from ..models.game import Game, GamePlayer # Import GamePlayer
from ..extensions import db

# ==============================================================================
# Campaign API Blueprint (`/api`)
# ==============================================================================
# Handles API endpoints primarily related to:
# - Initial Game Creation (`/api/games/create`): Creates the core Game record
#   and player association, saving overrides/customizations. Actual campaign
#   content generation is triggered later from the lobby via SocketIO.
# - Campaign Management (Optional/Future): Could include endpoints for listing,
#   viewing, or potentially managing generated campaign structures if needed.
#   (Currently includes placeholder /api/campaigns/... routes).
# ==============================================================================
campaign_api_bp = Blueprint('campaign_api', __name__, url_prefix='/api')

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

@campaign_api_bp.route('/games/create', methods=['POST']) # Corrected route relative to blueprint prefix
@login_required
def create_game_api():
    """
    API Endpoint: /api/games/create (POST)

    Handles the initial step of game creation triggered by the frontend form.

    1. Receives game name, template ID, template overrides, and creator customizations.
    2. Validates the input (template existence).
    3. Creates a new `Game` record in the database.
    4. Saves the received `template_overrides` and `creator_customizations`
       to the corresponding JSON fields in the new `Game` record.
    5. Creates the `GamePlayer` association record linking the creator (current user)
       to the newly created game.
    6. Commits the `Game` and `GamePlayer` records to the database.
    7. Returns a JSON response containing the URL for the game lobby (`/game/<id>/lobby`),
       redirecting the user there.

    Note: This endpoint *only* creates the initial records. The actual AI-driven
          campaign content generation happens later when the 'start_game' SocketIO
          event is triggered from the lobby (see `socket_service.py`).
    """
    # Basic logging added for debugging purposes
    current_app.logger.debug(f"--- Received request for /api/games/create ---")
    data = request.get_json()

    current_app.logger.debug(f"Incoming data: {data}")

    # --- Validation ---
    if not data or 'template_id' not in data:
        current_app.logger.warning("Missing template_id in request data.")
        return jsonify({'error': 'Missing template_id'}), 400

    template_id = data['template_id']
    game_name = data.get('name', f'New Game (Template {template_id})') # Default name
    template_overrides = data.get('template_overrides', {})
    creator_customizations = data.get('creator_customizations', {})

    template = db.session.get(Template, template_id)
    if not template:
        current_app.logger.error(f"Template with ID {template_id} not found.")
        return jsonify({'error': 'Template not found'}), 404
    current_app.logger.debug(f"Using Template ID: {template.id}")

    try:
        # --- Create Game Record ---
        current_app.logger.debug(f"Creating Game object: Name='{game_name}', TemplateID={template.id}")
        game = Game(
            name=game_name,
            template_id=template.id,
            created_by=current_user.id
        )
        # Set overrides and customizations AFTER initialization
        game.template_overrides = template_overrides
        game.creator_customizations = creator_customizations
        current_app.logger.debug(f"Set game.template_overrides: {game.template_overrides}")
        current_app.logger.debug(f"Set game.creator_customizations: {game.creator_customizations}")

        db.session.add(game)
        db.session.flush() # Flush to get game.id before creating association
        current_app.logger.debug(f"Game record added and flushed (ID: {game.id})")

        # --- Create GamePlayer Association ---
        current_app.logger.debug(f"Creating GamePlayer association: GameID={game.id}, UserID={current_user.id}")
        game_player_assoc = GamePlayer(game_id=game.id, user_id=current_user.id, is_ready=False)
        db.session.add(game_player_assoc)
        current_app.logger.debug("GamePlayer association added.")

        # --- Commit ---
        db.session.commit()
        current_app.logger.info(f"Successfully committed Game (ID: {game.id}) and GamePlayer association.")

        # --- Return Success Response ---
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
