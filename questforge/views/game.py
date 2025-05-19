from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import login_required, current_user
from ..models.game import Game, GamePlayer
from ..models.game_state import GameState # Added GameState import
from ..models.campaign import Campaign
from ..models.template import Template
from ..models.user import User
from ..models.api_usage_log import ApiUsageLog
from ..extensions import db, socketio
from .forms import GameForm
from flask_wtf import FlaskForm # Import FlaskForm
from sqlalchemy import func # Import func for sum aggregation
from decimal import Decimal # Import Decimal
# Removed unused ai_service import
import traceback # Import traceback

# ==============================================================================
# Game Blueprint (`/game`)
# ==============================================================================
# Handles routes related to viewing and interacting with specific games:
# - Game creation form view (`/game/create`)
# - Listing available games (`/game/list`)
# - Game lobby view (`/game/<id>/lobby`)
# - Gameplay view (`/game/<id>/play`)
# - Game history view (`/game/<id>/history`)
# - API endpoints for game state/actions (`/game/api/<id>/...`)
#
# Note: The actual game *creation* API endpoint (`/api/games/create`)
#       is located in `questforge/views/campaign_api.py`.
# ==============================================================================
game_bp = Blueprint('game', __name__, url_prefix='/game')

@game_bp.route('/<int:game_id>/lobby')
@login_required
def lobby(game_id):
    """Game lobby view. Adds the current user to the game if they aren't already part of it."""
    game = db.session.get(Game, game_id)
    if not game:
        abort(404, description="Game not found")

    # Check if the user is already associated with the game
    existing_association = GamePlayer.query.filter_by(game_id=game_id, user_id=current_user.id).first()

    if not existing_association:
        # Add the current user to the game if they aren't already part of it
        # Ensure game is not already in progress or finished? Add status check if needed.
        if game.status == 'active': # Only allow joining games that are waiting
            new_association = GamePlayer(game_id=game_id, user_id=current_user.id, is_ready=False) # Start as not ready
            db.session.add(new_association)
            try:
                db.session.commit()
                flash(f"You have joined the game '{game.name}'.", "success")
                # Emit event to notify others? The socket join handler should do this.
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error adding player {current_user.id} to game {game_id}: {str(e)}")
                flash("Could not join the game due to an error.", "danger")
                # Redirect to the list view within the same blueprint
                return redirect(url_for('game.list_games')) 
        else:
            flash("This game is not currently accepting new players.", "warning")
            # Redirect to the list view within the same blueprint
            return redirect(url_for('game.list_games')) 

    # Fetch associations again after potential add
    player_associations = GamePlayer.query.filter_by(game_id=game_id).all()

    return render_template('game/lobby.html',
        game=game,
        player_associations=player_associations,
        current_user_id=current_user.id
    )

@game_bp.route('/<int:game_id>/play')
@login_required
def play(game_id): # Renamed from play_game to play for consistency
    """Main game play view"""
    game = Game.query.get_or_404(game_id)
    campaign = Campaign.query.filter_by(game_id=game_id).first()

    # Redirect to lobby if campaign hasn't been generated yet
    if not campaign:
        flash("The game hasn't started yet. Waiting in the lobby.", "info")
        return redirect(url_for('game.lobby', game_id=game_id))

    # Retrieve the current game state (latest one)
    game_state = game.game_states[-1] if game.game_states else None

    # Calculate total cost for the current game
    total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
    total_cost = total_cost_query if total_cost_query is not None else Decimal('0.0')

    # Get the AI model from config
    ai_model = current_app.config.get('OPENAI_MODEL_LOGIC', 'Not Configured') # Changed to OPENAI_MODEL_LOGIC

    # Fetch player details (username, character name, and description)
    player_associations = GamePlayer.query.filter_by(game_id=game_id).options(db.joinedload(GamePlayer.user)).all()
    player_details = {}
    for assoc in player_associations:
        if assoc.user: # Ensure the user object is loaded
            player_details[assoc.user_id] = {
                'username': assoc.user.username,
                'character_name': assoc.character_name, # Add character_name (could be None)
                'character_description': assoc.character_description # Add description (could be None)
            }
        else:
             # Log a warning if a user couldn't be loaded for an association
             current_app.logger.warning(f"Could not load user for GamePlayer association: game_id={game_id}, user_id={assoc.user_id}")


    return render_template('game/play.html',
                           game=game,
                           campaign=campaign,
                           ai_model=ai_model,
                           user_id=current_user.id,
                           game_state=game_state,
                           game_log=game_state.game_log if game_state else [],
                           total_cost=total_cost,
                           player_details=player_details) # Pass updated player details map

@game_bp.route('/<int:game_id>/history')
@login_required
def history(game_id):
    """Game history view"""
    game = Game.query.get_or_404(game_id)
    # Potentially load game states or other history data here
    return render_template('game/history.html', game=game)

