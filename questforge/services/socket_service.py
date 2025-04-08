from flask import current_app, request # Added request import
from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from sqlalchemy.orm import joinedload # Import joinedload
from ..extensions import db
from ..extensions.socketio import get_socketio
from ..models import Game, User, GamePlayer, GameState, Template # Added GameState, Template

socketio = get_socketio()
from .game_state_service import game_state_service # Import the instance
from .ai_service import AIService

class SocketService:
    @staticmethod
    def register_handlers():
        """Register all Socket.IO event handlers"""
        
        @socketio.on('connect')
        def handle_connect():
            emit('connection_response', {'status': 'connected'})

        @socketio.on('join_game')
        def handle_join_game(data):
            """Handle player joining a game room"""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            
            if not game_id or not user_id:
                emit('error', {'message': 'Missing game_id or user_id'})
                return

            # Perform database operations within the app context
            with current_app.app_context(): 
                # Validate game and user using db.session.get
                game = db.session.get(Game, game_id)
                user = db.session.get(User, user_id)

                if not game or not user:
                    # Log the error server-side for debugging
                    current_app.logger.warning(f"Join game failed: Invalid game_id ({game_id}) or user_id ({user_id}).")
                    # Emit error back to the specific client (emit outside context is fine)
                    emit('error', {'message': 'Invalid game or user'})
                    return # Stop execution if validation fails

                # Log successful join before proceeding
                current_app.logger.info(f"User {user_id} ({user.username}) attempting to join game {game_id} ({game.name}).")

                # Join SocketIO room (can happen outside DB transaction)
                join_room(game_id)
                current_app.logger.info(f"User {user_id} ({user.username}) joined SocketIO room: {game_id}")

                # Update game state service (in-memory state) - Ensure this is idempotent too
                # Assuming game_state_service.join_game handles duplicates gracefully (e.g., using a set)
                game_state_service.join_game(game_id, user_id) 
                
                player_was_added = False # Flag to track if DB insertion happened
                # Check/Create player association in DB
                existing_association = GamePlayer.query.filter_by(game_id=game_id, user_id=user_id).first()
                if not existing_association:
                    current_app.logger.info(f"Player {user_id} not found in GamePlayer table for game {game_id}. Adding.")
                    new_association = GamePlayer(game_id=game_id, user_id=user_id)
                    db.session.add(new_association)
                    try:
                        db.session.commit()
                        current_app.logger.info(f"Successfully added player association to game.")
                        player_was_added = True # Mark that a new player was added
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error committing player association for user {user_id} in game {game_id}: {str(e)}")
                        emit('error', {'message': 'Database error adding player to game'})
                        return # Stop if DB error
                else:
                     current_app.logger.info(f"Player {user_id} already associated with game {game_id}. Skipping DB add.")


                # Get all players in this game (eager load user data) to send full initial state
                game_players = GamePlayer.query.filter_by(game_id=game_id).options(joinedload(GamePlayer.user)).all()

                # Prepare player list data *inside* the context
                player_list_data = [{
                    'user_id': p.user_id,
                    'username': p.user.username, # Access username while session is active & user is loaded
                    'is_ready': p.is_ready
                } for p in game_players]

                # Always emit player_list to ensure joining client gets the current state
                current_app.logger.info(f"Emitting 'player_list' to room {game_id} after join attempt by user {user_id}.")
                emit('player_list', {'players': player_list_data}, room=game_id)

                # Only emit player_joined if the player was newly added to the DB in this call
                if player_was_added:
                    # Prepare data for the newly added player
                    newly_added_player_data = next((p for p in player_list_data if str(p['user_id']) == str(user_id)), None)
                    if newly_added_player_data:
                         current_app.logger.info(f"Emitting 'player_joined' for newly added user {user_id} to room {game_id}")
                         emit('player_joined', newly_added_player_data, room=game_id)
                    else:
                         current_app.logger.error(f"Failed to find data for newly added player {user_id} in game {game_id} for player_joined emit.")
                else:
                     current_app.logger.info(f"Skipping 'player_joined' emit for user {user_id} as they were already associated.")

            # Removed separate context block and emit logic for player_joined

        @socketio.on('leave_game')
        def handle_leave_game(data):
            """Handle player leaving a game room"""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            
            if game_id and user_id:
                leave_room(game_id) # leave_room can be outside context
                with current_app.app_context(): # Add app context for GameStateService and logging
                    game_state_service.leave_game(game_id, user_id) # Call on the instance
                    current_app.logger.info(f"User {user_id} left SocketIO room: {game_id}") # Add log
                # Emit can be outside context
                current_app.logger.info(f"Emitting 'player_left' for user {user_id} to room {game_id}") # Add log
                emit('player_left', { # Renamed for consistency
                    'user_id': user_id,
                }, room=game_id)

        @socketio.on('player_ready')
        def handle_player_ready(data):
            """Handle player clicking the ready button."""
            game_id = data.get('game_id')
            user_id = data.get('user_id')  # Get from data rather than current_user
            
            if not game_id or not user_id:
                emit('error', {'message': 'Missing game_id or user_id'})
                return
            print(f"Handling player_ready event for user {user_id} in game {game_id}")

            with current_app.app_context(): # Add app context
                # Find the association object
                association = GamePlayer.query.filter_by(game_id=game_id, user_id=user_id).first()

                if not association:
                    emit('error', {'message': 'Player not found in this game'}) # Emit can be outside context
                    return

                if not association.is_ready:
                    association.is_ready = True
                    try:
                        db.session.commit()
                        current_app.logger.info(f"User {user_id} marked as ready for game {game_id}")
                        # Broadcast the status update (emit can be outside context)
                        current_app.logger.info(f"Emitting 'player_status_update' for user {user_id} to room {game_id}") # Add log
                        current_app.logger.info(f"Debug: Emitting 'player_status_update' with data: user_id={user_id}, is_ready=True to room {game_id}")
                        current_app.logger.info(f"Debug: Preparing to emit 'player_status_update' for user_id={user_id}, is_ready=True to room {game_id}")
                        current_app.logger.info(f"Debug: Emitting 'player_status_update' to room {game_id} with event data: {{'user_id': {user_id}, 'is_ready': True}}")
                        emit('player_status_update', {
                            'user_id': user_id,
                            'is_ready': True
                        }, room=game_id)
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error updating player ready status: {str(e)}")
                        emit('error', {'message': 'Failed to update ready status'}) # Emit can be outside context
                else:
                    current_app.logger.info(f"User {user_id} already marked as ready for game {game_id}")

        @socketio.on('start_game')
        def handle_start_game(data):
            """Handle request to start the game."""
            game_id = data.get('game_id')
            user_id = data.get('user_id') # Get user_id from data

            print(f"Handling start_game event for game {game_id} triggered by user {user_id}") # Add logging

            if not game_id or not user_id: # Check for user_id too
                emit('error', {'message': 'Missing game_id or user_id'})
                return

            with current_app.app_context(): # Add app context
                game = db.session.get(Game, game_id)
                if not game:
                    current_app.logger.error(f"Start game request failed: Game {game_id} not found.") # Add logging
                    emit('error', {'message': 'Game not found'}) # Emit can be outside context
                    return

                # Optional: Check if the user starting the game is the creator
                if str(game.created_by) != str(user_id): # Compare as strings for safety
                     current_app.logger.warning(f"User {user_id} attempted to start game {game_id} but is not the creator ({game.created_by}).")
                     emit('error', {'message': 'Only the game creator can start the game'})
                     return

                # Check if all players are ready
                players = GamePlayer.query.filter_by(game_id=game_id).all()
                player_count = len(players)
                ready_players = [p for p in players if p.is_ready]
                all_ready = len(ready_players) == player_count
                
                current_app.logger.info(f"Game {game_id}: Found {player_count} players, {len(ready_players)} are ready. All ready: {all_ready}") # Add logging

                # Add minimum player check (e.g., >= 2)
                if player_count < 2:
                    current_app.logger.warning(f"Game {game_id}: Not enough players to start ({player_count}).")
                    emit('error', {'message': 'Need at least 2 players to start.'})
                    return

                if not all_ready:
                    current_app.logger.warning(f"Game {game_id}: Not all players are ready.")
                    emit('error', {'message': 'Not all players are ready'}) # Emit can be outside context
                    return

                # Update game status
                if game.status != 'in_progress': # Prevent starting multiple times
                    game.status = 'in_progress'
                    try:
                        db.session.commit()
                        current_app.logger.info(f"Game {game_id} status updated to 'in_progress'.")
                        # Emit event to redirect players to the game play page (emit can be outside context)
                        current_app.logger.info(f"Emitting 'game_started' for game {game_id} to room {game_id}") # Add log
                        emit('game_started', {'game_id': game_id}, room=game_id)
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Error updating game status for game {game_id}: {str(e)}")
                        emit('error', {'message': 'Failed to start game'}) # Emit can be outside context
                else:
                     current_app.logger.warning(f"Attempted to start game {game_id} which is already in progress.")


        @socketio.on('player_action')
        def handle_player_action(data):
            """Process player actions through AI and update game state"""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            action = data.get('action')
            
            if not all([game_id, user_id, action]):
                emit('error', {'message': 'Missing required fields'}, room=game_id)
                return

            try:
                # Get current game state
                game_state = game_state_service.get_state(game_id)
                if not game_state:
                    raise ValueError("Game state not found")
                
                # Get AI response
                ai_response = AIService.get_response(
                    game_state=game_state,
                    player_action=action,
                    user_id=user_id
                )

                # Update game state with AI response
                updated_state = game_state_service.update_state(
                    game_id=game_id,
                    new_state=ai_response['updated_state'],
                    log_entry=ai_response['narrative']
                )

                # Broadcast updated state to all players
                emit('game_state_update', {
                    'state': updated_state,
                    'log': ai_response['narrative'],
                    'actions': ai_response['available_actions']
                }, room=game_id)

            except Exception as e:
                current_app.logger.error(f"Error processing action: {str(e)}")
                emit('error', {'message': 'Failed to process action'}, room=game_id)

        @socketio.on('request_state')
        def handle_state_request(data):
            """Send current game state to requesting player"""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            
            if not game_id or not user_id:
                emit('error', {'message': 'Missing game ID or user ID'}, room=request.sid)
                return

            try:
                with current_app.app_context():
                    # Load Game with its Campaign relationship eagerly
                    game = db.session.query(Game).options(joinedload(Game.campaign)).get(game_id)
                    if not game:
                        emit('error', {'message': 'Invalid game ID'}, room=request.sid)
                        current_app.logger.warning(f"State request failed: Invalid game ID {game_id} from {request.sid}")
                        return
                    if not game.campaign: # Check if campaign relationship loaded
                        current_app.logger.error(f"State request failed: Game {game_id} has no associated campaign template.")
                        emit('error', {'message': 'Game campaign template not found'}, room=request.sid)
                        return

                    # Check if state is already in the service (in-memory)
                    state_info = game_state_service.get_state(game_id)

                    # Check if state exists in memory and is not empty/default
                    if not state_info or not state_info.get('state'):
                        current_app.logger.info(f"State for game {game_id} not found in service, checking DB.")
                        # State not in memory, check the database
                        db_state = GameState.query.filter_by(game_id=game_id).first()

                        if db_state:
                            # State found in DB, load it into the service
                            current_app.logger.info(f"Loading existing state for game {game_id} from DB into service.")
                            game_state_service.join_game(game_id, 'system') # Ensure game is tracked
                            game_state_service.active_games[game_id]['state'] = db_state.state_data
                            # Use timestamp as a simple version indicator for now
                            loaded_version = db_state.last_updated.timestamp() if db_state.last_updated else 1
                            game_state_service.active_games[game_id]['version'] = loaded_version
                            current_app.logger.info(f"Loaded state version {loaded_version} for game {game_id}")
                        else:
                            # State not in DB, create a new GameState record
                            current_app.logger.info(f"No state found in DB for game {game_id}. Creating new state record.")
                            new_state_record = GameState(
                                game_id=game_id,
                                campaign_id=game.campaign_id,
                                state_data=game.campaign.initial_state # Use initial_state from loaded campaign
                            )
                            db.session.add(new_state_record)
                            try:
                                db.session.commit()
                                current_app.logger.info(f"Successfully created new GameState record for game {game_id}.")
                                # Initialize the state in the service *after* successful DB commit
                                game_state_service.join_game(game_id, 'system') # Ensure game is tracked
                                game_state_service.active_games[game_id]['state'] = new_state_record.state_data
                                game_state_service.active_games[game_id]['version'] = 1 # Initial version for new state
                            except Exception as db_exc:
                                db.session.rollback()
                                current_app.logger.error(f"Failed to commit new GameState for game {game_id}: {db_exc}", exc_info=True)
                                emit('error', {'message': 'Failed to save initial game state'}, room=request.sid)
                                return

                    # Retrieve the state from the service again (should be populated now)
                    final_state_info = game_state_service.get_state(game_id)

                    if not final_state_info or 'state' not in final_state_info:
                        current_app.logger.error(f"Failed to retrieve state for game {game_id} even after load/create attempt.")
                        raise ValueError("Game state retrieval failed")

                    # Emit the state data currently held by the service
                    # Note: Emitting only 'state' and 'version' as 'log' and 'actions' aren't directly available here.
                    emit_data = {
                        'state': final_state_info['state'], # Send the dictionary from the service
                        'version': final_state_info['version'] # Include version
                    }
                    current_app.logger.info(f"Emitting game_state (v{emit_data['version']}) for game {game_id} to {request.sid}")
                    emit('game_state', emit_data, room=request.sid)

            except Exception as e:
                current_app.logger.error(f"State request error (Game {game_id}): {str(e)}", exc_info=True)
                emit('error', {
                    'message': 'Failed to retrieve game state',
                    'details': str(e)
                }, room=request.sid)
