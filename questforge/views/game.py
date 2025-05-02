from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, abort, current_app
from flask_login import login_required, current_user
from ..models.game import Game, GamePlayer # Import GamePlayer
from ..models.campaign import Campaign
from ..models.template import Template
from ..models.user import User # Make sure User is imported
from ..models.api_usage_log import ApiUsageLog # Import the new model
from ..extensions import db, socketio
from .forms import GameForm
from sqlalchemy import func # Import func for sum aggregation
from decimal import Decimal # Import Decimal
from ..services import ai_service # Import ai_service
import traceback # Import traceback

game_bp = Blueprint('game', __name__)

@game_bp.route('/api/games/create-game', methods=['POST'])
@login_required
def create_game_old():
    """Create a new game from template"""
    data = request.get_json()
    print(f"DEBUG: Incoming request data: {data}")
    
    if not data:
        print("DEBUG: No data received in request")
    if 'template_id' not in data:
        print("DEBUG: Missing 'template_id' in request data")
    if 'name' not in data:
        print("DEBUG: Missing 'name' in request data")
    if not data or 'template_id' not in data or 'name' not in data:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    try:
        template = Template.query.get(data['template_id'])
        template_overrides = data.get('template_overrides', {}) # Get template overrides, default to empty dict
        creator_customizations = data.get('creator_customizations', {}) # Get customizations, default to empty dict
        
        if not template:
            return jsonify({'status': 'error', 'message': 'Template not found'}), 404
            
        game = Game(
            name=data['name'],
            template_id=template.id,
            created_by=current_user.id,
            creator_customizations=creator_customizations # Save customizations
        )
        db.session.add(game)
        db.session.flush() # Flush to get game.id before creating GamePlayer

        # Add creator as first player using the association object
        creator_association = GamePlayer(game_id=game.id, user_id=current_user.id)
        db.session.add(creator_association)

        db.session.commit()

        # Trigger campaign generation (asynchronous or synchronous based on design)
        # For now, let's assume a synchronous call for simplicity
        try:
            # Pass template_overrides and creator_customizations to the AI service
            campaign_data = ai_service.generate_campaign(
                template, 
                template_overrides=template_overrides, 
                creator_customizations=creator_customizations
            )
            
            # Save the generated campaign data
            campaign = Campaign(
                game_id=game.id,
                campaign_data=campaign_data # Store the full AI response
            )
            db.session.add(campaign)
            db.session.commit()

            # Update the game with the campaign ID
            game.campaign_id = campaign.id
            db.session.commit()

            # Redirect to the game lobby or play page
            return jsonify({'success': True, 'message': 'Game created successfully!', 'redirect_url': url_for('game.lobby', game_id=game.id)}), 201

        except Exception as e:
            # Rollback the game creation if campaign generation fails
            db.session.rollback()
            # Log the full exception traceback for detailed debugging
            print(f"Error generating campaign: {str(e)}")
            print(traceback.format_exc()) 
            return jsonify({'error': f'Failed to generate campaign: {e}'}), 500

    except Exception as e:
        db.session.rollback()
        # Log the full exception traceback for detailed debugging
        print(f"Error during initial game creation steps: {str(e)}")
        print(traceback.format_exc()) 
        return jsonify({'status': 'error', 'message': 'Internal server error during game creation.'}), 500


@game_bp.route('/game/<int:game_id>/lobby')
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
                return redirect(url_for('game.list_games')) # Redirect back if join fails
        else:
            flash("This game is not currently accepting new players.", "warning")
            return redirect(url_for('game.list_games')) # Redirect if game not joinable

    # Fetch associations again after potential add
    player_associations = GamePlayer.query.filter_by(game_id=game_id).all()

    return render_template('game/lobby.html',
        game=game,
        player_associations=player_associations,
        current_user_id=current_user.id
    )

@game_bp.route('/game/<int:game_id>/play')
@login_required
def play(game_id):
    """Main game play view"""
    game = Game.query.get_or_404(game_id)
    campaign = Campaign.query.filter_by(game_id=game_id).first()

    if not campaign:
        return redirect(url_for('game.lobby', game_id=game_id))

    # Retrieve the current game state
    game_state = game.game_states[-1] if game.game_states else None

    # Calculate total cost for the current game
    total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
    total_cost = total_cost_query if total_cost_query is not None else Decimal('0.0')

    # Get the AI model from config
    ai_model = current_app.config.get('OPENAI_MODEL', 'Not Configured')

    return render_template('game/play.html', 
                           game=game, 
                           campaign=campaign,
                           ai_model=ai_model, # Pass AI model to template
                           user_id=current_user.id, 
                           game_state=game_state, 
                           game_log=game_state.game_log if game_state else [],
                           total_cost=total_cost)

@game_bp.route('/game/<int:game_id>/history')
@login_required
def history(game_id):
    """Game history view"""
    game = Game.query.get_or_404(game_id)
    return render_template('game/history.html', game=game)

@game_bp.route('/game/create')
@login_required
def create_game_view():
    """Game creation view"""
    form = GameForm()
    templates = Template.query.all()
    return render_template('game_create.html', templates=templates, form=form)

@game_bp.route('/games/list')
@login_required
def list_games():
    """Lists active games available to join."""
    # Query for games that are 'active' (created but not started)
    # Exclude games the current user has already joined? Or show all active? Let's show all for now.
    all_games = Game.query.order_by(Game.created_at.desc()).all()
    
    # Calculate total cost for each game
    game_costs = {}
    for game in all_games:
        # Query the sum of costs from ApiUsageLog, handle None result
        total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game.id).scalar()
        # Ensure total_cost is Decimal or 0
        total_cost = total_cost_query if total_cost_query is not None else Decimal('0.0')
        game_costs[game.id] = total_cost

    return render_template('game/list.html', games=all_games, game_costs=game_costs)


# Game API Endpoints
@game_bp.route('/api/game/<int:game_id>/state', methods=['GET'])
@login_required
def get_game_state(game_id):
    """Get current game state"""
    game = Game.query.get_or_404(game_id)
    return {
        'status': 'success',
        'data': game.to_dict()
    }

@game_bp.route('/api/game/<int:game_id>/state', methods=['POST'])
@login_required
def update_game_state(game_id):
    """Update game state"""
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    if not data:
        return {'status': 'error', 'message': 'No data provided'}, 400
    
    try:
        game.update_state(data)
        db.session.commit()
        socketio.emit('game_state_update', {'game_id': game_id, 'state': game.state})
        return {'status': 'success', 'data': game.to_dict()}
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 400

@game_bp.route('/api/game/<int:game_id>/action', methods=['POST'])
@login_required
def player_action(game_id):
    """Handle player actions"""
    game = Game.query.get_or_404(game_id)
    data = request.get_json()
    
    if not data or 'action' not in data:
        return {'status': 'error', 'message': 'Invalid action'}, 400
    
    try:
        # Process player action
        result = game.process_action(current_user.id, data['action'], data.get('payload', {}))
        db.session.commit()
        socketio.emit('game_action', {
            'game_id': game_id,
            'player_id': current_user.id,
            'action': data['action'],
            'result': result
        })
        return {'status': 'success', 'data': result}
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}, 400
