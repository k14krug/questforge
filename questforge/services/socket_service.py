from flask import current_app, request # Added request import
from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from sqlalchemy.orm import joinedload, attributes # Import joinedload and attributes
from sqlalchemy import func # Import func for sum aggregation
import json # Import json for logging state_data
from ..extensions import db, get_socketio # Import get_socketio from extensions.py
from ..models import Game, User, GamePlayer, GameState, Template, ApiUsageLog # Added GameState, Template, ApiUsageLog
from decimal import Decimal # For cost calculation

socketio = get_socketio()
from .game_state_service import game_state_service # Import the instance
from .ai_service import ai_service # Import the singleton INSTANCE
# Import the specific functions needed
from .campaign_service import generate_campaign_structure, check_conclusion

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
                
                # Retrieve creator customizations
                creator_customizations = game.creator_customizations
                current_app.logger.info(f"Retrieved creator customizations for game {game_id}: {creator_customizations}")

                if not game.template:
                    current_app.logger.error(f"Start game request failed: Game {game_id} has no associated template.")
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

                # Add minimum player check (allow 1 for single-player mode)
                if player_count < 1:
                    current_app.logger.warning(f"Game {game_id}: Not enough players to start ({player_count}). Need at least 1.")
                    emit('error', {'message': 'Need at least 1 player to start.'}, room=request.sid)
                    return

                # For single-player, readiness check is not strictly necessary, but keep for consistency
                if player_count > 1 and not all_ready:
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
                        player_descriptions=player_descriptions,
                        creator_customizations=creator_customizations # Pass customizations
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

            player_log = {"type": "player", "content": action} # Define player log early
            updated_state_info = None # Define updated_state_info early
            ai_result = None # Initialize ai_result

            try:
                # --- Perform ALL DB operations within a single transaction ---
                with current_app.app_context():
                    # 1. Fetch GameState (no need to refresh initially, fetch gets latest)
                    db_game_state = db.session.query(GameState).options(
                        joinedload(GameState.game).joinedload(Game.campaign)
                    ).filter_by(game_id=game_id).first()

                    if not db_game_state:
                        raise ValueError(f"GameState record not found for game_id {game_id}")
                    
                    # Log the state *as fetched* before AI call
                    current_app.logger.debug(f"State data *before* AI call: {json.dumps(db_game_state.state_data)}")

                    # --- Narrative Guidance Logic ---
                    # Ensure state_data is a dict
                    if not isinstance(db_game_state.state_data, dict):
                        db_game_state.state_data = {} # Initialize if not dict

                    # Task 3.1: Increment turns_since_plot_progress
                    turns_key = 'turns_since_plot_progress'
                    current_turns = db_game_state.state_data.get(turns_key, 0)
                    db_game_state.state_data[turns_key] = current_turns + 1
                    current_app.logger.debug(f"Game {game_id}: Incremented {turns_key} to {db_game_state.state_data[turns_key]}")

                    # Task 3.2: Identify next required plot point
                    next_required_plot_point_desc = None
                    all_plot_points = db_game_state.game.campaign.major_plot_points
                    completed_plots = db_game_state.completed_plot_points or [] # Ensure list
                    if isinstance(all_plot_points, list):
                        for plot_point in all_plot_points:
                            if isinstance(plot_point, dict) and plot_point.get('required') is True:
                                description = plot_point.get('description')
                                if description and description not in completed_plots:
                                    next_required_plot_point_desc = description
                                    break # Found the first uncompleted required point
                    current_app.logger.debug(f"Game {game_id}: Next required plot point: {next_required_plot_point_desc}")

                    # Task 3.3: Determine if stuck
                    STUCK_THRESHOLD = 3 # Define threshold
                    is_stuck = db_game_state.state_data[turns_key] >= STUCK_THRESHOLD
                    current_app.logger.debug(f"Game {game_id}: Is player stuck? {is_stuck} (Turns: {db_game_state.state_data[turns_key]})")
                    # --- End Narrative Guidance Logic ---


                    # --- Inventory Validation ---
                    action_lower = action.lower()
                    item_keywords = ["use ", "give ", "read ", "equip ", "combine "] # Note the space
                    required_item = None
                    keyword_found = None
                    validation_passed = True # Assume validation passes unless proven otherwise

                    for keyword in item_keywords:
                        if action_lower.startswith(keyword):
                            keyword_found = keyword
                            # Final extraction fix v3: Capture the item name more intelligently
                            parts = action_lower.split(keyword, 1)
                            if len(parts) > 1:
                                # Take the remainder and split by common prepositions/articles
                                item_part = parts[1].strip()
                                # Split by common prepositions/articles, stopping at the first one found
                                for preposition in ["on", "at", "in", "to", "with", "the", "a", "an"]:
                                    item_part = item_part.split(preposition, 1)[0].strip() # Take the first part before any preposition
                                # Assign the cleaned item_part to required_item
                                required_item = item_part
                                current_app.logger.debug(f"Keyword '{keyword.strip()}' found. Extracted required_item: '{required_item}'")
                            else:
                                current_app.logger.debug(f"Keyword '{keyword.strip()}' found, but no item name followed.")
                                required_item = None # Ensure required_item is None if nothing follows keyword
                            break # Stop after first keyword match

                    # Check if an item was successfully extracted
                    if required_item:
                        current_app.logger.info(f"Action '{action}' requires item: '{required_item}'")
                        # Corrected key lookup: use 'current_inventory' based on logs
                        inventory = db_game_state.state_data.get('current_inventory') 
                        
                        if not isinstance(inventory, list):
                            current_app.logger.warning(f"Inventory validation failed for game {game_id}: 'current_inventory' key missing or not a list in state_data.")
                            emit('error', {'message': f"You don't seem to have a '{required_item}'."}, room=game_id)
                            validation_passed = False
                        else:
                            # Normalize inventory items to lowercase strings for comparison
                            inventory_lower = [str(item).lower() for item in inventory if isinstance(item, str)]
                            required_item_lower = required_item.lower()

                            # Check for exact match first
                            exact_match_found = required_item_lower in inventory_lower

                            if exact_match_found:
                                current_app.logger.info(f"Inventory validation passed (exact match) for game {game_id}: Item '{required_item}' found in inventory.")
                                # validation_passed remains True (set initially)
                            else:
                                # No exact match found, now check for partial (startswith) match
                                partial_match_found = False
                                for item_in_inv_lower in inventory_lower:
                                    if item_in_inv_lower.startswith(required_item_lower):
                                        current_app.logger.info(f"Inventory validation passed (partial match): Inventory item '{item_in_inv_lower}' starts with required '{required_item_lower}'. Allowing action.")
                                        partial_match_found = True
                                        validation_passed = True 
                                        break # Allow action based on first partial match
                                
                                # Only set validation_passed to False if NEITHER exact NOR partial match was found
                                if not partial_match_found: 
                                    current_app.logger.warning(f"Inventory validation failed for game {game_id}: Item '{required_item}' not found (exact or partial match) in current_inventory {inventory}.")
                                    emit('error', {'message': f"You don't have a '{required_item}'."}, room=game_id)
                                    validation_passed = False

                    # 2. Call AI Service (only if validation passed)
                    # Task 3.4: Pass narrative guidance info to AI Service
                    if validation_passed:
                        ai_result = ai_service.get_response(
                            game_state=db_game_state, # Pass the fetched object
                            player_action=action,
                            is_stuck=is_stuck, # Pass stuck status
                            next_required_plot_point=next_required_plot_point_desc # Pass next objective
                        )
                        if not ai_result:
                            # AI service itself failed after validation passed
                            raise ValueError("AI service failed to respond after inventory check (or no check needed).")
                    # else: ai_result remains None

                    # 3. Add player action to log (ALWAYS happens)
                    if not isinstance(db_game_state.game_log, list):
                        db_game_state.game_log = []
                    db_game_state.game_log.append(player_log)
                    if game_id in game_state_service.active_games:
                         if 'log' not in game_state_service.active_games[game_id] or not isinstance(game_state_service.active_games[game_id]['log'], list):
                              game_state_service.active_games[game_id]['log'] = []
                         game_state_service.active_games[game_id]['log'].append(player_log)
                    current_app.logger.debug(f"Appended player log entry for game {game_id}")
                    attributes.flag_modified(db_game_state, "game_log") # Flag game_log modification

                    # 4. Process AI Result (if validation passed AND AI responded)
                    if ai_result:
                        # This block is now correctly indented relative to the outer 'with'
                        ai_response_data, model_used, usage_data = ai_result

                        # Task 3.5: Process achieved_plot_point from AI response
                        state_changes = ai_response_data.get('state_changes')
                        achieved_plot_desc = None
                        plot_point_achieved_this_turn = False
                        if isinstance(state_changes, dict):
                            achieved_plot_desc = state_changes.pop('achieved_plot_point', None) # Use pop to remove if present

                        if achieved_plot_desc:
                            current_app.logger.info(f"Game {game_id}: AI indicated plot point achieved: '{achieved_plot_desc}'")
                            # Ensure completed_plot_points is a list
                            if not isinstance(db_game_state.completed_plot_points, list):
                                db_game_state.completed_plot_points = []
                            # Add if not already present
                            if achieved_plot_desc not in db_game_state.completed_plot_points:
                                db_game_state.completed_plot_points.append(achieved_plot_desc)
                                attributes.flag_modified(db_game_state, "completed_plot_points")
                                current_app.logger.debug(f"Game {game_id}: Added '{achieved_plot_desc}' to completed_plot_points.")
                            else:
                                current_app.logger.debug(f"Game {game_id}: Plot point '{achieved_plot_desc}' already completed.")
                            # Reset stuck counter
                            db_game_state.state_data[turns_key] = 0
                            plot_point_achieved_this_turn = True
                            current_app.logger.debug(f"Game {game_id}: Reset {turns_key} to 0 due to plot point achievement.")
                        # --- End Plot Point Achievement Processing ---

                        # Update GameState object with AI response data (state_changes might have been modified)
                        updated_state_info = game_state_service.update_state(
                            game_id=game_id, # Pass game_id for in-memory update
                            user_id=user_id, # Pass the user_id of the player performing the action
                            state_changes=state_changes, # Pass potentially modified state_changes
                            log_entry=ai_response_data.get('narrative'),
                            actions=ai_response_data.get('available_actions'),
                            increment_version=True # Version increments only on successful AI update
                        )
                        # This nested if is also correctly indented
                        if not updated_state_info:
                            raise ValueError("Failed to update game state via service after AI response")

                        # Log API Usage
                        if usage_data:
                            try:
                                current_app.logger.info(f"Attempting to log usage for model: '{model_used}' (action)")
                                pricing_config = current_app.config.get('OPENAI_PRICING', {})
                                pricing_info = None
                                matched_key = None

                                if model_used in pricing_config:
                                    pricing_info = pricing_config[model_used]
                                    matched_key = model_used
                                    current_app.logger.info(f"Found exact pricing key '{matched_key}' for model '{model_used}' (action)")
                                else:
                                    model_parts = model_used.split('-')
                                    for i in range(len(model_parts) - 1, 0, -1):
                                        potential_key = '-'.join(model_parts[:i])
                                        if potential_key in pricing_config:
                                            pricing_info = pricing_config[potential_key]
                                            matched_key = potential_key
                                            current_app.logger.info(f"Found partial pricing key '{matched_key}' for model '{model_used}' (action)")
                                            break

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
                                current_app.logger.info(f"Created ApiUsageLog entry for game {game_id} (Player Action)")
                            except Exception as log_e:
                                current_app.logger.error(f"Failed to create ApiUsageLog entry for game {game_id} (action): {log_e}", exc_info=True)
                                # Decide if this should cause a rollback - probably not
                        else:
                            current_app.logger.warning(f"No usage data returned from AI service for game {game_id} player action.")

                        # --- Apply the complete updated state from game_state_service to the DB object ---
                        # updated_state_info contains the fully processed state including visited_locations etc.
                        # We already updated db_game_state.state_data[turns_key] and potentially db_game_state.completed_plot_points
                        # The game_state_service.update_state call also updates db_game_state.state_data with other changes.
                        # We just need to ensure state_data is flagged.
                        attributes.flag_modified(db_game_state, "state_data") # Flag state_data modification (covers turns counter)
                        # completed_plot_points was already flagged if modified
                        current_app.logger.debug(f"Game {game_id}: Flagged state_data as modified.")
                        # The rest of the state application logic inside update_state handles merging other changes.

                        # Update available actions on DB object using the processed actions
                        if updated_state_info and 'actions' in updated_state_info:
                             db_game_state.available_actions = updated_state_info['actions'] # Use actions from the service
                             attributes.flag_modified(db_game_state, "available_actions") # Flag available_actions modification
                             current_app.logger.debug(f"Updated db_game_state.available_actions from game_state_service for game {game_id}")
                        # else: # Log if actions are missing?

                        # --- End of block executed only on successful AI response ---

                    # Log state JUST BEFORE commit
                    current_app.logger.debug(f"PRE-COMMIT state_data: {json.dumps(db_game_state.state_data)}")
                    current_app.logger.debug(f"PRE-COMMIT game_log: {json.dumps(db_game_state.game_log)}")
                    current_app.logger.debug(f"PRE-COMMIT available_actions: {json.dumps(db_game_state.available_actions)}")


                    # 5. Commit the transaction (saves player log always, saves full state if AI ran)
                    db.session.commit()
                    if ai_result:
                        current_app.logger.info(f"Committed full state update and usage log for game {game_id} after action '{action}'.")
                    else:
                        current_app.logger.info(f"Committed player log entry for game {game_id} after failed inventory check for action '{action}'.")

                    # Log state JUST AFTER commit
                    current_app.logger.debug(f"POST-COMMIT state_data: {json.dumps(db_game_state.state_data)}")

                    # --- Post-Commit Operations (Outside transaction) ---
                    game_concluded = False # Flag to track conclusion
                    if ai_result and updated_state_info: # Only check conclusion and broadcast if AI updated state
                        # 6. Check for game conclusion AFTER commit using the committed state data
                        try:
                            # Extract necessary data *before* potential session issues
                            campaign = db_game_state.game.campaign # Get campaign object
                            campaign_conditions = campaign.conclusion_conditions
                            major_plot_points = campaign.major_plot_points # Get plot points
                            # Use the state data from the DB object which includes our direct modifications
                            committed_state_data = db_game_state.state_data
                            completed_plot_points_list = db_game_state.completed_plot_points # Get completed plots

                            current_app.logger.info(f"Checking conclusion for game {game_id} using committed state data.")
                            current_app.logger.debug(f"Conditions: {json.dumps(campaign_conditions)}")
                            current_app.logger.debug(f"Major Plot Points: {json.dumps(major_plot_points)}")
                            # Log the exact state data being passed to the function
                            current_app.logger.debug(f"State Data being passed to check_conclusion: {json.dumps(committed_state_data)}")
                            current_app.logger.debug(f"Completed Plot Points being passed: {json.dumps(completed_plot_points_list)}")


                            # Pass the extracted data directly to check_conclusion
                            # NOTE: check_conclusion needs modification to accept major_plot_points and completed_plot_points_list
                            game_concluded = check_conclusion(
                                game_id=game_id, # Pass the game_id
                                campaign_conditions=campaign_conditions,
                                major_plot_points=major_plot_points, # Pass plot points
                                current_state_data=committed_state_data,
                                completed_plot_points=completed_plot_points_list # Pass completed plots
                            )
                            if game_concluded:
                                current_app.logger.info(f"Game conclusion detected for game {game_id}.")
                                # Update game status in DB - re-fetch Game object here is safer
                                game = db.session.get(Game, game_id)
                                if game:
                                    game.status = 'completed'
                                    db.session.commit()
                                    current_app.logger.info(f"Game {game_id} status updated to 'completed'.")
                                else:
                                    current_app.logger.error(f"Could not find game {game_id} to update status to completed.")
                        except Exception as conc_e:
                            current_app.logger.error(f"Error during conclusion check for game {game_id}: {conc_e}", exc_info=True)
                            # Proceed with normal state update even if conclusion check fails

                        # 7. Broadcast appropriate event
                        if game_concluded:
                            # Emit game_concluded event
                            # Include final state details if needed
                            final_state_data = updated_state_info.copy() # Use the latest in-memory state info
                            # Recalculate cost one last time
                            new_total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
                            final_state_data['total_cost'] = float(new_total_cost_query if new_total_cost_query is not None else Decimal('0.0'))
                            # Add a conclusion message?
                            final_state_data['conclusion_message'] = "The adventure has concluded!" # Example message
                            current_app.logger.info(f"Broadcasting game_concluded for game {game_id}")
                            emit('game_concluded', final_state_data, room=game_id)
                        else:
                            # Broadcast normal game_state_update
                            # Recalculate total cost after commit
                            new_total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
                            new_total_cost = new_total_cost_query if new_total_cost_query is not None else Decimal('0.0')

                            # Prepare broadcast data using the info returned by update_state
                            broadcast_data = updated_state_info.copy()
                            broadcast_data['total_cost'] = float(new_total_cost)

                            # Broadcast updated state and cost to all players
                            current_app.logger.info(f"Broadcasting game_state_update for game {game_id} (v{broadcast_data['version']}) including total_cost: {broadcast_data['total_cost']:.4f}")
                            emit('game_state_update', broadcast_data, room=game_id)
                    # else: # No broadcast if commit was skipped (e.g., inventory check failed)
                    #    current_app.logger.info(f"Skipping broadcast for game {game_id} as commit was skipped.")

            except Exception as e:
                # Rollback needed if any error occurred within the try block
                with current_app.app_context(): # Need context for rollback
                    db.session.rollback()
                current_app.logger.error(f"Error processing player action '{action}' in game {game_id}, rolling back transaction: {str(e)}", exc_info=True)
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
