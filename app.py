from flask import Flask, jsonify, request, render_template, redirect, url_for # Import redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room # Import emit, join_room, leave_room
from config import config_by_name # Import config_by_name
from database import init_db # Only import init_db, not db directly
from models import User, Game, GamePlayer, GameState # Import User, Game, GamePlayer, GameState models
from flask_bcrypt import Bcrypt # Import Flask-Bcrypt
from flask_jwt_extended import JWTManager, get_jwt_identity, jwt_required # Import jwt_required
from datetime import datetime # Import datetime
# Import blueprints later to avoid circular imports
from flask.json.provider import DefaultJSONProvider # Import DefaultJSONProvider
from flask_migrate import Migrate # Import Flask-Migrate
import os # Import os to get FLASK_ENV
from services.ai_service import AIService # Import AIService
from services.game_state_service import GameStateService # Import GameStateService
from flask import current_app # Import current_app

app = Flask(__name__)
# Load configuration based on FLASK_ENV
env_name = os.environ.get('FLASK_ENV', 'development') # Default to 'development'
app.config.from_object(config_by_name[env_name])

#app.json_encoder = DefaultJSONProvider.default_json_encoder # Set the JSON encoder for Flask 2.x compatibility
socketio = SocketIO(app)
bcrypt = Bcrypt(app) # Initialize Bcrypt with the app

# Configure Flask-JWT-Extended
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False  # Should be True in production over HTTPS
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False # Set to True and handle CSRF if forms submit directly to protected cookie routes
                                         # For JS fetch to API, CSRF might be handled differently or via custom headers.
                                         # If only API endpoints are protected and called by JS, this might be okay as False.
                                         # But if @jwt_required is on HTML serving routes, CSRF is more relevant.
jwt = JWTManager(app) # Initialize Flask-JWT-Extended

# Initialize AI and GameState services and attach to app context
app.ai_service = AIService(app.config)
app.game_state_service = GameStateService(app.ai_service, socketio) # Pass socketio instance
app.socketio = socketio

# Custom unauthorized loader for JWT
@jwt.unauthorized_loader
def unauthorized_callback(error_string):
    # If the request seems to want HTML, redirect to login page
    if 'text/html' in request.accept_mimetypes:
        return redirect(url_for('auth.login_page', next=request.path))
    # Otherwise, return the default JSON error
    return jsonify(msg=error_string), 401

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    # If the request seems to want HTML, redirect to login page
    if 'text/html' in request.accept_mimetypes:
        # You might want to add a flash message here
        return redirect(url_for('auth.login_page', error="invalid_token", next=request.path))
    # Otherwise, return the default JSON error
    return jsonify(msg=error_string), 422 # 422 Unprocessable Entity for invalid token

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    # If the request seems to want HTML, redirect to login page
    if 'text/html' in request.accept_mimetypes:
        # You might want to add a flash message here
        return redirect(url_for('auth.login_page', error="expired_token", next=request.path))
    # Otherwise, return the default JSON error
    return jsonify(msg="Token has expired"), 401


init_db(app) # Initialize database
from database import db # Import db for Flask-Migrate
migrate = Migrate(app, db) # Initialize Flask-Migrate

# Register blueprints after app and extensions are initialized
from routes.auth import auth_bp, user_bp # Import both auth and user blueprints
from routes.templates import templates_bp # Import templates blueprint
from routes.games import games_bp # Import games blueprint

app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(templates_bp)
app.register_blueprint(games_bp)

# Frontend Routes
@app.route('/')
@jwt_required() # Require login
def index_route(): # Explicitly named to match layout.html
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    # In a real app, you'd fetch actual games and templates for the user
    active_games = [] # Placeholder
    templates = []    # Placeholder
    return render_template('dashboard.html', current_user=user, active_games=active_games, templates=templates)

@app.route('/dashboard')
@jwt_required() # Require login
def dashboard_route(): # Explicitly named to match layout.html
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    # In a real app, you'd fetch actual games and templates for the user
    active_games = [] # Placeholder
    templates = []    # Placeholder
    return render_template('dashboard.html', current_user=user, active_games=active_games, templates=templates)

