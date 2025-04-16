from flask import current_app, request # Added request import
from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from sqlalchemy.orm import joinedload # Import joinedload
from sqlalchemy import func # Import func for sum aggregation
from ..extensions import db
from ..extensions.socketio import get_socketio
from ..models import Game, User, GamePlayer, GameState, Template, ApiUsageLog # Added GameState, Template, ApiUsageLog
from decimal import Decimal # For cost calculation

socketio = get_socketio()
from .game_state_service import game_state_service # Import the instance
from .ai_service import ai_service # Import the singleton INSTANCE
# Import the specific function needed, not a non-existent instance
from .campaign_service import generate_campaign_structure 

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

            print(f"Handling start_game event for game {game_id} triggered by user {user_id}")

            if not game_id or not user_id:
                emit('error', {'message': 'Missing game_id or user_id'}, room=request.sid) # Emit to specific user
                return

            with current_app.app_context():
                # Eagerly load template and player associations
                game = db.session.query(Game).options(
                    joinedload(Game.template), 
                    joinedload(Game.player_associations).joinedload(GamePlayer.user) # Load users via association
                ).get(game_id)
                if not game:
                    current_app.logger.error(f"Start game request failed: Game {game_id} not found.")
                    emit('error', {'message': 'Game not found'}, room=request.sid)
                    return
                
                if not game.template:
                    current_app.logger.error(f"Start game request failed: Game {game_id} has no associated template.")
                    emit('error', {'message': 'Game template not found'}, room=request.sid)
                    return

                # Check if the user starting the game is the creator
                if str(game.created_by) != str(user_id):
                     current_app.logger.warning(f"User {user_id} attempted to start game {game_id} but is not the creator ({game.created_by}).")
                     emit('error', {'message': 'Only the game creator can start the game'}, room=request.sid)
                     return

                # Check if all players are ready using the eager-loaded associations
                players = game.player_associations 
                player_count = len(players)
                ready_players = [p for p in players if p.is_ready]
                all_ready = len(ready_players) == player_count
                
                current_app.logger.info(f"Game {game_id}: Found {player_count} players, {len(ready_players)} are ready. All ready: {all_ready}") # Add logging

                # Add minimum player check (e.g., >= 2)
                if player_count < 1: # Allow starting solo for testing? Or enforce 2? Let's enforce 2 for now.
                    current_app.logger.warning(f"Game {game_id}: Not enough players to start ({player_count}). Need at least 2.")
                    emit('error', {'message': 'Need at least 2 players to start.'}, room=request.sid)
                    return

                if not all_ready:
                    current_app.logger.warning(f"Game {game_id}: Not all players are ready.")
                    emit('error', {'message': 'Not all players are ready'}, room=request.sid)
                    return

                # Check if game already has a campaign (meaning it was already started)
                if game.campaign:
                    current_app.logger.warning(f"Attempted to start game {game_id} which already has a campaign.")
                    # Optionally re-emit game_started if needed, or just ignore
                    emit('game_started', {'game_id': game_id}, room=game_id) # Re-emit for clients that missed it?
                    return

                # --- Trigger Campaign Generation ---
                current_app.logger.info(f"All players ready for game {game_id}. Triggering campaign generation.")
                
                # Gather player descriptions
                player_descriptions = {
                    str(p.user_id): p.character_description or f"Player {i+1}" # Use default if None
                    for i, p in enumerate(players)
                }
                current_app.logger.info(f"Gathered player descriptions for game {game_id}: {player_descriptions}")

                try:
                    # Call the campaign service to generate the campaign structure and initial state
                    campaign_generated = generate_campaign_structure(
                        game=game, 
                        template=game.template, 
                        player_descriptions=player_descriptions
                    )

                    if campaign_generated:
                        current_app.logger.info(f"Campaign generation successful for game {game_id}.")

                        # Update game status *after* successful generation
                        game.status = 'in_progress'
                        try:
                            db.session.commit()  # Commit status change
                            current_app.logger.info(f"Game {game_id} status updated to 'in_progress'.")

                            # Emit game_started to the room
                            current_app.logger.info(f"Emitting 'game_started' for game {game_id} to room {game_id}")
                            emit('game_started', {'game_id': game_id}, room=game_id)

                            # DO NOT emit initial state here. Client will request it upon loading play.html.
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"Error updating game status to 'in_progress' for game {game_id}: {str(e)}", exc_info=True)
                            emit('error', {'message': 'Failed to update game status.'}, room=request.sid)
                    else:
                        current_app.logger.error(f"Campaign generation failed for game {game_id}.")
                        emit('error', {'message': 'Failed to generate campaign.'}, room=request.sid)
                except Exception as e:
                    current_app.logger.error(f"Error during campaign generation for game {game_id}: {str(e)}", exc_info=True)
                    emit('error', {'message': 'An error occurred during campaign generation.'}, room=request.sid)

            # Removed the misplaced try...except block that was here

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
                # Fetch the GameState OBJECT from the database, eagerly loading game and campaign
                with current_app.app_context(): # Ensure DB access is within context
                    db_game_state = db.session.query(GameState).options(
                        joinedload(GameState.game).joinedload(Game.campaign) # Eager load game -> campaign
                    ).filter_by(game_id=game_id).first()

                if not db_game_state:
                    # Use the specific game_id in the error message
                    raise ValueError(f"GameState record not found for game_id {game_id}")
                
                # --- Log the player's action ---
                player_log = {"type": "player", "content": action}
                if not isinstance(db_game_state.game_log, list):
                    db_game_state.game_log = []
                db_game_state.game_log.append(player_log)
                if 'log' not in game_state_service.active_games[game_id] or not isinstance(game_state_service.active_games[game_id]['log'], list):
                    game_state_service.active_games[game_id]['log'] = []
                game_state_service.active_games[game_id]['log'].append(player_log)
                current_app.logger.debug(f"Appended player log entry for game {game_id}")
                
                # Get AI response using the imported instance, passing the OBJECT
                # The get_response method expects the GameState object
                # Update call to handle new return signature: (response_data, model_used, usage_data)
                ai_result = ai_service.get_response(
                    game_state=db_game_state, # Pass the actual GameState object
                    player_action=action      # Pass the action here
                )

                # Check if AI service failed
                if not ai_result:
                    current_app.logger.error(f"AI service failed to return a response for action '{action}' in game {game_id}")
                    # Emit a specific error or raise to be caught below
                    raise ValueError("AI service failed to respond")
                    
                # Unpack result
                ai_response_data, model_used, usage_data = ai_result

                # Log API Usage within the same app context
                if usage_data:
                    try:
                        current_app.logger.info(f"Attempting to log usage for model: '{model_used}' (action)") 
                        
                        # Revised Pricing Lookup Logic
                        pricing_config = current_app.config.get('OPENAI_PRICING', {})
                        pricing_info = None
                        matched_key = None

                        # 1. Try exact match first
                        if model_used in pricing_config:
                            pricing_info = pricing_config[model_used]
                            matched_key = model_used
                            current_app.logger.info(f"Found exact pricing key '{matched_key}' for model '{model_used}' (action)")
                        else:
                            # 2. Iteratively remove suffix components
                            model_parts = model_used.split('-')
                            for i in range(len(model_parts) - 1, 0, -1):
                                potential_key = '-'.join(model_parts[:i])
                                if potential_key in pricing_config:
                                    pricing_info = pricing_config[potential_key]
                                    matched_key = potential_key
                                    current_app.logger.info(f"Found partial pricing key '{matched_key}' for model '{model_used}' (action)")
                                    break # Use the first partial match found
                        
                        cost = None
                        prompt_tokens = usage_data.prompt_tokens
                        completion_tokens = usage_data.completion_tokens
                        total_tokens = usage_data.total_tokens

                        if pricing_info:
                            prompt_cost = (Decimal(prompt_tokens) / 1000) * Decimal(pricing_info['prompt'])
                            completion_cost = (Decimal(completion_tokens) / 1000) * Decimal(pricing_info['completion'])
                            cost = prompt_cost + completion_cost
                            current_app.logger.info(f"Calculated cost for game {game_id} API call (action): ${cost:.6f}")
                        else:
                            current_app.logger.warning(f"No pricing info found for model '{model_used}'. Cost will be null.")

                        usage_log = ApiUsageLog(
                            game_id=game_id,
                            model_name=model_used,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            cost=cost
                        )
                        db.session.add(usage_log)
                        # Commit will happen after state update
                        current_app.logger.info(f"Created ApiUsageLog entry for game {game_id} (Player Action)")
                    except Exception as log_e:
                        current_app.logger.error(f"Failed to create ApiUsageLog entry for game {game_id} (action): {log_e}", exc_info=True)
                        # Don't necessarily fail the whole action if logging fails
                else:
                    current_app.logger.warning(f"No usage data returned from AI service for game {game_id} player action.")


                # Update game state, log, and actions via the service
                # Use ai_response_data now
                updated_state_info = game_state_service.update_state(
                    game_id=game_id,
                    state_changes=ai_response_data.get('state_changes'), # Pass state changes dict
                    log_entry=ai_response_data.get('narrative'),       # Pass narrative as log entry
                    actions=ai_response_data.get('available_actions'), # Pass new actions list
                    increment_version=True                        # Increment version on player action
                )

                if not updated_state_info:
                     # Error already logged in update_state if DB issue occurred there
                     # Rollback should happen in the except block below
                     raise ValueError("Failed to update game state after action")

                # If we reach here, both AI call and state update logic (in memory + DB object modification) were successful
                # Now commit the transaction including the ApiUsageLog and the GameState changes
                db.session.commit()
                current_app.logger.info(f"Committed state update and usage log for game {game_id} after action '{action}'.")

                # Recalculate total cost after commit
                new_total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
                new_total_cost = new_total_cost_query if new_total_cost_query is not None else Decimal('0.0')
                
                # Add the new total cost to the broadcast data
                broadcast_data = updated_state_info.copy() # Avoid modifying the original dict
                broadcast_data['total_cost'] = float(new_total_cost) # Convert Decimal to float for JSON serialization

                # Broadcast updated state and cost to all players
                current_app.logger.info(f"Broadcasting game_state_update for game {game_id} (v{broadcast_data['version']}) including total_cost: {broadcast_data['total_cost']:.4f}")
                emit('game_state_update', broadcast_data, room=game_id)

            except Exception as e:
                # Rollback the session in case of any error after AI call
                db.session.rollback() 
                current_app.logger.error(f"Error processing player action '{action}' in game {game_id}, rolling back transaction: {str(e)}", exc_info=True)
                emit('error', {'message': 'Failed to process action'}, room=game_id) # Keep generic message for client

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
                        current_app.logger.error(f"State request failed: Game {game_id} has no associated campaign.")
                        emit('error', {'message': 'Game campaign not found'}, room=request.sid)
                        return

                    # Check if state is already in the service (in-memory)
                    # The state *must* be in the service after campaign generation
                    state_info = game_state_service.get_state(game_id)

                    if not state_info or not state_info.get('state'):
                        current_app.logger.error(f"No state found in GameStateService for game {game_id}. This is unexpected after campaign generation.")
                        emit('error', {'message': 'Failed to retrieve game state. Please contact support.'}, room=request.sid)
                        return

                    # Emit the state data currently held by the service
                    emit_data = {
                        'state': state_info['state'],
                        'version': state_info['version'],
                        'log': state_info.get('log', []), # Include log, default to empty list
                        'actions': state_info.get('actions', []) # Include actions, default to empty list
                    }
                    current_app.logger.info(f"Emitting game_state (v{emit_data['version']}) with log/actions for game {game_id} to {request.sid}")
                    emit('game_state', emit_data, room=request.sid)

            except Exception as e:
                current_app.logger.error(f"State request error (Game {game_id}): {str(e)}", exc_info=True)
                emit('error', {
                    'message': 'Failed to retrieve game state',
                    'details': str(e)
                }, room=request.sid)

        @socketio.on('update_character_description')
        def handle_update_character_description(data):
            """Handle player updating their character description."""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            description = data.get('description', '').strip() # Get description, default to empty, strip whitespace

            # Basic validation
            if not game_id or not user_id:
                emit('error', {'message': 'Missing game_id or user_id'}, room=request.sid)
                return
            
            # Security check: Ensure the user updating is the one logged in
            if str(current_user.id) != str(user_id):
                 current_app.logger.warning(f"Security Alert: User {current_user.id} attempted to update description for user {user_id} in game {game_id}.")
                 emit('error', {'message': 'Authorization error'}, room=request.sid)
                 return

            current_app.logger.info(f"Handling update_character_description for user {user_id} in game {game_id}.")

            with current_app.app_context():
                # Find the GamePlayer association
                association = GamePlayer.query.filter_by(game_id=game_id, user_id=user_id).first()

                if not association:
                    current_app.logger.error(f"Update description failed: GamePlayer association not found for user {user_id} in game {game_id}.")
                    emit('error', {'message': 'Player not found in this game'}, room=request.sid)
                    return

                # Update the description
                association.character_description = description
                
                try:
                    db.session.commit()
                    current_app.logger.info(f"Successfully updated character description for user {user_id} in game {game_id}.")
                    # Emit confirmation back to the specific user and potentially broadcast?
                    # For now, just confirm back to the sender.
                    emit('character_description_updated', {'user_id': user_id, 'status': 'success'}, room=request.sid) 
                    # Optionally, broadcast the change to the room if needed in the future:
                    # emit('player_description_changed', {'user_id': user_id, 'description': description}, room=game_id)
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Database error updating character description for user {user_id} in game {game_id}: {str(e)}", exc_info=True)
                    emit('error', {'message': 'Failed to save description'}, room=request.sid)
