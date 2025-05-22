from flask import current_app, request # Added request import
from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from sqlalchemy.orm import joinedload, attributes # Import joinedload and attributes
from sqlalchemy import func # Import func for sum aggregation
import json # Import json for logging state_data
from ..extensions import db
from ..extensions.socketio import get_socketio
from ..models import Game, User, GamePlayer, GameState, Template, ApiUsageLog, Campaign # Added Campaign
from decimal import Decimal # For cost calculation
from questforge.utils.context_manager import build_context # Import build_context

socketio = get_socketio()
from .game_state_service import game_state_service # Import the instance
from .ai_service import ai_service, calculate_cost, log_api_usage # Import the singleton INSTANCE and helper functions
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
            current_app.logger.info(f"Handling player_ready event for user {user_id} in game {game_id}")

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
                        current_app.logger.info(f"Emitting 'player_status_update' for user {user_id}, is_ready=True, to room {game_id}")
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
                
                # --- Add Detailed Logging Here ---
                if game:
                    current_app.logger.debug(f"Retrieved Game object (ID: {game.id}) in handle_start_game.")
                    current_app.logger.debug(f"Value of game.template_overrides from DB: {game.template_overrides}")
                    current_app.logger.debug(f"Value of game.creator_customizations from DB: {game.creator_customizations}")
                else:
                     current_app.logger.error(f"Start game request failed: Game {game_id} not found.")
                     emit('error', {'message': 'Game not found'}, room=request.sid)
                     return
                # --- End Detailed Logging ---

                if not game: # This check is now redundant due to the else block above, but keep for safety
                    current_app.logger.error(f"Start game request failed: Game {game_id} not found.")
                    emit('error', {'message': 'Game not found'}, room=request.sid)
                    return
                
                # Retrieve creator customizations and template overrides
                creator_customizations = game.creator_customizations or {} # Default to empty dict if None
                template_overrides = game.template_overrides or {} # Default to empty dict if None
                current_app.logger.info(f"Retrieved creator customizations for game {game_id}: {creator_customizations}")
                current_app.logger.info(f"Retrieved template overrides for game {game_id}: {template_overrides}")

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

                # Gather player details (name and description)
                player_details = {}
                for p in players:
                    player_details[str(p.user_id)] = {
                        'name': p.character_name, # Could be None
                        'description': p.character_description or f"Player {p.user_id}" # Use default if None
                    }
                current_app.logger.info(f"Gathered player details for game {game_id}: {player_details}")

                try:
                    # Call the campaign service to generate the campaign structure and initial state
                    # Pass player_details instead of player_descriptions
                    campaign_generated = generate_campaign_structure(
                        game=game,
                        template=game.template,
                        player_details=player_details, # Pass the details dict
                        creator_customizations=creator_customizations, # Pass customizations
                        template_overrides=template_overrides # Pass overrides
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

            player_log = {"type": "player", "user_id": user_id, "content": action} # Include user_id for mapping
            updated_state_info = None # Define updated_state_info early
            stage_one_ai_result_tuple = None # Renamed from ai_result for clarity
            narrative_from_stage1 = "Action not processed due to validation failure or AI error." # Default narrative
            available_actions_from_stage1 = [] # Default actions

            try:
                # --- Perform ALL DB operations within a single transaction ---
                with current_app.app_context():
                    # 1. Fetch GameState and related Campaign
                    db_game_state = db.session.query(GameState).options(
                        joinedload(GameState.game).joinedload(Game.campaign)
                    ).filter_by(game_id=game_id).first()

                    if not db_game_state:
                        raise ValueError(f"GameState record not found for game_id {game_id}")
                    if not db_game_state.game or not db_game_state.game.campaign:
                        raise ValueError(f"Campaign data not found for game_id {game_id}")

                    campaign = db_game_state.game.campaign
                    state_data = db_game_state.state_data or {}

                    # --- Narrative Guidance Logic (ID-Based) ---
                    STUCK_THRESHOLD = 3
                    
                    # Ensure 'turns_since_plot_progress' exists and increment
                    turns_since_plot_progress = state_data.get('turns_since_plot_progress', 0) + 1
                    # state_data['turns_since_plot_progress'] will be updated later, before AI call if no achievement, or after if achievement.

                    # Identify next required plot point (ID and Description)
                    next_required_plot_point_id = None
                    next_required_plot_point_desc = None
                    
                    completed_plot_points_data = state_data.get('completed_plot_points', [])
                    if not isinstance(completed_plot_points_data, list): # Ensure it's a list
                        completed_plot_points_data = []
                    completed_plot_point_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id')]
                    
                    major_plot_points_list = campaign.major_plot_points
                    if not isinstance(major_plot_points_list, list):
                        major_plot_points_list = []

                    for plot_point in major_plot_points_list:
                        if isinstance(plot_point, dict) and plot_point.get('required') and plot_point.get('id') not in completed_plot_point_ids:
                            next_required_plot_point_id = plot_point.get('id')
                            next_required_plot_point_desc = plot_point.get('description')
                            break
                    
                    is_stuck = turns_since_plot_progress >= STUCK_THRESHOLD and next_required_plot_point_id is not None
                    
                    current_app.logger.debug(f"Narrative Guidance: Turns since progress: {turns_since_plot_progress}, Next required ID: '{next_required_plot_point_id}', Desc: '{next_required_plot_point_desc}', Stuck: {is_stuck}")
                    # --- End Narrative Guidance Logic (ID-Based) ---
                    
                    # Update turns_since_plot_progress in state_data *before* AI call, will be reset if plot point achieved
                    state_data['turns_since_plot_progress'] = turns_since_plot_progress

                    # Log the state *as fetched* before AI call
                    current_app.logger.debug(f"State data *before* AI call: {json.dumps(state_data)}") # Use updated state_data

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

                    # 2. Call Stage 1 AI Service (only if validation passed)
                    if validation_passed:
                        stage_one_ai_result_tuple = ai_service.get_response( # This is now Stage 1
                            game_state=db_game_state,
                            player_action=action,
                            is_stuck=is_stuck,
                            next_required_plot_point=next_required_plot_point_desc,
                            current_difficulty=db_game_state.game.current_difficulty # Pass current difficulty
                        )
                        if not stage_one_ai_result_tuple:
                            raise ValueError("AI service (Stage 1) failed to respond after inventory check (or no check needed).")
                    # else: stage_one_ai_result_tuple remains None

                    # 3. Add player action to log (ALWAYS happens)
                    if not isinstance(db_game_state.game_log, list):
                        db_game_state.game_log = []
                    db_game_state.game_log.append(player_log)
                    if game_id in game_state_service.active_games:
                         if 'log' not in game_state_service.active_games[game_id] or not isinstance(game_state_service.active_games[game_id]['log'], list):
                              game_state_service.active_games[game_id]['log'] = []
                         game_state_service.active_games[game_id]['log'].append(player_log)
                    current_app.logger.debug(f"Appended player log entry for game {game_id}")
                    attributes.flag_modified(db_game_state, "game_log") # Flag game_log modification immediately

                    # 4. Process Stage 1 AI Result (if validation passed AND AI responded)
                    if stage_one_ai_result_tuple:
                        stage_one_ai_output, model_used, usage_data = stage_one_ai_result_tuple

                        # Ensure stage_one_ai_output is a dictionary before accessing keys
                        if isinstance(stage_one_ai_output, dict):
                            narrative_from_stage1 = stage_one_ai_output.get('narrative', 'Error: AI narrative missing.')
                            general_state_changes_from_stage1 = stage_one_ai_output.get('state_changes', {})
                            available_actions_from_stage1 = stage_one_ai_output.get('available_actions', [])
                        else:
                            # Handle unexpected AI output format
                            current_app.logger.error(f"Stage 1 AI service returned unexpected output format for game {game_id}. Expected dict, got {type(stage_one_ai_output)}. Raw output: {stage_one_ai_output}")
                            narrative_from_stage1 = 'Error: AI returned unexpected format.'
                            general_state_changes_from_stage1 = {}
                            available_actions_from_stage1 = []
                            # Optionally, raise an error or emit a client error here if this is critical
                            # raise ValueError("AI service (Stage 1) returned unexpected output format.")

                        # Add AI narrative to game_log
                        db_game_state.game_log.append({"type": "ai", "content": narrative_from_stage1})
                        if game_id in game_state_service.active_games: # Also update in-memory log
                             if 'log' not in game_state_service.active_games[game_id] or not isinstance(game_state_service.active_games[game_id]['log'], list):
                                  game_state_service.active_games[game_id]['log'] = []
                             game_state_service.active_games[game_id]['log'].append({"type": "ai", "content": narrative_from_stage1})
                        current_app.logger.debug(f"Appended AI (Stage 1) narrative log entry for game {game_id}")
                        attributes.flag_modified(db_game_state, "game_log") # Flag game_log modification

                        # Merge general_state_changes_from_stage1 into state_data
                        # This includes location, inventory_changes, npc_status, world_object_states, conclusion flags etc.
                        # It does NOT include plot point completions.
                        if general_state_changes_from_stage1:
                            state_data.update(general_state_changes_from_stage1)
                            current_app.logger.debug(f"Merged Stage 1 AI's general_state_changes into state_data. Current state_data: {json.dumps(state_data)}")

                        # Update visited_locations based on AI's reported new location from Stage 1
                        new_location_from_stage1 = general_state_changes_from_stage1.get('location')
                        if new_location_from_stage1:
                            if 'visited_locations' not in state_data or not isinstance(state_data['visited_locations'], list):
                                state_data['visited_locations'] = []
                            if new_location_from_stage1 not in state_data['visited_locations']:
                                state_data['visited_locations'].append(new_location_from_stage1)
                                current_app.logger.debug(f"Added '{new_location_from_stage1}' to state_data['visited_locations']. Current: {state_data.get('visited_locations')}")

                        # Update available actions in db_game_state (will be part of the final emit)
                        db_game_state.available_actions = available_actions_from_stage1 # These are from Stage 1
                        attributes.flag_modified(db_game_state, "available_actions")

                        # Log API Usage for Stage 1
                        if usage_data:
                            try:
                                # Cost calculation and logging for Stage 1
                                cost = calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens, 'completion_tokens': usage_data.completion_tokens})
                                log_api_usage(
                                    model_name=model_used,
                                    prompt_tokens=usage_data.prompt_tokens,
                                    completion_tokens=usage_data.completion_tokens,
                                    total_tokens=usage_data.total_tokens,
                                    cost=cost,
                                    game_id=game_id
                                )
                                current_app.logger.info(f"Logged API usage for Stage 1 AI call (Game {game_id}). Cost: {cost}")
                            except Exception as log_e:
                                current_app.logger.error(f"Failed to create ApiUsageLog entry for game {game_id} (Stage 1 action): {log_e}", exc_info=True)
                        else:
                            current_app.logger.warning(f"No usage data returned from Stage 1 AI service for game {game_id} player action.")

                        # At this point, state_data contains updates from Stage 1.
                        
                        # --- Historical Summary Generation (New Step) ---
                        current_app.logger.debug(f"Attempting to generate historical summary for game {game_id}, action: '{action}'")
                        try:
                            # Pass the general state changes from Stage 1, as these are the immediate consequences of the action.
                            historical_summary_text = ai_service.generate_historical_summary(
                                player_action=action,
                                stage_one_narrative=narrative_from_stage1,
                                state_changes=general_state_changes_from_stage1, # Pass the state_changes from Stage 1
                                game_id=game_id
                            )

                            if historical_summary_text:
                                if 'historical_summary' not in state_data or not isinstance(state_data['historical_summary'], list):
                                    state_data['historical_summary'] = []
                                
                                # Optional: Limit the number of summaries stored to prevent unbounded growth
                                MAX_SUMMARIES = current_app.config.get('MAX_HISTORICAL_SUMMARIES', 20) # Default to 20
                                if len(state_data['historical_summary']) >= MAX_SUMMARIES:
                                    state_data['historical_summary'].pop(0) # Remove the oldest summary

                                state_data['historical_summary'].append(historical_summary_text)
                                # state_data is modified in place. The existing flag_modified call after Stage 4 will cover this.
                                current_app.logger.info(f"Successfully generated and appended historical summary for game {game_id}: '{historical_summary_text}'")
                                current_app.logger.debug(f"Current historical_summary list for game {game_id}: {state_data['historical_summary']}")
                            else:
                                current_app.logger.warning(f"Historical summary generation returned None for game {game_id}.")
                        except Exception as hs_e:
                            current_app.logger.error(f"Error during historical summary generation for game {game_id}: {str(hs_e)}", exc_info=True)
                        # --- End Historical Summary Generation ---

                        # Plot point completion is handled next.
                        # We will persist db_game_state.state_data after Stage 4.

                    # --- STAGE 2: System-Side Plausibility Check ---
                    plausible_plot_points_to_check = []
                    if stage_one_ai_result_tuple: # Only do Stage 2-4 if Stage 1 was successful
                        # completed_plot_point_ids was defined earlier for narrative guidance, reuse it.
                        # major_plot_points_list was also defined earlier.
                        pending_plot_points = [
                            pp for pp in major_plot_points_list 
                            if isinstance(pp, dict) and pp.get('id') not in completed_plot_point_ids
                        ]
                        current_app.logger.debug(f"Stage 2: Found {len(pending_plot_points)} pending plot points for plausibility check.")

                        action_narrative_text_lower = f"{action.lower()} {narrative_from_stage1.lower()}"
                        current_location = state_data.get('location', '').lower()
                        
                        # Get NPCs present in the current location from state_data
                        npcs_present = []
                        npc_status = state_data.get('npc_status', {})
                        if isinstance(npc_status, dict):
                            for npc_name, npc_info in npc_status.items():
                                # Check if NPC is in current location (either as string or in a dict)
                                if isinstance(npc_info, dict) and npc_info.get('location', '').lower() == current_location:
                                    npcs_present.append(npc_name.lower())
                                elif isinstance(npc_info, str) and npc_info.lower() in ['present', 'here']:
                                    npcs_present.append(npc_name.lower())
                        
                        current_app.logger.debug(f"Stage 2: Current location: '{current_location}', NPCs present: {npcs_present}")
                        
                        # Check each pending plot point for plausibility
                        for pp in pending_plot_points:
                            pp_desc_lower = pp.get('description', '').lower()
                            pp_id = pp.get('id', '')
                            is_plausible = False
                            plausibility_reasons = []
                            
                            # 1. Enhanced word matching (TF-IDF inspired approach)
                            # Extract meaningful words (longer than 3 chars) from plot point description
                            pp_words = set(w for w in pp_desc_lower.split() if len(w) > 3)
                            action_narrative_words = set(w for w in action_narrative_text_lower.split() if len(w) > 3)
                            
                            # Calculate word overlap ratio for more nuanced matching
                            if pp_words and action_narrative_words:  # Avoid division by zero
                                overlap_words = pp_words.intersection(action_narrative_words)
                                overlap_ratio = len(overlap_words) / len(pp_words)
                                
                                # More significant overlap (25% or more of plot point words)
                                if overlap_ratio >= 0.25:
                                    is_plausible = True
                                    plausibility_reasons.append(f"Word overlap ratio: {overlap_ratio:.2f}")
                                # Some overlap but below threshold
                                elif overlap_words:
                                    plausibility_reasons.append(f"Some word overlap but below threshold: {overlap_ratio:.2f}")
                            
                            # 2. Location-based relevance
                            if current_location and current_location in pp_desc_lower:
                                is_plausible = True
                                plausibility_reasons.append(f"Current location '{current_location}' mentioned in plot point")
                            
                            # 3. NPC-based relevance
                            for npc in npcs_present:
                                if npc and len(npc) > 3 and npc in pp_desc_lower:
                                    is_plausible = True
                                    plausibility_reasons.append(f"NPC '{npc}' present and mentioned in plot point")
                            
                            # 4. Special handling for critical game moments
                            # Check if this is a "required" plot point - give these higher priority
                            if pp.get('required', False):
                                # For required plot points, be more lenient
                                if not is_plausible and pp_words and action_narrative_words:
                                    # Check for any meaningful word overlap for required plot points
                                    if pp_words.intersection(action_narrative_words):
                                        is_plausible = True
                                        plausibility_reasons.append("Required plot point with some word overlap")
                            
                            # Add to plausible list if any check passed
                            if is_plausible:
                                plausible_plot_points_to_check.append(pp)
                                current_app.logger.debug(f"Stage 2: Plot point ID '{pp_id}' (Desc: '{pp.get('description')}') deemed plausible. Reasons: {', '.join(plausibility_reasons)}")
                            else:
                                current_app.logger.debug(f"Stage 2: Plot point ID '{pp_id}' not deemed plausible.")
                        
                        # If no plot points were deemed plausible but there are pending required plot points,
                        # include the first required plot point to ensure progress can be made
                        if not plausible_plot_points_to_check:
                            required_pending_plot_points = [pp for pp in pending_plot_points if pp.get('required', False)]
                            if required_pending_plot_points and turns_since_plot_progress >= 2:  # Only after 2+ turns without progress
                                first_required = required_pending_plot_points[0]
                                plausible_plot_points_to_check.append(first_required)
                                current_app.logger.info(f"Stage 2: No plot points deemed plausible, but including first required plot point '{first_required.get('id')}' due to {turns_since_plot_progress} turns without progress.")
                        
                        current_app.logger.info(f"Stage 2: Identified {len(plausible_plot_points_to_check)} plausible plot points for Stage 3 AI check.")

                    # --- STAGE 3: Focused AI Completion Analysis ---
                    stage_3_ai_results = [] # To store results from AI calls
                    if plausible_plot_points_to_check: # Only if there are plausible points
                        current_app.logger.info(f"Stage 3: Beginning focused AI completion analysis for {len(plausible_plot_points_to_check)} plot points.")
                        for plausible_pp in plausible_plot_points_to_check:
                            pp_id = plausible_pp.get('id')
                            pp_desc = plausible_pp.get('description')
                            current_app.logger.debug(f"Stage 3: Calling ai_service.check_atomic_plot_completion for ID: {pp_id}")
                            
                            # Call the new AI service method
                            # state_data here is the one already updated by Stage 1 general changes
                            stage_3_single_result = ai_service.check_atomic_plot_completion(
                                plot_point_id=pp_id,
                                plot_point_description=pp_desc,
                                current_game_state_data=state_data, 
                                player_action=action,
                                stage_one_narrative=narrative_from_stage1,
                                game_id=game_id # For logging API usage
                            )
                            
                            if stage_3_single_result and 'error' not in stage_3_single_result:
                                stage_3_ai_results.append(stage_3_single_result)
                                current_app.logger.info(f"Stage 3: AI check for plot ID '{pp_id}' returned: Completed={stage_3_single_result.get('completed')}, Confidence={stage_3_single_result.get('confidence_score')}")
                            else:
                                current_app.logger.error(f"Stage 3: AI check_atomic_plot_completion call failed for plot ID '{pp_id}'. Result: {stage_3_single_result}")
                        current_app.logger.info(f"Stage 3: Finished focused AI completion analysis. Got {len(stage_3_ai_results)} valid results.")
                    
                    # --- STAGE 4: System Aggregation & Final State Update (Plot Points) ---
                    CONFIDENCE_THRESHOLD = float(current_app.config.get('PLOT_COMPLETION_CONFIDENCE_THRESHOLD', 0.7))
                    newly_completed_plot_points_this_turn_ids = [] 

                    if stage_3_ai_results: # Only if Stage 3 produced results
                        current_app.logger.info(f"Stage 4: Aggregating {len(stage_3_ai_results)} Stage 3 AI results. Confidence threshold: {CONFIDENCE_THRESHOLD}")
                        if 'completed_plot_points' not in state_data or not isinstance(state_data['completed_plot_points'], list):
                            state_data['completed_plot_points'] = []
                        
                        # Get IDs of plot points already marked as completed *before* this turn's Stage 4 processing
                        # This uses the `completed_plot_point_ids` list which was up-to-date before Stage 1.
                        # Or, more robustly, re-derive from current state_data['completed_plot_points'] before modification in this loop.
                        ids_already_completed = [cp.get('id') for cp in state_data.get('completed_plot_points', []) if isinstance(cp, dict)]

                        for res in stage_3_ai_results:
                            is_completed_by_ai = res.get('completed', False)
                            confidence = res.get('confidence_score', 0.0)
                            plot_id_from_ai = res.get('plot_point_id')

                            if is_completed_by_ai and confidence >= CONFIDENCE_THRESHOLD:
                                if plot_id_from_ai not in ids_already_completed:
                                    # Find the full plot point object from campaign.major_plot_points
                                    full_plot_point_obj = next((p for p in major_plot_points_list if isinstance(p, dict) and p.get('id') == plot_id_from_ai), None)
                                    if full_plot_point_obj:
                                        state_data['completed_plot_points'].append(full_plot_point_obj)
                                        newly_completed_plot_points_this_turn_ids.append(plot_id_from_ai)
                                        current_app.logger.info(f"Stage 4: NEWLY COMPLETED plot point ID '{plot_id_from_ai}' (Desc: '{full_plot_point_obj.get('description')}'). Added to state_data.")
                                    else:
                                        current_app.logger.warning(f"Stage 4: AI confirmed completion for ID '{plot_id_from_ai}', but full object not found in campaign's major_plot_points.")
                                else:
                                    current_app.logger.debug(f"Stage 4: Plot point ID '{plot_id_from_ai}' was already in completed_plot_points. No change from this AI check.")
                            else:
                                current_app.logger.debug(f"Stage 4: Plot point ID '{plot_id_from_ai}' not completed or confidence too low (Completed: {is_completed_by_ai}, Confidence: {confidence}).")
                        
                        if newly_completed_plot_points_this_turn_ids:
                            current_app.logger.info(f"Stage 4: Newly completed plot points this turn: {newly_completed_plot_points_this_turn_ids}")
                            # Check if any of the *newly completed* plot points were *required*
                            was_any_newly_completed_required = any(
                                pp_obj.get('required') for newly_id in newly_completed_plot_points_this_turn_ids
                                for pp_obj in major_plot_points_list if isinstance(pp_obj, dict) and pp.get('id') == newly_id
                            )
                            if was_any_newly_completed_required:
                                state_data['turns_since_plot_progress'] = 0 # Reset counter
                                current_app.logger.info(f"Stage 4: Reset turns_since_plot_progress to 0 due to new required plot point(s) completion.")
                            else:
                                current_app.logger.info(f"Stage 4: Newly completed plot points were optional or none that were required. Turns since progress remains: {state_data['turns_since_plot_progress']}")
                        else:
                             current_app.logger.info(f"Stage 4: No new plot points confirmed as completed this turn based on Stage 3 AI checks and confidence.")
                    else:
                        current_app.logger.info("Stage 4: No Stage 3 AI results to process for plot point completion.")
                    
                    # state_data now contains Stage 1 general updates + Stage 4 plot point completions.
                    # Persist the final state_data to the database object
                    db_game_state.state_data = state_data
                    attributes.flag_modified(db_game_state, "state_data") # Ensure it's flagged for SQLAlchemy
                    current_app.logger.debug(f"Flagged final state_data on db_game_state for commit (after all stages).")

                    # Log state JUST BEFORE final commit
                    current_app.logger.debug(f"PRE-COMMIT final state_data (after all stages): {json.dumps(db_game_state.state_data)}")

                    # 5. Commit the transaction (saves all logs and the fully updated state_data)
                    db.session.commit()
                    current_app.logger.info(f"Committed all updates for game {game_id} after action '{action}'.")
                    
                    # Log state JUST AFTER final commit
                    current_app.logger.debug(f"POST-COMMIT final state_data: {json.dumps(db_game_state.state_data)}")

                # --- Post-Commit Operations (Outside transaction) ---
                # This section now uses the state that includes all stages.
                if stage_one_ai_result_tuple: # Check if Stage 1 AI call was successful to proceed with broadcast
                    # Update the in-memory game_state_service cache with the final state from DB
                    # The log_entry is the narrative from Stage 1, actions are also from Stage 1.
                    # The state_changes for the service should ideally be a diff, but for simplicity,
                    # we can let the service handle the full state if its update logic is robust.
                    # However, the `update_state` method expects `state_changes`.
                    # For now, we'll pass the general_state_changes_from_stage1 for the service's internal merging,
                    # but the broadcast will use the definitive db_game_state.state_data.
                    
                    # Re-evaluate what to pass to game_state_service.update_state
                    # It's used to update its internal cache and increment version.
                    # The narrative and actions are from Stage 1.
                    # The state_changes it receives are merged into its cached state.
                    # Since db_game_state.state_data is now the source of truth after commit,
                    # we should ensure the service's cache aligns if possible, or rely on subsequent get_state calls.
                    
                    # For the broadcast, we use the definitive data from db_game_state.
                    # The `updated_state_info` from `game_state_service.update_state` is mainly for the version number.
                    
                    # Let's call update_state to increment version and update its log/actions cache.
                    # The state_changes passed here are just for its internal merging logic, which might be okay.
                    temp_general_state_changes = {}
                    if stage_one_ai_result_tuple and stage_one_ai_result_tuple[0]:
                        temp_general_state_changes = stage_one_ai_result_tuple[0].get('state_changes', {})

                    updated_state_info = game_state_service.update_state(
                        game_id=game_id,
                        user_id=user_id,
                        state_changes=temp_general_state_changes, # General changes from Stage 1 for service's cache
                        log_entry=narrative_from_stage1, # Narrative from Stage 1
                        actions=available_actions_from_stage1, # Actions from Stage 1
                        increment_version=True 
                    )
                    if not updated_state_info:
                         current_app.logger.error(f"Failed to update in-memory game_state_service for game {game_id} after all stages.")
                         # This is not ideal, but DB is consistent.

                    with current_app.app_context(): # Context for cost query and game status update
                        new_total_cost_query = db.session.query(func.sum(ApiUsageLog.cost)).filter(ApiUsageLog.game_id == game_id).scalar()
                        new_total_cost = new_total_cost_query if new_total_cost_query is not None else Decimal('0.0')

                        # Prepare broadcast data using the definitive state from the DB
                        
                        # --- Calculate Plot Point Display Counts ---
                        first_required_pp_id = None
                        if major_plot_points_list:
                            for pp in major_plot_points_list:
                                if isinstance(pp, dict) and pp.get('required'):
                                    first_required_pp_id = pp.get('id')
                                    break
                        
                        total_plot_points_for_display = 0
                        for pp in major_plot_points_list:
                            if isinstance(pp, dict) and pp.get('id') != first_required_pp_id:
                                total_plot_points_for_display += 1
                        
                        current_completed_for_display = db_game_state.state_data.get('completed_plot_points', [])
                        completed_plot_points_display_count = 0
                        for pp in current_completed_for_display:
                            if isinstance(pp, dict) and pp.get('id') != first_required_pp_id:
                                completed_plot_points_display_count += 1
                        
                        newly_completed_display_details_msg = None
                        if newly_completed_plot_points_this_turn_ids:
                            for completed_id in newly_completed_plot_points_this_turn_ids:
                                if completed_id != first_required_pp_id:
                                    # Find the description of this newly completed, displayable plot point
                                    pp_obj = next((p for p in major_plot_points_list if isinstance(p, dict) and p.get('id') == completed_id), None)
                                    if pp_obj:
                                        newly_completed_display_details_msg = f"Plot point achieved: {pp_obj.get('description', 'Objective met!')}"
                                        break # Show notification for the first one
                        # --- End Calculate Plot Point Display Counts ---

                        # --- New: Extract latest_ai_response, player_commands, historical_summary for frontend ---
                        game_log = db_game_state.game_log if isinstance(db_game_state.game_log, list) else []
                        latest_ai_response = None
                        player_commands = []
                        for entry in game_log:
                            if isinstance(entry, dict):
                                if entry.get("type") == "ai":
                                    latest_ai_response = entry.get("content")
                                elif entry.get("type") == "player":
                                    player_commands.append({
                                        "user_id": entry.get("user_id"),
                                        "content": entry.get("content")
                                    })
                        # If multiple AI entries, take the last one
                        if any(e.get("type") == "ai" for e in game_log if isinstance(e, dict)):
                            latest_ai_response = [e.get("content") for e in game_log if isinstance(e, dict) and e.get("type") == "ai"][-1]
                        # Historical summary from state_data
                        historical_summary = db_game_state.state_data.get("historical_summary", [])

                        # --- Build player_display_map for mapping user_id to display name ---
                        # Eager-load all GamePlayer associations with user for this game
                        game_players = GamePlayer.query.filter_by(game_id=game_id).options(joinedload(GamePlayer.user)).all()
                        player_display_map = {}
                        for p in game_players:
                            display_name = p.character_name if p.character_name else (p.user.username if p.user else f"Player {p.user_id}")
                            player_display_map[str(p.user_id)] = display_name

                        broadcast_data = {
                            'game_id': game_id,
                            'user_id': user_id, # User who took the action
                            'state': db_game_state.state_data,       # Fully updated state from DB
                            'log': db_game_state.game_log,           # Fully updated log from DB
                            'actions': db_game_state.available_actions, # Actions from Stage 1, stored in DB
                            'version': updated_state_info.get('version') if updated_state_info else db_game_state.version,
                            'total_cost': float(new_total_cost),
                            'total_plot_points_display': total_plot_points_for_display,
                            'completed_plot_points_display_count': completed_plot_points_display_count,
                            'newly_completed_plot_point_message': newly_completed_display_details_msg, # Can be null
                            # --- New fields for frontend ---
                            'latest_ai_response': latest_ai_response,
                            'player_commands': player_commands,
                            'historical_summary': historical_summary,
                            'player_display_map': player_display_map
                        }
                        
                        current_app.logger.debug(f"Final broadcast data prepared for game {game_id}: {json.dumps(broadcast_data)}")

                        from .campaign_service import check_conclusion
                        game_has_concluded = check_conclusion(db_game_state)

                        if game_has_concluded:
                            current_app.logger.info(f"Game {game_id} has concluded. Modifying final broadcast.")
                            
                            # 1. Append system message to log
                            if not isinstance(broadcast_data.get('log'), list): # Ensure log is a list
                                broadcast_data['log'] = []
                            broadcast_data['log'].append({"type": "system", "content": "** CAMPAIGN COMPLETE! **"})
                            
                            # 2. Set actions to indicate completion
                            broadcast_data['actions'] = ["Campaign Complete"]

                            # Emit the modified game_state_update for the final turn
                            current_app.logger.info(f"Broadcasting FINAL game_state_update for concluded game {game_id} (v{broadcast_data['version']})")
                            emit('game_state_update', broadcast_data, room=game_id)

                            # Emit game_concluded event
                            current_app.logger.info(f"Emitting 'game_concluded' for game {game_id}.")
                            emit('game_concluded', {'game_id': game_id, 'message': 'The adventure has reached its conclusion!'}, room=game_id)
                            
                            # Update game status to 'completed'
                            game_to_update = db.session.get(Game, game_id)
                            if game_to_update:
                                game_to_update.status = 'completed'
                                try:
                                    db.session.add(game_to_update) # Add to session if re-fetched or to ensure it's managed
                                    db.session.commit()
                                    current_app.logger.info(f"Game {game_id} status updated to 'completed'.")
                                except Exception as e_status:
                                    db.session.rollback()
                                    current_app.logger.error(f"Error updating game status to 'completed' for game {game_id}: {e_status}", exc_info=True)
                            else:
                                current_app.logger.error(f"Could not find game {game_id} to update status to 'completed'.")
                        else:
                            # Game has not concluded, broadcast normal update
                            current_app.logger.info(f"[socket_service] Game {game_id} has not concluded. Broadcasting normal 'game_state_update' (v{broadcast_data.get('version')}) to room {game_id}.")
                            current_app.logger.debug(f"[socket_service] Full 'game_state_update' data for room {game_id}: {json.dumps(broadcast_data)}")
                            emit('game_state_update', broadcast_data, room=game_id)
                            current_app.logger.info(f"[socket_service] Game {game_id} has not concluded yet after action by user {user_id}.")
                # else: # No broadcast if commit was skipped or AI call failed
                #    current_app.logger.info(f"[socket_service] Skipping broadcast and conclusion check for game {game_id} as full AI update and commit did not occur.")

            except Exception as e:
                # Rollback needed if any error occurred within the try block OR if inventory check failed and we need to ensure no partial changes
                with current_app.app_context(): # Need context for rollback
                    db.session.rollback()
                current_app.logger.error(f"Error processing player action '{action}' in game {game_id}, rolling back transaction: {str(e)}", exc_info=True)
                emit('error', {'message': 'Failed to process action'}, room=game_id)


        @socketio.on('request_state')
        def handle_state_request(data):
            """Send current game state to requesting player"""
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            
            current_app.logger.info(f"[socket_service] Received 'request_state' for game_id={game_id}, user_id={user_id}, from SID: {request.sid}")

            if not game_id or not user_id:
                current_app.logger.warning(f"[socket_service] 'request_state' failed for SID {request.sid}: Missing game_id or user_id. Data: {data}")
                emit('error', {'message': 'Missing game ID or user ID'}, room=request.sid)
                return

            try:
                with current_app.app_context():
                    current_app.logger.debug(f"[socket_service] 'request_state' handler: Attempting to load game {game_id} and campaign.")
                    # Load Game with its Campaign relationship eagerly
                    game = db.session.query(Game).options(joinedload(Game.campaign)).get(game_id)
                    if not game:
                        current_app.logger.warning(f"[socket_service] 'request_state' failed: Invalid game ID {game_id} from SID {request.sid}")
                        emit('error', {'message': 'Invalid game ID'}, room=request.sid)
                        return
                    if not game.campaign: # Check if campaign relationship loaded
                        current_app.logger.error(f"[socket_service] 'request_state' failed: Game {game_id} (SID: {request.sid}) has no associated campaign.")
                        emit('error', {'message': 'Game campaign not found'}, room=request.sid)
                        return
                    current_app.logger.debug(f"[socket_service] 'request_state' handler: Game {game_id} and campaign loaded. Fetching state from game_state_service.")

                    # Check if state is already in the service (in-memory)
                    # The state *must* be in the service after campaign generation
                    state_info = game_state_service.get_state(game_id)
                    current_app.logger.debug(f"[socket_service] 'request_state' handler: game_state_service.get_state({game_id}) returned: {state_info is not None}")


                    if not state_info or not state_info.get('state'):
                        current_app.logger.error(f"[socket_service] No state found in GameStateService for game {game_id} (SID: {request.sid}). This is unexpected. State_info: {json.dumps(state_info)}")
                        emit('error', {'message': 'Failed to retrieve game state. Please contact support.'}, room=request.sid)
                        return
                    
                    current_app.logger.debug(f"[socket_service] 'request_state' handler: State found in service. Calculating plot display counts. state_info['state'] keys: {list(state_info['state'].keys()) if state_info.get('state') else 'None'}")


                    # Emit the state data currently held by the service
                    # Calculate plot point display counts for initial state
                    major_plot_points_list_initial = game.campaign.major_plot_points if game.campaign else []
                    if not isinstance(major_plot_points_list_initial, list):
                        major_plot_points_list_initial = []

                    first_required_pp_id_initial = None
                    if major_plot_points_list_initial:
                        for pp_init in major_plot_points_list_initial:
                            if isinstance(pp_init, dict) and pp_init.get('required'):
                                first_required_pp_id_initial = pp_init.get('id')
                                break
                    
                    total_plot_points_for_display_initial = 0
                    for pp_init in major_plot_points_list_initial:
                        if isinstance(pp_init, dict) and pp_init.get('id') != first_required_pp_id_initial:
                            total_plot_points_for_display_initial += 1
                    
                    completed_plot_points_initial_raw = state_info['state'].get('completed_plot_points', [])
                    if not isinstance(completed_plot_points_initial_raw, list):
                        completed_plot_points_initial_raw = []
                        
                    completed_plot_points_display_count_initial = 0
                    for pp_init in completed_plot_points_initial_raw:
                        if isinstance(pp_init, dict) and pp_init.get('id') != first_required_pp_id_initial:
                            completed_plot_points_display_count_initial += 1

                    # --- New: Extract latest_ai_response, player_commands, historical_summary for frontend initial state ---
                    game_log = state_info.get('log', [])
                    latest_ai_response = None
                    player_commands = []
                    historical_summary = state_info['state'].get("historical_summary", [])

                    # Handle initial game_log that may be a list of strings (legacy) or dicts (new)
                    if isinstance(game_log, list) and len(game_log) > 0:
                        # If the first entry is a string, treat it as the initial AI response
                        if isinstance(game_log[0], str):
                            latest_ai_response = game_log[0]
                        else:
                            # Otherwise, use the previous logic (look for type == "ai")
                            for entry in game_log:
                                if isinstance(entry, dict):
                                    if entry.get("type") == "ai":
                                        latest_ai_response = entry.get("content")
                                    elif entry.get("type") == "player":
                                        player_commands.append({
                                            "user_id": entry.get("user_id"),
                                            "content": entry.get("content")
                                        })
                            # If multiple AI entries, take the last one
                            if any(e.get("type") == "ai" for e in game_log if isinstance(e, dict)):
                                latest_ai_response = [e.get("content") for e in game_log if isinstance(e, dict) and e.get("type") == "ai"][-1]
                    # Defensive: ensure player_commands and historical_summary are lists
                    if not isinstance(player_commands, list):
                        player_commands = []
                    if not isinstance(historical_summary, list):
                        historical_summary = []

                    # --- Build player_display_map for mapping user_id to display name (initial state) ---
                    game_players = GamePlayer.query.filter_by(game_id=game_id).options(joinedload(GamePlayer.user)).all()
                    player_display_map = {}
                    for p in game_players:
                        display_name = p.character_name if p.character_name else (p.user.username if p.user else f"Player {p.user_id}")
                        player_display_map[str(p.user_id)] = display_name

                    emit_data = {
                        'state': state_info['state'],
                        'version': state_info['version'],
                        'log': state_info.get('log', []),
                        'actions': state_info.get('actions', []),
                        'total_plot_points_display': total_plot_points_for_display_initial,
                        'completed_plot_points_display_count': completed_plot_points_display_count_initial,
                        'newly_completed_plot_point_message': None, # No new message on initial load
                        # --- New fields for frontend ---
                        'latest_ai_response': latest_ai_response,
                        'player_commands': player_commands,
                        'historical_summary': historical_summary,
                        'player_display_map': player_display_map
                    }
                    current_app.logger.info(f"[socket_service] Emitting 'game_state' (v{emit_data.get('version')}) for game {game_id} to SID {request.sid}. Plot counts: {total_plot_points_for_display_initial} total, {completed_plot_points_display_count_initial} completed.")
                    current_app.logger.debug(f"[socket_service] Full 'game_state' data being emitted to SID {request.sid}: {json.dumps(emit_data)}")
                    emit('game_state', emit_data, room=request.sid)

            except Exception as e:
                current_app.logger.error(f"[socket_service] 'request_state' error (Game {game_id}, SID: {request.sid}): {str(e)}", exc_info=True)
                emit('error', {
                    'message': 'Failed to retrieve game state',
                    'details': str(e)
                }, room=request.sid)

        @socketio.on('update_character_details') # Renamed event
        def handle_update_character_details(data): # Renamed function
            """Handle player updating their character name and description.""" # Updated docstring
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            name = data.get('name', '').strip() # Get name
            description = data.get('description', '').strip() # Get description

            # Basic validation
            if not game_id or not user_id:
                emit('error', {'message': 'Missing game_id or user_id'}, room=request.sid)
                return
            
            # Security check: Ensure the user updating is the one logged in
            if str(current_user.id) != str(user_id):
                 current_app.logger.warning(f"Security Alert: User {current_user.id} attempted to update details for user {user_id} in game {game_id}.") # Updated log
                 emit('error', {'message': 'Authorization error'}, room=request.sid)
                 return

            current_app.logger.info(f"Handling update_character_details for user {user_id} in game {game_id}.") # Updated log

            with current_app.app_context():
                # Find the GamePlayer association
                association = GamePlayer.query.filter_by(game_id=game_id, user_id=user_id).first()

                if not association:
                    current_app.logger.error(f"Update details failed: GamePlayer association not found for user {user_id} in game {game_id}.") # Updated log
                    emit('error', {'message': 'Player not found in this game'}, room=request.sid)
                    return

                # Update the name and description
                association.character_name = name # Update name
                association.character_description = description # Update description
                
                try:
                    db.session.commit()
                    current_app.logger.info(f"Successfully updated character details for user {user_id} in game {game_id}.") # Updated log
                    # Emit confirmation back to the specific user
                    emit('character_details_updated', {'user_id': user_id, 'status': 'success'}, room=request.sid) # Renamed event
                    # Optionally, broadcast the change to the room if needed in the future:
                    # emit('player_details_changed', {'user_id': user_id, 'name': name, 'description': description}, room=game_id)
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Database error updating character details for user {user_id} in game {game_id}: {str(e)}", exc_info=True) # Updated log
                    emit('error', {'message': 'Failed to save details'}, room=request.sid) # Updated message

        @socketio.on('slash_command')
        def handle_slash_command(data):
            game_id = data.get('game_id')
            user_id = data.get('user_id')
            command = data.get('command', '').lower() # Ensure lowercase for command matching
            args = data.get('args', [])

            if not all([game_id, user_id, command]):
                emit('slash_command_response', {
                    'command': command,
                    'type': 'error',
                    'message': 'Missing required fields for slash command (game_id, user_id, command).'
                }, room=request.sid)
                return

            current_app.logger.info(f"Processing slash_command: /{command} {args} from user {user_id} in game {game_id}.")

            with current_app.app_context():
                game = db.session.get(Game, game_id)
                if not game:
                    emit('slash_command_response', {
                        'command': command,
                        'type': 'error',
                        'message': 'Game not found.'
                    }, room=request.sid)
                    return

                # User authentication/validation (optional, but good for security)
                # user = db.session.get(User, user_id)
                # if not user or not current_user.is_authenticated or str(current_user.id) != str(user_id):
                #     emit('slash_command_response', {'command': command, 'type': 'error', 'message': 'Authentication error.'}, room=request.sid)
                #     return

                if command == 'help':
                    available_commands = [
                        "/help - Shows this help message.",
                        "/remaining_plot_points - Shows how many plot points are left.",
                        "/show_plot_points - Shows details of remaining plot points.",
                        "/game_help - Asks the AI for a hint."
                    ]
                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'header': 'Available Slash Commands:', # Optional header for client display
                        'lines': available_commands
                    }, room=request.sid)

                elif command == 'help_debug':
                    debug_commands = [
                        "/debug_plot_points_show_all - Shows all plot points with details.",
                        "/debug_plot_point_complete <plot_point_id> - Mark a plot point as completed.",
                        "/debug_plot_point_uncomplete <plot_point_id> - Mark a plot point as not completed.",
                        "/debug_show_state_data - Show full GameState.state_data JSON."
                    ]
                    # Ensure lines are unique to avoid duplication
                    unique_debug_commands = list(dict.fromkeys(debug_commands))
                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'header': 'Available Debug Slash Commands:',
                        'lines': unique_debug_commands
                    }, room=request.sid)

                elif command == 'remaining_plot_points':
                    campaign = db.session.query(Campaign).filter_by(game_id=game_id).first()
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()

                    if not campaign or not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Could not retrieve game data to calculate plot points.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    completed_plot_points_data = state_data.get('completed_plot_points', [])
                    if not isinstance(completed_plot_points_data, list):
                        completed_plot_points_data = []
                    
                    completed_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id')]
                    
                    major_plot_points_list = campaign.major_plot_points
                    if not isinstance(major_plot_points_list, list):
                        major_plot_points_list = []

                    required_plot_points = [pp for pp in major_plot_points_list if isinstance(pp, dict) and pp.get('required')]
                    remaining_required = [pp for pp in required_plot_points if pp.get('id') not in completed_ids]
                    
                    count = len(remaining_required)
                    total_required = len(required_plot_points)
                    
                    message = f"There are {count} out of {total_required} required plot points remaining."
                    if count == 0 and total_required > 0:
                        message = "All required plot points have been completed!"
                    elif total_required == 0:
                        message = "This campaign does not have any specifically required plot points defined."

                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'message': message
                    }, room=request.sid)

                elif command == 'show_plot_points':
                    campaign = db.session.query(Campaign).filter_by(game_id=game_id).first()
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()

                    if not campaign or not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Could not retrieve game data to show plot points.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    completed_plot_points_data = state_data.get('completed_plot_points', [])
                    if not isinstance(completed_plot_points_data, list):
                        completed_plot_points_data = []
                    
                    completed_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id')]
                    
                    major_plot_points_list = campaign.major_plot_points
                    if not isinstance(major_plot_points_list, list):
                        major_plot_points_list = []

                    plot_point_details_list = []
                    if not major_plot_points_list:
                        message = "No plot points defined for this campaign."
                        plot_point_details_list.append(message)
                    else:
                        for pp in major_plot_points_list:
                            if isinstance(pp, dict):
                                desc = pp.get('description', 'No description')
                                req_status = "Required" if pp.get('required') else "Optional"
                                completion_status = "Completed" if pp.get('id') in completed_ids else "Pending"
                                plot_point_details_list.append(f"- {desc} ({req_status}, {completion_status})")
                        
                        if not plot_point_details_list: # Should not happen if major_plot_points_list was not empty
                             message = "All plot points have been completed or no plot points to show."
                        else:
                             message = "Plot Points Status:" # Header for the list

                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'header': message, # Use message as a header
                        'lines': plot_point_details_list # Send as a list of strings
                    }, room=request.sid)

                elif command == 'game_help':
                    campaign = db.session.query(Campaign).filter_by(game_id=game_id).first()
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()

                    if not campaign or not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Could not retrieve game data to provide a hint.'
                        }, room=request.sid)
                        return # Early exit

                    hint_result = ai_service.get_ai_hint(game_state=game_state_obj, campaign=campaign)

                    if hint_result:
                        hint_text, model_used, usage_data = hint_result
                        current_app.logger.info(f"AI Hint for game {game_id}: '{hint_text}' (model: {model_used})")
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'hint', # Specific type for hints
                            'message': hint_text
                        }, room=request.sid)
                    else:
                        current_app.logger.error(f"Failed to get AI hint for game {game_id}.")
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Sorry, I could not come up with a hint right now.'
                        }, room=request.sid)

                # Developer debug commands for plot points and state data
                elif command == 'debug_plot_points_show_all':
                    campaign = db.session.query(Campaign).filter_by(game_id=game_id).first()
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()

                    if not campaign or not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Could not retrieve game data to show plot points.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    completed_plot_points_data = state_data.get('completed_plot_points', [])
                    if not isinstance(completed_plot_points_data, list):
                        completed_plot_points_data = []

                    completed_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id')]

                    major_plot_points_list = campaign.major_plot_points
                    if not isinstance(major_plot_points_list, list):
                        major_plot_points_list = []

                    # Prepare raw plot point data for debugging
                    raw_plot_points_info = []
                    for pp in major_plot_points_list:
                        if isinstance(pp, dict):
                            raw_plot_points_info.append({
                                'id': pp.get('id'),
                                'description': pp.get('description'),
                                'required': pp.get('required'),
                                'completed': pp.get('id') in completed_ids
                            })

                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'header': 'Debug: All Plot Points (Raw Data)',
                        'lines': [str(pp) for pp in raw_plot_points_info]
                    }, room=request.sid)

                elif command == 'debug_plot_point_complete':
                    if not args or len(args) < 1:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Usage: /debug_plot_point_complete <plot_point_id>'
                        }, room=request.sid)
                        return

                    plot_point_id = args[0]
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()
                    if not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Game state not found.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    if 'completed_plot_points' not in state_data or not isinstance(state_data['completed_plot_points'], list):
                        state_data['completed_plot_points'] = []

                    # Check if already completed
                    if any(pp.get('id') == plot_point_id for pp in state_data['completed_plot_points'] if isinstance(pp, dict)):
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'info',
                            'message': f'Plot point {plot_point_id} is already marked as completed.'
                        }, room=request.sid)
                        return

                    # Find plot point object from campaign
                    campaign = db.session.query(Campaign).filter_by(game_id=game_id).first()
                    if not campaign:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Campaign not found.'
                        }, room=request.sid)
                        return

                    plot_point_obj = next((pp for pp in campaign.major_plot_points if isinstance(pp, dict) and pp.get('id') == plot_point_id), None)
                    if not plot_point_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': f'Plot point ID {plot_point_id} not found in campaign.'
                        }, room=request.sid)
                        return

                    # Mark as completed
                    state_data['completed_plot_points'].append(plot_point_obj)
                    game_state_obj.state_data = state_data
                    attributes.flag_modified(game_state_obj, 'state_data')
                    db.session.commit()

                    # Broadcast updated state to all players in the game room
                    updated_state_info = game_state_service.get_state(game_id)
                    emit('game_state', updated_state_info, room=game_id)

                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'message': f'Plot point {plot_point_id} marked as completed.'
                    }, room=request.sid)

                elif command == 'debug_plot_point_uncomplete':
                    if not args or len(args) < 1:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Usage: /debug_plot_point_uncomplete <plot_point_id>'
                        }, room=request.sid)
                        return

                    plot_point_id = args[0]
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()
                    if not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Game state not found.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    if 'completed_plot_points' not in state_data or not isinstance(state_data['completed_plot_points'], list):
                        state_data['completed_plot_points'] = []

                    # Remove plot point if present
                    before_count = len(state_data['completed_plot_points'])
                    state_data['completed_plot_points'] = [pp for pp in state_data['completed_plot_points'] if not (isinstance(pp, dict) and pp.get('id') == plot_point_id)]
                    after_count = len(state_data['completed_plot_points'])

                    if before_count == after_count:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'info',
                            'message': f'Plot point {plot_point_id} was not marked as completed.'
                        }, room=request.sid)
                        return

                    game_state_obj.state_data = state_data
                    attributes.flag_modified(game_state_obj, 'state_data')
                    db.session.commit()

                    # Broadcast updated state to all players in the game room
                    updated_state_info = game_state_service.get_state(game_id)
                    emit('game_state', updated_state_info, room=game_id)

                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'message': f'Plot point {plot_point_id} marked as not completed.'
                    }, room=request.sid)

                elif command == 'debug_show_state_data':
                    game_state_obj = db.session.query(GameState).filter_by(game_id=game_id).first()
                    if not game_state_obj:
                        emit('slash_command_response', {
                            'command': command,
                            'type': 'error',
                            'message': 'Game state not found.'
                        }, room=request.sid)
                        return

                    state_data = game_state_obj.state_data or {}
                    # Split the JSON string into lines for the 'lines' parameter
                    state_data_json_lines = json.dumps(state_data, indent=2).splitlines()
                    emit('slash_command_response', {
                        'command': command,
                        'type': 'info',
                        'header': 'Debug: Full GameState.state_data',
                        'lines': state_data_json_lines # Pass the list of lines
                    }, room=request.sid)
                else:
                    emit('slash_command_response', {
                        'command': command,
                        'type': 'error',
                        'message': f"Unknown command: /{command}"
                    }, room=request.sid)

        @socketio.on('change_difficulty')
        def handle_change_difficulty(data):
            """Handle game creator changing the game difficulty."""
            game_id = data.get('game_id')
            new_difficulty = data.get('new_difficulty')
            user_id_from_client = data.get('user_id') # User ID sent by the client

            current_app.logger.info(f"Handling 'change_difficulty' event for game {game_id} to '{new_difficulty}' by user {user_id_from_client} (current_user: {current_user.id if current_user.is_authenticated else 'Guest'}).")

            if not all([game_id, new_difficulty, user_id_from_client]):
                emit('difficulty_change_ack', {'status': 'error', 'message': 'Missing data for difficulty change.'}, room=request.sid)
                return

            if not current_user.is_authenticated or str(current_user.id) != str(user_id_from_client):
                current_app.logger.warning(f"User {current_user.id} (client) vs {current_user.id} (server) mismatch or not authenticated for change_difficulty.")
                emit('difficulty_change_ack', {'status': 'error', 'message': 'Authentication error.'}, room=request.sid)
                return

            valid_difficulties = ['Easy', 'Normal', 'Hard']
            if new_difficulty not in valid_difficulties:
                current_app.logger.warning(f"Invalid difficulty level '{new_difficulty}' received for game {game_id}.")
                emit('difficulty_change_ack', {'status': 'error', 'message': 'Invalid difficulty level.'}, room=request.sid)
                return

            with current_app.app_context():
                game = db.session.get(Game, game_id)

                if not game:
                    current_app.logger.error(f"Game {game_id} not found for difficulty change.")
                    emit('difficulty_change_ack', {'status': 'error', 'message': 'Game not found.'}, room=request.sid)
                    return

                if str(game.created_by) != str(current_user.id):
                    current_app.logger.warning(f"User {current_user.id} attempted to change difficulty for game {game_id} but is not the creator ({game.created_by}).")
                    emit('difficulty_change_ack', {'status': 'error', 'message': 'Only the game creator can change difficulty.'}, room=request.sid)
                    return
                
                if game.status != 'in_progress':
                    current_app.logger.warning(f"Attempt to change difficulty for game {game_id} that is not 'in_progress' (status: {game.status}).")
                    # Allow changing difficulty even if not in_progress, e.g. in lobby or if game concluded but want to see effect on logs.
                    # If strict 'in_progress' check is desired, uncomment below:
                    # emit('difficulty_change_ack', {'status': 'error', 'message': 'Difficulty can only be changed for games in progress.'}, room=request.sid)
                    # return

                try:
                    game.current_difficulty = new_difficulty
                    db.session.commit()
                    current_app.logger.info(f"Game {game_id} difficulty successfully changed to '{new_difficulty}' by creator {current_user.id}.")
                    emit('difficulty_change_ack', {
                        'status': 'success',
                        'message': f'Difficulty changed to {new_difficulty}.',
                        'new_difficulty': new_difficulty
                    }, room=request.sid)
                    
                    # Optionally, broadcast to the room if other players need to be aware (e.g., for UI updates)
                    # emit('game_difficulty_updated', {'game_id': game_id, 'new_difficulty': new_difficulty}, room=game_id)

                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error changing difficulty for game {game_id}: {str(e)}", exc_info=True)
                    emit('difficulty_change_ack', {'status': 'error', 'message': 'Failed to save difficulty change.'}, room=request.sid)