# Placeholder routes for nav links - to be implemented later
@app.route('/templates-page') # Using a distinct path from the API blueprint
@jwt_required() # Protect this page
def templates_route():
    current_user_id = get_jwt_identity() # Needed for context if current_user is used in layout
    user = db.session.get(User, current_user_id)
    return render_template('templates_page.html', current_user=user)

@app.route('/games-page') # Using a distinct path from the API blueprint
@jwt_required() # Protect this page
def games_route():
    # The action query parameter can be used by the frontend JS to determine initial state
    # e.g., show create form if action=create
    current_user_id = get_jwt_identity() # Needed for context if current_user is used in layout
    user = db.session.get(User, current_user_id)
    return render_template('games_page.html', current_user=user)

@app.route('/games/create')
@jwt_required()
def create_game_page_route():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    # The actual template list will be fetched by JS on the client-side
    return render_template('create_game_page.html', current_user=user)

@app.route('/games/<int:game_id>/lobby')
@jwt_required()
def lobby_page_route(game_id):
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Basic authorization: ensure the current user is part of this game
    # More complex logic might be needed depending on requirements (e.g., is game public? invite only?)
    game_player_entry = GamePlayer.query.filter_by(game_id=game.id, user_id=current_user_id).first()
    if not game_player_entry and game.creator_user_id != current_user_id:
        # If not a player and not the creator, deny access (or redirect with a message)
        # For simplicity, redirecting to dashboard. A flash message would be good here.
        return redirect(url_for('dashboard_route'))


    return render_template('lobby_page.html', current_user=user, game=game)

@app.route('/play/<int:game_id>')
@jwt_required()
def play_page_route(game_id):
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"msg": "Game not found"}), 404

    # Ensure user is a player in this game
    game_player_entry = GamePlayer.query.filter_by(game_id=game.id, user_id=current_user_id).first()
    if not game_player_entry:
        return redirect(url_for('dashboard_route')) # Or show an error

    # Extract required properties for the template
    gm_persona = 'Unknown GM' # Default value
    campaign_charter_data = {}
    
    current_app.logger.debug(f"Debug: Type of game.campaign_charter: {type(game.campaign_charter)}")
    current_app.logger.debug(f"Debug: Content of game.campaign_charter: {game.campaign_charter}")

    if game.campaign_charter:
        if isinstance(game.campaign_charter, str):
            try:
                campaign_charter_data = json.loads(game.campaign_charter)
            except json.JSONDecodeError:
                current_app.logger.error(f"Failed to decode campaign_charter for game {game.id}: {game.campaign_charter}")
        elif isinstance(game.campaign_charter, dict):
            campaign_charter_data = game.campaign_charter
    
    gm_persona = campaign_charter_data.get('ai_gm_persona_for_campaign', 'Unknown GM')
    
    cumulative_cost = game.cumulative_cost or 0.0

    game_state = GameState.query.filter_by(id=game.current_game_state_id).first()
    
    # Extract data for the information panel
    npcs = game_state.active_npcs if game_state else []
    objectives = campaign_charter_data.get('critical_path_objectives') or campaign_charter_data.get('initial_state_elements', {}).get('initial_quests', [])
    # Placeholder for objective states and lore, assuming they will be in world_state
    objective_states = game_state.completed_objectives if game_state and game_state.completed_objectives else []
    lore_documents = game_state.discovered_lore_items if game_state and game_state.discovered_lore_items else []


    return render_template(
        'play_page.html',
        current_user=user,
        game=game,
        gm_persona=gm_persona,
        cumulative_cost=cumulative_cost,
        game_name=game.game_name,
        players=[player.to_dict() for player in game.game_players],
        npcs=npcs,
        objectives=objectives,
        objective_states=objective_states,
        lore_documents=lore_documents
    )

    # Socket.IO event handlers
    @socketio.on('connect')
    def handle_connect():
        print('Client connected:', request.sid)
        emit('connection_ack', {'message': 'Successfully connected to QuestForge Socket.IO server!'})

    @socketio.on('update_npc_status')
    @jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
    def handle_update_npc_status(data):
        """Handles updating NPC status"""
        current_user_id = get_jwt_identity()
        if not current_user_id:
            emit('error', {'message': 'Authentication required.'}, room=request.sid)
            return

        game_id = data.get('game_id')
        npc_id = data.get('npc_id')
        new_status = data.get('new_status')

        if not game_id or not npc_id or not new_status:
            emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
            return

        try:
            current_app.game_state_service.update_npc_status(game_id, npc_id, new_status)
        except Exception as e:
            emit('error', {'message': f'Failed to update NPC status: {str(e)}'}, room=request.sid)

    @socketio.on('move_npc')
    @jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
    def handle_move_npc(data):
        """Handles moving NPC to new location"""
        current_user_id = get_jwt_identity()
        if not current_user_id:
            emit('error', {'message': 'Authentication required.'}, room=request.sid)
            return

        game_id = data.get('game_id')
        npc_id = data.get('npc_id')
        new_location = data.get('new_location')

        if not game_id or not npc_id or not new_location:
            emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
            return

        try:
            current_app.game_state_service.move_npc(game_id, npc_id, new_location)
        except Exception as e:
            emit('error', {'message': f'Failed to move NPC: {str(e)}'}, room=request.sid)

