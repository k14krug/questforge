from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from database import db # Import db directly from database
from models import Game, Template, User, GamePlayer, GameState
from datetime import datetime
import uuid
from services.ai_service import AIService # Import AIService
import logging # Import logging for AIService
from flask import current_app # Import current_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

games_bp = Blueprint('games', __name__, url_prefix='/api') # Add /api prefix

@games_bp.route('/games', methods=['POST'])
@jwt_required()
def create_game():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    template_id = data.get('template_id')
    game_name = data.get('game_name')
    # Optional settings from request body
    settings = data.get('settings', {})

    if not template_id or not game_name:
        return jsonify({"msg": "Missing template_id or game_name"}), 400

    template = Template.query.get(template_id)
    if not template:
        return jsonify({"msg": "Template not found"}), 404

    # Ensure the creator_user_id is the current authenticated user
    creator_user = User.query.get(current_user_id)
    if not creator_user:
        return jsonify({"msg": "Creator user not found"}), 404 # Should not happen with jwt_required

    try:
        # Generate Campaign Charter using AIService
        # Pass template data and game settings to the AI service
        template_data_for_ai = {
            "name": template.name,
            "genre": template.genre,
            "core_conflict": template.core_conflict,
            "world_description": template.world_description,
            "ai_gm_persona": template.ai_gm_persona,
            "core_skills": template.core_skills
        }
        campaign_charter, charter_cost, _, _ = current_app.ai_service.generate_campaign_charter(
            template_data=template_data_for_ai,
            game_settings=settings
        )

        new_game = Game(
            game_name=game_name, # Store the user-provided game name
            template_id=template.id,
            creator_user_id=creator_user.id,
            settings=settings,
            campaign_charter=campaign_charter, # Populated by AI
            cumulative_cost=charter_cost, # Initial cost from charter generation
            created_at=datetime.utcnow()
        )
        db.session.add(new_game)
        db.session.flush() # Use flush to get new_game.id before commit

        # Add the creator as the first player to the game
        character_name = data.get('character_name', f"{creator_user.username}'s Character")
        
        # Generate character sheet using AIService
        # Pass character_name (as keywords) and core_skills from the template
        character_sheet_response, character_sheet_cost, _, _ = current_app.ai_service.generate_character_sheet(
            character_keywords=character_name,
            core_skills=template.core_skills
        )
        
        new_game_player = GamePlayer(
            game_id=new_game.id,
            user_id=creator_user.id,
            character_name=character_name,
            character_sheet=character_sheet_response.get('character_sheet', {}) # Populated by AI
        )
        db.session.add(new_game_player)
        db.session.flush() # Use flush to get new_game_player.id before commit
        logging.info(f"GamePlayer created: id={new_game_player.id}, game_id={new_game_player.game_id}, user_id={new_game_player.user_id}")

        # Update game's cumulative cost with character sheet generation cost
        new_game.cumulative_cost += character_sheet_cost
        db.session.add(new_game) # Re-add to session to track changes

        # Create initial GameState for the new game with NPCs
        initial_narration = campaign_charter.get('initial_player_context', f"The adventure in '{campaign_charter.get('campaign_name', 'this mysterious place')}' begins...")
        
        # Initialize NPCs from campaign charter
        initial_npcs = campaign_charter.get('initial_state_elements', {}).get('key_npcs', [])
        for npc in initial_npcs:
            if 'id' not in npc:
                npc['id'] = str(uuid.uuid4())
            if 'status' not in npc:
                npc['status'] = 'active'
            if 'location' not in npc:
                npc['location'] = campaign_charter.get('initial_state_elements', {}).get('starting_location', 'Unknown Location')
        
        initial_game_state = GameState(
            game_id=new_game.id,
            current_player_id=creator_user.id, # Creator is the first player
            turn_number=1,
            current_story_summary=initial_narration,
            active_npcs=initial_npcs,
            game_log=[{"type": "GM_NARRATIVE", "timestamp": datetime.utcnow().isoformat(), "content": initial_narration}],
            updated_at=datetime.utcnow()
        )
        db.session.add(initial_game_state)
        db.session.flush() # Get ID before commit

        # Link the initial GameState to the Game
        new_game.current_game_state_id = initial_game_state.id
        db.session.add(new_game) # Re-add to session to track changes

        db.session.commit() # Commit all changes at once

        return jsonify({
            "message": "Game created successfully",
            "game_id": new_game.id,
            "template_id": new_game.template_id,
            "creator_user_id": new_game.creator_user_id,
            "settings": new_game.settings,
            "campaign_charter": new_game.campaign_charter, # Include the generated charter
            "cumulative_cost": new_game.cumulative_cost, # Include the initial cost
            "created_at": new_game.created_at.isoformat(),
            "initial_game_player_id": new_game_player.id
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Error creating game. Check unique constraints."}), 409
    except FileNotFoundError as e:
        db.session.rollback()
        return jsonify({"msg": f"Configuration error: {str(e)}"}), 500
    except ValueError as e:
        db.session.rollback()
        return jsonify({"msg": f"AI Service configuration error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"An unexpected error occurred during game creation: {str(e)}"}), 500

@games_bp.route('/games', methods=['GET'])
@jwt_required()
def get_all_games():
    current_user_id = get_jwt_identity()

    # Get games where the current user is either the creator or a GamePlayer
    games_as_creator = Game.query.filter_by(creator_user_id=current_user_id).all()
    games_as_player = Game.query.join(GamePlayer).filter(GamePlayer.user_id == current_user_id).all()

    # Combine and remove duplicates
    all_games = list(set(games_as_creator + games_as_player))

    return jsonify([game.to_dict() for game in all_games]), 200

@games_bp.route('/games/<int:game_id>', methods=['GET'])
@jwt_required()
def get_game_details(game_id):
    current_user_id = get_jwt_identity()

    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Check if the current user is the creator or a player in the game
    is_creator = (game.creator_user_id == current_user_id)
    is_player = GamePlayer.query.filter_by(game_id=game_id, user_id=current_user_id).first() is not None

    if not is_creator and not is_player:
        return jsonify({"msg": "Unauthorized: You are not a participant in this game"}), 403

    return jsonify(game.to_dict()), 200

@games_bp.route('/games/<int:game_id>', methods=['DELETE'])
@jwt_required()
def delete_game(game_id):
    current_user_id = get_jwt_identity()
    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Convert both to string for consistent comparison since JWT identity is string
    if str(game.creator_user_id) != str(current_user_id):
        return jsonify({"msg": "Unauthorized: Only the game creator can delete the game"}), 403

    try:
        # Set current_game_state_id to NULL in games table
        Game.query.filter_by(id=game_id).update({Game.current_game_state_id: None})

        # Delete all GamePlayer records for this game
        GamePlayer.query.filter_by(game_id=game_id).delete()
        
        # Delete all GameState records for this game
        GameState.query.filter_by(game_id=game_id).delete()
        
        # Delete the game itself
        db.session.delete(game)
        db.session.commit()
        
        return jsonify({"msg": "Game deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to delete game: {str(e)}"}), 500

@games_bp.route('/games/<int:game_id>/join', methods=['POST'])
@jwt_required()
def join_game(game_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    character_name = data.get('character_name')

    if not character_name:
        return jsonify({"msg": "Missing character_name"}), 400

    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Check if user is already in the game
    existing_player = GamePlayer.query.filter_by(game_id=game_id, user_id=current_user_id).first()
    if existing_player:
        return jsonify({"msg": "User already joined this game"}), 400

    # Check if game is full (if a player limit is implemented in settings)
    # For now, assuming no explicit player limit, or it's handled by frontend/AI
    # if game.settings.get('player_limit') and len(game.players) >= game.settings['player_limit']:
    #     return jsonify({"msg": "Game is full"}), 400

    try:
        new_game_player = GamePlayer(
            game_id=game.id,
            user_id=current_user_id,
            character_name=character_name,
            character_sheet={} # Placeholder, to be filled by AI later
        )
        db.session.add(new_game_player)
        db.session.commit()
        return jsonify({
            "message": "Successfully joined game",
            "game_player_id": new_game_player.id
        }), 200
    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "Error joining game. Check unique constraints."}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"An unexpected error occurred during game creation: {str(e)}"}), 500


@games_bp.route('/games/<int:game_id>/state', methods=['GET'])
@jwt_required()
def get_game_state(game_id):
    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    game_state_service = current_app.game_state_service # Access service from app context
    game_state, error = game_state_service.get_current_game_state(game_id)
    if error:
        return jsonify({"msg": error}), 404 if "not found" in error else 500
    
    state_dict = game_state.to_dict()
    state_dict['players'] = [player.to_dict() for player in game.game_players]
    
    charter = game.campaign_charter
    if isinstance(charter, str):
        try:
            charter = json.loads(charter)
        except json.JSONDecodeError:
            logging.error(f"Failed to decode campaign_charter for game {game_id}")
            charter = {}

    state_dict['campaign_charter'] = charter
    state_dict['all_objectives'] = charter.get('critical_path_objectives') or charter.get('initial_state_elements', {}).get('initial_quests', [])
    
    return jsonify(state_dict), 200

@games_bp.route('/games/<int:game_id>/action', methods=['POST'])
@jwt_required()
def submit_player_action(game_id):
    current_user_id = get_jwt_identity()
    data = request.get_json()
    action_text = data.get('action_text')
    game_player_id = data.get('game_player_id') # Assuming frontend sends this

    if not action_text or not game_player_id:
        return jsonify({"msg": "Missing action_text or game_player_id"}), 400

    # Verify game_player_id belongs to current_user and game_id
    game_player = GamePlayer.query.filter_by(id=game_player_id, user_id=current_user_id, game_id=game_id).first()
    if not game_player:
        return jsonify({"msg": "Unauthorized: Invalid game_player_id or not your player in this game"}), 403

    game_state_service = current_app.game_state_service # Access service from app context
    result, error = game_state_service.process_player_action(game_id, game_player_id, action_text)

    if error:
        return jsonify({"msg": error}), 500 # Or more specific error codes
    
    # In a real scenario, this would update the GameState in DB and potentially emit Socket.IO events
    # For now, return the simulated result
    return jsonify(result), 200

@games_bp.route('/games/<int:game_id>/leave', methods=['POST'])
@jwt_required()
def leave_game(game_id):
    current_user_id = get_jwt_identity()

    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    game_player = GamePlayer.query.filter_by(game_id=game_id, user_id=current_user_id).first()
    if not game_player:
        return jsonify({"msg": "User not in this game"}), 400

    try:
        db.session.delete(game_player)
        db.session.commit()
        return jsonify({"message": "Successfully left game"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"An error occurred: {str(e)}"}), 500

@games_bp.route('/games/<int:game_id>/end', methods=['POST'])
@jwt_required()
def end_game(game_id):
    current_user_id = get_jwt_identity()

    game = Game.query.get(game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Only the creator can end the game
    if game.creator_user_id != int(current_user_id): # Cast current_user_id to int
        return jsonify({"msg": "Unauthorized: Only the game creator can end the game"}), 403

    if game.completed_at:
        return jsonify({"msg": "Game is already ended"}), 400

    try:
        game.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            "message": "Game ended successfully",
            "game_id": game.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"An error occurred: {str(e)}"}), 500

@games_bp.route('/games/<int:game_id>/ready', methods=['POST'])
@jwt_required()
def ready_up(game_id):
    current_user_id = get_jwt_identity()
    game_player = GamePlayer.query.filter_by(game_id=game_id, user_id=int(current_user_id)).first()

    if not game_player:
        return jsonify({"msg": "Player not in this game"}), 404

    try:
        game_player.ready_status = not game_player.ready_status
        db.session.commit()

        game = Game.query.get(game_id)
        all_players = game.game_players
        all_ready = all(p.ready_status for p in all_players)

        if all_ready and all_players:
            if not game.started_at:
                game.started_at = datetime.utcnow()
                db.session.commit()
            current_app.socketio.emit('game_starting', {'game_id': game_id}, room=f'game_{game_id}')
        else:
            game_state, error = current_app.game_state_service.get_current_game_state(game_id)
            if error:
                return jsonify({"msg": "Could not retrieve game state after readying up"}), 500
            
            state_dict = game_state.to_dict()
            state_dict['players'] = [player.to_dict() for player in all_players]
            
            charter = game.campaign_charter
            if isinstance(charter, str):
                try:
                    charter = json.loads(charter)
                except json.JSONDecodeError:
                    logging.error(f"Failed to decode campaign_charter for game {game_id} in ready_up")
                    charter = {}

            state_dict['campaign_charter'] = charter
            state_dict['all_objectives'] = charter.get('critical_path_objectives') or charter.get('initial_state_elements', {}).get('initial_quests', [])
            current_app.socketio.emit('game_state_update', state_dict, room=f'game_{game_id}')
        
        return jsonify({"message": "Ready status updated"}), 200
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in ready_up for game {game_id}: {e}")
        return jsonify({"msg": f"An unexpected error occurred: {str(e)}"}), 500
