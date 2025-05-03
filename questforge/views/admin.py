from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
import os
import json
from datetime import datetime

from ..extensions import db
from ..models import Game, Campaign, GamePlayer, GameState, User, Template # Import necessary models

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Helper function to serialize SQLAlchemy objects, handling datetime
def alchemy_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Add other type handlers if needed
    # Let the default encoder handle the rest, which might raise TypeError for unhandled types
    # Consider using marshmallow for more robust serialization if complexity increases

# Helper function to get seed file path
def get_seed_data_path():
    return os.path.join(current_app.instance_path, 'seed_data')

# Route to display admin panel and list existing seed files
@admin_bp.route('/')
@login_required
def index():
    # Add admin check later if needed
    # if not current_user.is_admin:
    #     flash('You do not have permission to access the admin area.', 'danger')
    #     return redirect(url_for('main.home'))

    seed_data_path = get_seed_data_path()
    seed_files = []
    if os.path.exists(seed_data_path):
        try:
            seed_files = [f for f in os.listdir(seed_data_path) if f.endswith('.json')]
        except OSError as e:
            flash(f"Error reading seed data directory: {e}", "danger")
            
    return render_template('admin/admin.html', title="Admin Panel", seed_files=seed_files)

# Route to handle exporting game data
@admin_bp.route('/export', methods=['POST'])
@login_required
def export_seed():
    # Add admin check later if needed
    # if not current_user.is_admin:
    #     flash('You do not have permission to access the admin area.', 'danger')
    #     return redirect(url_for('main.home'))

    game_id = request.form.get('game_id')
    seed_name = request.form.get('seed_name')

    if not game_id or not seed_name:
        flash('Game ID and Seed Name are required.', 'warning')
        return redirect(url_for('admin.index'))

    # Basic sanitization for seed_name (allow letters, numbers, underscore, hyphen)
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]+$', seed_name):
        flash('Invalid characters in Seed File Name. Use only letters, numbers, underscores, hyphens.', 'warning')
        return redirect(url_for('admin.index'))

    try:
        game_id = int(game_id)
        # Fetch game with related data (adjust eager loading as needed)
        game = Game.query.options(
            db.joinedload(Game.campaign),
            db.joinedload(Game.player_associations).joinedload(GamePlayer.user), # Load players and their users
            # Load only the latest game state? Or all? Let's start with latest.
            # db.joinedload(Game.game_states) 
        ).get(game_id)

        if not game:
            flash(f'Game with ID {game_id} not found.', 'danger')
            return redirect(url_for('admin.index'))

        # Fetch the latest game state separately if not eager loaded
        latest_game_state = GameState.query.filter_by(game_id=game_id).order_by(GameState.last_updated.desc()).first()

        # --- Prepare data for serialization ---
        # Manually construct dictionaries to avoid circular refs and control data
        game_data = {k: getattr(game, k) for k in game.__table__.columns.keys()}
        # Remove sensitive or irrelevant fields if necessary
        game_data.pop('created_by', None) # Example: remove creator ID if not needed for seeding

        campaign_data = None
        if game.campaign:
            campaign_data = {k: getattr(game.campaign, k) for k in game.campaign.__table__.columns.keys()}
            campaign_data.pop('game_id', None) # Avoid redundancy

        game_players_data = []
        for assoc in game.player_associations:
            player_data = {k: getattr(assoc, k) for k in assoc.__table__.columns.keys()}
            player_data.pop('game_id', None)
            # Include basic user info if needed for context, but maybe not for seeding?
            # player_data['user'] = {'id': assoc.user.id, 'username': assoc.user.username}
            game_players_data.append(player_data)

        game_state_data = None
        if latest_game_state:
            game_state_data = {k: getattr(latest_game_state, k) for k in latest_game_state.__table__.columns.keys()}
            game_state_data.pop('game_id', None)
            # campaign_id might be useful if campaign isn't always present
            # game_state_data.pop('campaign_id', None) 

        seed_content = {
            'exported_at': datetime.utcnow(),
            'source_game_id': game_id,
            'game': game_data,
            'campaign': campaign_data,
            'game_players': game_players_data,
            'game_state': game_state_data # Store only the latest state for seeding
        }

        # --- Save to file ---
        seed_data_path = get_seed_data_path()
        os.makedirs(seed_data_path, exist_ok=True) # Ensure directory exists
        
        filename = f"{seed_name}.json"
        filepath = os.path.join(seed_data_path, filename)

        with open(filepath, 'w') as f:
            # Use default=alchemy_encoder to handle datetime objects
            json.dump(seed_content, f, indent=4, default=alchemy_encoder) 

        flash(f'Successfully exported game {game_id} data to {filename}.', 'success')

    except ValueError:
        flash('Invalid Game ID format.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error exporting seed data for game {game_id}: {e}", exc_info=True)
        flash(f'An error occurred during export: {e}', 'danger')

    return redirect(url_for('admin.index'))

# Helper function to parse datetime strings from JSON
def parse_datetime(value):
    if isinstance(value, str):
        try:
            # Handle potential timezone info if present (e.g., Z or +00:00)
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except ValueError:
            return None # Or raise an error, or return original string
    return value

# Route to handle importing game data from seed file
@admin_bp.route('/import', methods=['POST'])
@login_required
def import_seed():
    # Add admin check later if needed
    # if not current_user.is_admin:
    #     flash('You do not have permission to access the admin area.', 'danger')
    #     return redirect(url_for('main.home'))

    seed_filename = request.form.get('seed_file')
    new_game_name = request.form.get('new_game_name')

    if not seed_filename or not new_game_name:
        flash('Seed File and New Game Name are required.', 'warning')
        return redirect(url_for('admin.index'))

    seed_data_path = get_seed_data_path()
    filepath = os.path.join(seed_data_path, seed_filename)

    if not os.path.exists(filepath):
        flash(f'Seed file {seed_filename} not found.', 'danger')
        return redirect(url_for('admin.index'))

    try:
        with open(filepath, 'r') as f:
            seed_content = json.load(f)

        # --- Validate Seed Content Structure ---
        required_keys = ['game', 'campaign', 'game_players', 'game_state']
        if not all(key in seed_content for key in required_keys):
            flash(f'Seed file {seed_filename} is missing required data sections.', 'danger')
            return redirect(url_for('admin.index'))
            
        game_data = seed_content['game']
        campaign_data = seed_content['campaign']
        game_players_data = seed_content['game_players']
        game_state_data = seed_content['game_state']

        # --- Create New Game Objects ---
        # 1. Create Game
        # Ensure required fields exist in game_data before creating
        if not all(k in game_data for k in ['template_id', 'status']):
             flash('Seed file game data is missing required fields (template_id, status).', 'danger')
             return redirect(url_for('admin.index'))
             
        # Verify template exists
        template = db.session.get(Template, game_data['template_id'])
        if not template:
             flash(f"Template ID {game_data['template_id']} referenced in seed file does not exist.", 'danger')
             return redirect(url_for('admin.index'))

        new_game = Game(
            name=new_game_name.strip(),
            created_by=current_user.id, # Set current user as creator
            template_id=game_data['template_id'],
            status=game_data.get('status', 'pending'), # Use seeded status or default
            max_players=game_data.get('max_players', 1), # Use seeded or default
            # Copy other relevant fields if needed, ensure they exist in model
            creator_customizations=game_data.get('creator_customizations', {}) 
        )
        # Set created_at explicitly if needed, otherwise DB default works
        # new_game.created_at = datetime.utcnow() 
        db.session.add(new_game)
        db.session.flush() # Flush to get the new_game.id

        # 2. Create Campaign (if data exists)
        new_campaign = None
        if campaign_data:
            # Ensure required fields exist
            if not all(k in campaign_data for k in ['template_id', 'campaign_data', 'objectives', 'conclusion_conditions', 'key_locations', 'key_characters', 'major_plot_points', 'possible_branches']):
                 flash('Seed file campaign data is missing required fields.', 'danger')
                 db.session.rollback()
                 return redirect(url_for('admin.index'))
                 
            new_campaign = Campaign(
                game_id=new_game.id, # Use the NEW game ID
                template_id=campaign_data['template_id'],
                campaign_data=campaign_data['campaign_data'],
                objectives=campaign_data['objectives'],
                conclusion_conditions=campaign_data['conclusion_conditions'],
                key_locations=campaign_data['key_locations'],
                key_characters=campaign_data['key_characters'],
                major_plot_points=campaign_data['major_plot_points'],
                possible_branches=campaign_data['possible_branches']
            )
            db.session.add(new_campaign)
            # Associate with game (SQLAlchemy handles this via back_populates)
            # new_game.campaign = new_campaign 

        # 3. Create GamePlayers
        if not isinstance(game_players_data, list):
             flash('Seed file game_players data is not a list.', 'danger')
             db.session.rollback()
             return redirect(url_for('admin.index'))
             
        for player_data in game_players_data:
            # Ensure required fields exist
            if not all(k in player_data for k in ['user_id']):
                 flash('Seed file player data is missing required fields (user_id).', 'danger')
                 db.session.rollback()
                 return redirect(url_for('admin.index'))
                 
            # Verify user exists
            user = db.session.get(User, player_data['user_id'])
            if not user:
                 flash(f"User ID {player_data['user_id']} referenced in seed file does not exist.", 'danger')
                 db.session.rollback()
                 return redirect(url_for('admin.index'))
                 
            new_player = GamePlayer(
                game_id=new_game.id, # Use the NEW game ID
                user_id=player_data['user_id'],
                is_ready=player_data.get('is_ready', False),
                character_description=player_data.get('character_description')
            )
            db.session.add(new_player)

        # 4. Create GameState (if data exists)
        if game_state_data:
             # Ensure required fields exist
            if not all(k in game_state_data for k in ['state_data', 'game_log', 'available_actions']):
                 flash('Seed file game_state data is missing required fields (state_data, game_log, available_actions).', 'danger')
                 db.session.rollback()
                 return redirect(url_for('admin.index'))
                 
            new_game_state = GameState(
                game_id=new_game.id, # Use the NEW game ID
                state_data=game_state_data['state_data']
            )
            # Set other fields from seed, parsing datetime if needed
            new_game_state.completed_objectives = game_state_data.get('completed_objectives', [])
            new_game_state.discovered_locations = game_state_data.get('discovered_locations', [])
            new_game_state.encountered_characters = game_state_data.get('encountered_characters', [])
            new_game_state.completed_plot_points = game_state_data.get('completed_plot_points', [])
            new_game_state.player_decisions = game_state_data.get('player_decisions', [])
            new_game_state.current_branch = game_state_data.get('current_branch', 'main')
            new_game_state.campaign_complete = game_state_data.get('campaign_complete', False)
            new_game_state.game_log = game_state_data.get('game_log', [])
            new_game_state.available_actions = game_state_data.get('available_actions', [])
            new_game_state.visited_locations = game_state_data.get('visited_locations', [])
            # Reset timestamps
            new_game_state.created_at = datetime.utcnow()
            new_game_state.last_updated = datetime.utcnow()
            
            # Associate campaign_id if campaign was created
            if new_campaign:
                 new_game_state.campaign_id = new_campaign.id
                 
            db.session.add(new_game_state)

        # Commit all new objects
        db.session.commit()
        flash(f'Successfully created new game "{new_game_name}" (ID: {new_game.id}) from seed file {seed_filename}.', 'success')

    except json.JSONDecodeError:
        flash(f'Error parsing JSON from seed file {seed_filename}.', 'danger')
        db.session.rollback() # Rollback on error
    except Exception as e:
        db.session.rollback() # Rollback on any other error
        current_app.logger.error(f"Error importing seed data from {seed_filename}: {e}", exc_info=True)
        flash(f'An error occurred during import: {e}', 'danger')

    return redirect(url_for('admin.index'))