@socketio.on('send_chat_message')
@jwt_required(optional=True) # Or your preferred auth method
def handle_send_chat_message(data):
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required for chat.'})
        return

    game_id = data.get('game_id')
    message = data.get('message')
    if not game_id or not message:
        return # Ignore empty messages or requests

    player = GamePlayer.query.filter_by(game_id=game_id, user_id=int(current_user_id_str)).first()
    if not player:
        return # User is not a player in this game

    room_name = f"game_{game_id}"
    emit('new_chat_message', {
        'sender_name': player.character_name,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }, to=room_name)


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('join_game_room')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False) # Add jwt_required for socket events if needed
def handle_join_game_room(data):
    """
    Handles a client joining a specific game room.
    Expects data: {'game_id': 'some_game_id'}
    Requires JWT for user identification.
    """
    current_user_id = get_jwt_identity() # Get user identity from JWT
    if not current_user_id:
        emit('error', {'message': 'Authentication required to join game room.'})
        return

    game_id = data.get('game_id')
    if not game_id:
        emit('error', {'message': 'game_id missing from join_game_room request.'})
        return

    # Here, you might want to verify if the user is actually part of this game
    # For now, we'll just let them join the room
    
    room_name = f"game_{game_id}"
    join_room(room_name)
    print(f"User {current_user_id} (sid: {request.sid}) joined room: {room_name}")
    
    # Notify the client they've joined
    emit('joined_room', {'room': room_name, 'user_id': current_user_id, 'message': f'Successfully joined game room {game_id}.'}, room=request.sid)
    
    # Notify others in the room (optional)
    # emit('player_joined', {'user_id': current_user_id, 'message': f'Player {current_user_id} has joined the game.'}, to=room_name, skip_sid=request.sid)


@socketio.on('leave_game_room')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_leave_game_room(data):
    """
    Handles a client leaving a specific game room.
    Expects data: {'game_id': 'some_game_id'}
    """
    current_user_id = get_jwt_identity()
    if not current_user_id:
        # Silently ignore if not authenticated, or emit error
        return

    game_id = data.get('game_id')
    if not game_id:
        # Silently ignore if no game_id, or emit error
        return
        
    room_name = f"game_{game_id}"
    leave_room(room_name)
    print(f"User {current_user_id} (sid: {request.sid}) left room: {room_name}")

    # Notify the client they've left
    emit('left_room', {'room': room_name, 'user_id': current_user_id, 'message': f'Successfully left game room {game_id}.'}, room=request.sid)

    # Notify others in the room (optional)
    # emit('player_left', {'user_id': current_user_id, 'message': f'Player {current_user_id} has left the game.'}, to=room_name, skip_sid=request.sid)