@game_bp.route('/create')
@login_required
def create_game_view():
    """Renders the game creation form view."""
    form = GameForm() # Used for CSRF token if enabled
    templates = Template.query.order_by(Template.name).all() # Fetch templates for the dropdown
    return render_template('game/create.html', templates=templates, form=form) 

@game_bp.route('/list')
@login_required
def list_games():
    """Lists all games."""
    # Query for all games, ordered by creation date
    all_games = Game.query.order_by(Game.created_at.desc()).all()
    
    # Calculate total cost for each game
    game_costs = {}
    for game in all_games:
        total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game.id).scalar()
        total_cost = total_cost_query if total_cost_query is not None else Decimal('0.0')
        game_costs[game.id] = total_cost
    
    form = FlaskForm() # Create a generic form instance for CSRF token

    return render_template('game/list.html', games=all_games, game_costs=game_costs, form=form)

@game_bp.route('/<int:game_id>/delete', methods=['POST'])
@login_required
def delete_game(game_id):
    """Deletes a game and its associated data."""
    game = db.session.get(Game, game_id)

    if not game:
        flash("Game not found.", "danger")
        return redirect(url_for('game.list_games'))

    # Use game.creator.id for comparison, similar to the template fix
    if not game.creator or game.creator.id != current_user.id:
        flash("You are not authorized to delete this game.", "danger")
        return redirect(url_for('game.list_games'))

    try:
        # Delete associated GameStates
        GameState.query.filter_by(game_id=game.id).delete()
        # Delete associated Campaign
        Campaign.query.filter_by(game_id=game.id).delete()
        # Delete associated GamePlayers
        GamePlayer.query.filter_by(game_id=game.id).delete()
        # Delete associated ApiUsageLogs
        ApiUsageLog.query.filter_by(game_id=game.id).delete()
        
        # Delete the game itself
        db.session.delete(game)
        db.session.commit()
        flash(f"Game '{game.name}' and all its data have been deleted.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting game {game_id}: {str(e)}\n{traceback.format_exc()}")
        flash("An error occurred while trying to delete the game.", "danger")

    return redirect(url_for('game.list_games'))


@game_bp.route('/<int:game_id>/details', methods=['GET'])
@login_required
def game_details(game_id):
    """Displays the details of a specific game."""
    game = Game.query.get_or_404(game_id)
    template = game.template  # Access associated Template
    campaign = game.campaign  # Access associated Campaign (can be None)

    players_details = []
    if game.player_associations:  # Check if player_associations is not None
        for assoc in game.player_associations:
            players_details.append({
                'username': assoc.user.username if assoc.user else 'Unknown User',
                'character_name': assoc.character_name,
                'character_description': assoc.character_description
            })

    return render_template('game/details.html',
                           game=game,
                           template_data=template,
                           campaign_data=campaign,
                           players_details=players_details)

# ==============================================================================
# Game State/Action API Endpoints (`/game/api/<id>/...`)
# ==============================================================================
# These endpoints are potentially better suited for a dedicated game_api blueprint,
# but are kept here for now as they directly relate to interacting with a game instance.
# ==============================================================================

@game_bp.route('/api/<int:game_id>/state', methods=['GET'])
@login_required
def get_game_state(game_id):
    """API: Get current game state (likely deprecated if using SocketIO for state)"""
    # This might be less relevant if state is primarily managed via SocketIO
    game = Game.query.get_or_404(game_id)
    # Consider returning the latest GameState data instead of game.to_dict()
    latest_state = game.game_states[-1] if game.game_states else None
    return jsonify({
        'status': 'success',
        'data': latest_state.to_dict() if latest_state else None # Adapt GameState model if needed
    })

@game_bp.route('/api/<int:game_id>/state', methods=['POST'])
@login_required
def update_game_state(game_id):
    """API: Update game state (likely deprecated if using SocketIO for state)"""
    # This is likely superseded by SocketIO events like 'player_action'
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    try:
        # This logic should likely live within a service or the GameState model
        # game.update_state(data) # Assuming this method exists and works
        # For now, just acknowledge - real updates happen via SocketIO
        # db.session.commit() 
        # socketio.emit('game_state_update', {'game_id': game_id, 'state': game.state}) # Example emit
        return jsonify({'status': 'success', 'message': 'State update acknowledged (handled via SocketIO)'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in deprecated update_game_state API for game {game_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@game_bp.route('/api/<int:game_id>/action', methods=['POST'])
@login_required
def player_action(game_id):
    """API: Handle player actions (likely deprecated if using SocketIO for actions)"""
    # This is likely superseded by the 'player_action' SocketIO event
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    if not data or 'action' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid action'}, 400)
    
    try:
        # This logic should live within the SocketIO handler
        # result = game.process_action(current_user.id, data['action'], data.get('payload', {})) # Example call
        # db.session.commit()
        # socketio.emit('game_action', { ... }) # Example emit
        return jsonify({'status': 'success', 'message': 'Action acknowledged (handled via SocketIO)'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in deprecated player_action API for game {game_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}, 400)