@socketio.on('player_ready')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_player_ready(data):
    """
    Handles a player signaling they are ready.
    Expects data: {'game_id': 'some_game_id', 'is_ready': true/false}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    is_ready = data.get('is_ready', False) # Default to False if not provided
    
    if not game_id:
        emit('error', {'message': 'game_id missing.'}, room=request.sid)
        return

    game_player = GamePlayer.query.filter_by(game_id=game_id, user_id=int(current_user_id_str)).first()
    if not game_player:
        emit('error', {'message': 'Player not found in this game.'}, room=request.sid)
        return

    game_player.ready_status = is_ready
    db.session.commit()

    room_name = f"game_{game_id}"
    print(f"User {current_user_id_str} in game {game_id} readiness: {is_ready}")
    emit('player_readiness_updated', {
        'user_id': current_user_id_str, 
        'game_player_id': game_player.id,
        'is_ready': is_ready
    }, to=room_name)


@socketio.on('start_game_request')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_start_game_request(data):
    """
    Handles a request from the game creator to start the game.
    Expects data: {'game_id': 'some_game_id'}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    if not game_id:
        emit('error', {'message': 'game_id missing.'}, room=request.sid)
        return

    game = db.session.get(Game, game_id)
    if not game:
        emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    
    # Refresh the game object to ensure relationships like game_players are loaded
    db.session.refresh(game)

    if game.creator_user_id != int(current_user_id_str):
        emit('error', {'message': 'Only the game creator can start the game.'}, room=request.sid)
        return

    if game.started_at:
        emit('error', {'message': 'Game has already started.'}, room=request.sid)
        return

    # Optional: Check if all players are ready
    # all_players_ready = all(gp.ready_status for gp in game.game_players)
    # if not all_players_ready:
    #     emit('error', {'message': 'Not all players are ready.'}, room=request.sid)
    #     return
        
    game.started_at = datetime.utcnow()
    
    if not game.current_game_state_id:
        # Ensure campaign_charter is a dictionary
        campaign_charter_data = game.campaign_charter
        if isinstance(campaign_charter_data, str):
            try:
                campaign_charter_data = json.loads(campaign_charter_data)
            except json.JSONDecodeError:
                current_app.logger.error(f"Failed to decode campaign_charter for game {game.id} during game start.")
                campaign_charter_data = {} # Fallback to empty dict

        initial_narration = campaign_charter_data.get('initial_player_context', f"The adventure in '{campaign_charter_data.get('campaign_name', 'this mysterious place')}' begins...")
        
        # Initialize active_npcs from campaign_charter
        initial_npcs = campaign_charter_data.get('initial_state_elements', {}).get('key_npcs', [])
        current_app.logger.debug(f"Debug: Initial NPCs for GameState: {initial_npcs}")

        # Initialize player_states from existing GamePlayers
        initial_player_states = []
        for player in game.game_players:
            initial_player_states.append({
                "user_id": player.user_id,
                "game_player_id": player.id,
                "character_name": player.character_name,
                "character_sheet": player.character_sheet,
                "ready_status": player.ready_status,
                "current_location": campaign_charter_data.get('initial_state_elements', {}).get('starting_location', 'Unknown Location'),
                "status_effects": [],
                "inventory": []
            })
        current_app.logger.debug(f"Debug: Initial Player States for GameState: {initial_player_states}")

        initial_game_state = GameState(
            game_id=game.id,
            current_player_id=game.creator_user_id, # Creator starts first
            turn_number=1,
            current_story_summary=initial_narration,
            current_location=campaign_charter_data.get('initial_state_elements', {}).get('starting_location', 'Unknown Location'),
            active_npcs=initial_npcs, # Pass directly to constructor
            player_states=initial_player_states, # Pass directly to constructor
            game_log=[{"type": "GM_NARRATIVE", "timestamp": datetime.utcnow().isoformat(), "content": initial_narration}]
        )
        current_app.logger.debug(f"Debug: GameState object before add - active_npcs: {initial_game_state.active_npcs}")
        current_app.logger.debug(f"Debug: GameState object before add - player_states: {initial_game_state.player_states}")
        db.session.add(initial_game_state)
        db.session.flush() # Get ID before commit
        game.current_game_state_id = initial_game_state.id
    
    db.session.commit()

    # Only expunge if initial_game_state was created
    if 'initial_game_state' in locals() and initial_game_state is not None:
        db.session.expunge(initial_game_state)

    # Explicitly fetch the GameState object again to ensure it's fresh from DB
    game_state_obj = db.session.get(GameState, game.current_game_state_id)
    if game_state_obj:
        current_app.logger.debug(f"Debug: GameState re-fetched from DB - active_npcs: {game_state_obj.active_npcs}")
        current_app.logger.debug(f"Debug: GameState re-fetched from DB - player_states: {game_state_obj.player_states}")
    else:
        current_app.logger.error(f"Debug: Re-fetched GameState is None for game {game.id}")

    room_name = f"game_{game_id}"
    print(f"Game {game_id} started by user {current_user_id_str}.")
    
    # Broadcast game started event with initial game state (or relevant parts)
    game_state_obj = db.session.get(GameState, game.current_game_state_id) if game.current_game_state_id else None
    initial_story_content = game_state_obj.current_story_summary if game_state_obj else "The adventure begins..."
    
    emit('game_started', {
        'game_id': game_id,
        'message': 'The game has started!',
        'started_at': game.started_at.isoformat(),
        'initial_story': initial_story_content,
        'initial_game_state': game_state_obj.to_dict() if game_state_obj else None
    }, to=room_name)


@socketio.on('submit_player_action')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_submit_player_action(data):
    """
    Handles a player submitting an action.
    Expects data: {'game_id': 'some_game_id', 'game_player_id': id, 'action_text': '...'}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = int(data.get('game_id')) # Cast to int
    game_player_id = data.get('game_player_id') # This should be the GamePlayer ID
    action_text = data.get('action_text')

    if not action_text: # game_player_id is no longer strictly required from frontend
        emit('error', {'message': 'Missing action_text.'}, room=request.sid)
        return

    # Find the GamePlayer based on game_id and current_user_id
    print(f"Debug Backend - Querying GamePlayer with game_id={game_id} (type: {type(game_id)}) and user_id={int(current_user_id_str)} (type: {type(int(current_user_id_str))})")
    game_player = GamePlayer.query.filter_by(game_id=game_id, user_id=int(current_user_id_str)).first()
    if not game_player:
        print(f"Debug Backend - GamePlayer not found for game_id={game_id}, user_id={int(current_user_id_str)}")
        emit('error', {'message': 'You are not a player in this game.'}, room=request.sid)
        return
    
    game = db.session.get(Game, game_id)
    if not game or not game.started_at or game.completed_at:
        emit('error', {'message': 'Game not active or does not exist.'}, room=request.sid)
        return

    # Call GameStateService to process the action
    # The service will handle emitting events like 'skill_check_initiated', 'dice_roll_result', 'narrative_update'
    result, error = current_app.game_state_service.process_player_action(
        game_id=game_id, 
        game_player_id=game_player_id, 
        action_text=action_text
    )

    if error:
        # Send error back to the originating client
        emit('action_error', {'message': error, 'game_id': game_id, 'game_player_id': game_player_id}, room=request.sid)
        return

    # Send an acknowledgment to the originating client that their action was received and is being processed.
    # The actual game updates will be broadcast by GameStateService.
    emit('action_received_ack', {
        'game_id': game_id,
        'game_player_id': game_player_id,
        'action_text': action_text,
        'message': 'Your action has been received and is being processed.'
    }, room=request.sid)
    
    # The 'result' variable from process_player_action contains detailed info like AI narrative and cost.
    # This could be logged or used for other server-side purposes if needed, but broadcasts are handled by the service.
    print(f"Action from player {game_player_id} in game {game_id} processed by service. Result: {result}")

# NPC Management Event Handlers

@socketio.on('update_npc_status')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_update_npc_status(data):
    """
    Updates the status of an NPC in the current game state.
    Expects data: {'game_id': int, 'npc_id': str, 'new_status': str}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    npc_id = data.get('npc_id')
    new_status = data.get('new_status')

    if not game_id or not npc_id or not new_status:
        emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
        return

    try:
        current_app.game_state_service.update_npc_status(game_id, npc_id, new_status)
        emit('success', {'message': 'NPC status updated successfully'}, room=request.sid)
    except Exception as e:
        emit('error', {'message': f'Failed to update NPC status: {str(e)}'}, room=request.sid)

@socketio.on('move_npc')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_move_npc(data):
    """
    Moves an NPC to a new location.
    Expects data: {'game_id': int, 'npc_id': str, 'new_location': str}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    npc_id = data.get('npc_id')
    new_location = data.get('new_location')

    if not game_id or not npc_id or not new_location:
        emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
        return

    try:
        current_app.game_state_service.move_npc(game_id, npc_id, new_location)
        emit('success', {'message': 'NPC moved successfully'}, room=request.sid)
    except Exception as e:
        emit('error', {'message': f'Failed to move NPC: {str(e)}'}, room=request.sid)

@socketio.on('add_npc_to_scene')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_add_npc_to_scene(data):
    """
    Adds a new NPC to the current scene.
    Expects data: {'game_id': int, 'npc_data': dict}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    npc_data = data.get('npc_data')

    if not game_id or not npc_data:
        emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
        return

    try:
        current_app.game_state_service.add_npc_to_scene(game_id, npc_data)
        emit('success', {'message': 'NPC added to scene successfully'}, room=request.sid)
    except Exception as e:
        emit('error', {'message': f'Failed to add NPC: {str(e)}'}, room=request.sid)

@socketio.on('remove_npc_from_scene')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_remove_npc_from_scene(data):
    """
    Removes an NPC from the current scene.
    Expects data: {'game_id': int, 'npc_id': str}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    npc_id = data.get('npc_id')

    if not game_id or not npc_id:
        emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
        return

    try:
        current_app.game_state_service.remove_npc_from_scene(game_id, npc_id)
        emit('success', {'message': 'NPC removed from scene successfully'}, room=request.sid)
    except Exception as e:
        emit('error', {'message': f'Failed to remove NPC: {str(e)}'}, room=request.sid)

@socketio.on('modify_npc_details')
@jwt_required(optional=True, fresh=False, refresh=False, locations=None, verify_type=True, skip_revocation_check=False)
def handle_modify_npc_details(data):
    """
    Modifies an NPC's details.
    Expects data: {'game_id': int, 'npc_id': str, 'updated_fields': dict}
    """
    current_user_id_str = get_jwt_identity()
    if not current_user_id_str:
        emit('error', {'message': 'Authentication required.'}, room=request.sid)
        return

    game_id = data.get('game_id')
    npc_id = data.get('npc_id')
    updated_fields = data.get('updated_fields')

    if not game_id or not npc_id or not updated_fields:
        emit('error', {'message': 'Missing required parameters.'}, room=request.sid)
        return

    try:
        current_app.game_state_service.modify_npc_details(game_id, npc_id, updated_fields)
        emit('success', {'message': 'NPC details updated successfully'}, room=request.sid)
    except Exception as e:
        emit('error', {'message': f'Failed to modify NPC: {str(e)}'}, room=request.sid)

# AI Context Integration
@socketio.on('request_ai_context')
@jwt_required(optional=True)
def handle_request_ai_context(data):
    """Provides AI with current game state including NPCs"""
    game_id = data.get('game_id')
    if not game_id:
        return
    
    game_state = GameState.query.filter_by(game_id=game_id).order_by(GameState.updated_at.desc()).first()
    if not game_state:
        return
        
    emit('ai_context_update', {
        'active_npcs': game_state.active_npcs or [],
        'player_states': game_state.player_states or [],
        'current_location': game_state.current_location or ''
    }, room=f"game_{game_id}")

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5014)
