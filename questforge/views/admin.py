from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
import os
import json
from datetime import datetime
from sqlalchemy.orm import joinedload
from questforge.models.game import Game, GamePlayer # Correctly import GamePlayer
from questforge.models.campaign import Campaign
from questforge.models.game_state import GameState
from questforge.models.user import User # Needed for import validation
from questforge.extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/', methods=['GET', 'POST'])
@login_required
def admin_index():
    seed_data_dir = os.path.join(current_app.instance_path, 'seed_data')
    os.makedirs(seed_data_dir, exist_ok=True)
    seed_files = [f for f in os.listdir(seed_data_dir) if f.endswith('.json')]

    if request.method == 'POST':
        if request.form.get('action') == 'export':
            # Handle export form submission
            game_id = request.form.get('game_id')
            seed_name = request.form.get('seed_name')
            if not game_id or not seed_name:
                flash('Game ID and Seed Name are required for export.', 'danger')
                return redirect(url_for('admin.admin_index'))
            # Validate seed_name pattern
            import re
            if not re.match(r'^[A-Za-z0-9_-]+$', seed_name):
                flash('Seed Name contains invalid characters.', 'danger')
                return redirect(url_for('admin.admin_index'))
            # Export logic placeholder
            # Implement export seed data functionality here
            try:
                # Correctly load the game and its player associations
                game = Game.query.options(
                    joinedload(Game.campaign),
                    joinedload(Game.player_associations).joinedload(GamePlayer.user), # Load users via association
                    joinedload(Game.game_states)
                ).filter_by(id=int(game_id)).first()
                if not game:
                    flash(f'Game with ID {game_id} not found.', 'danger')
                    return redirect(url_for('admin.admin_index'))

                # Get latest game state
                latest_state = None
                if game.game_states:
                    latest_state = max(game.game_states, key=lambda gs: gs.created_at)

                # Build export dictionary
                export_data = {
                    'exported_at': datetime.utcnow().isoformat(),
                    'source_game_id': game.id,
                    'game': {
                        'name': game.name,
                        'template_id': game.template_id,
                        'status': game.status,
                        'creator_customizations': game.creator_customizations,
                        'created_at': game.created_at.isoformat() if game.created_at else None, # Add created_at
                    },
                    'campaign': None,
                    'game_players': [],
                    'game_state': None,
                }

                # Export Campaign data (all relevant fields)
                if game.campaign:
                    export_data['campaign'] = {
                        'template_id': game.campaign.template_id,
                        'campaign_data': game.campaign.campaign_data,
                        'objectives': game.campaign.objectives,
                        'conclusion_conditions': game.campaign.conclusion_conditions,
                        'key_locations': game.campaign.key_locations,
                        'key_characters': game.campaign.key_characters,
                        'major_plot_points': game.campaign.major_plot_points,
                        'possible_branches': game.campaign.possible_branches,
                    }

                # Export GamePlayer data (all relevant fields)
                for assoc in game.player_associations:
                    export_data['game_players'].append({
                        'user_id': assoc.user_id,
                        'character_description': assoc.character_description,
                        'is_ready': assoc.is_ready,
                        'join_date': assoc.join_date.isoformat() if assoc.join_date else None,
                    })

                # Export GameState data (all relevant fields)
                if latest_state:
                    export_data['game_state'] = {
                        'state_data': latest_state.state_data,
                        'completed_objectives': latest_state.completed_objectives,
                        'discovered_locations': latest_state.discovered_locations,
                        'encountered_characters': latest_state.encountered_characters,
                        'completed_plot_points': latest_state.completed_plot_points,
                        'player_decisions': latest_state.player_decisions,
                        'current_branch': latest_state.current_branch,
                        'campaign_complete': latest_state.campaign_complete,
                        'game_log': latest_state.game_log,
                        'available_actions': latest_state.available_actions,
                        'visited_locations': latest_state.visited_locations,
                        'created_at': latest_state.created_at.isoformat() if latest_state.created_at else None,
                        'last_updated': latest_state.last_updated.isoformat() if latest_state.last_updated else None,
                    }

                # Save to JSON file
                seed_data_dir = os.path.join(current_app.instance_path, 'seed_data')
                os.makedirs(seed_data_dir, exist_ok=True)
                file_path = os.path.join(seed_data_dir, f'{seed_name}.json')
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=4)

                flash(f'Seed data exported successfully to {seed_name}.json', 'success')
            except Exception as e:
                flash(f'Error exporting seed data: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_index'))

        elif request.form.get('action') == 'import':
            # Handle import form submission
            seed_file = request.form.get('seed_file')
            new_game_name = request.form.get('new_game_name')
            if not seed_file or not new_game_name:
                flash('Seed file and new game name are required for import.', 'danger')
                return redirect(url_for('admin.admin_index'))
            # Import logic placeholder
            try:
                seed_data_dir = os.path.join(current_app.instance_path, 'seed_data')
                file_path = os.path.join(seed_data_dir, seed_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Validate basic structure
                if 'game' not in data or 'source_game_id' not in data:
                    flash('Invalid seed file structure.', 'danger')
                    return redirect(url_for('admin.admin_index'))

                # Create new Game record using __init__
                new_game = Game(
                    name=new_game_name,
                    template_id=data['game']['template_id'],
                    created_by=current_user.id
                )
                # Set other attributes after initialization
                new_game.status = data['game']['status']
                new_game.creator_customizations = data['game'].get('creator_customizations')
                # Optionally set created_at from seed, or let DB default handle it. Sticking with default for now.
                # if data['game'].get('created_at'):
                #     new_game.created_at = datetime.fromisoformat(data['game']['created_at'])

                db.session.add(new_game)
                db.session.flush()  # To get new_game.id

                # Create Campaign if present (using all fields)
                if data.get('campaign'):
                    campaign_seed_data = data['campaign']
                    new_campaign = Campaign(
                        game_id=new_game.id,
                        template_id=campaign_seed_data['template_id'],
                        campaign_data=campaign_seed_data['campaign_data'],
                        objectives=campaign_seed_data['objectives'],
                        conclusion_conditions=campaign_seed_data['conclusion_conditions'],
                        key_locations=campaign_seed_data['key_locations'],
                        key_characters=campaign_seed_data['key_characters'],
                        major_plot_points=campaign_seed_data['major_plot_points'],
                        possible_branches=campaign_seed_data['possible_branches']
                        # Timestamps are handled by DB defaults
                    )
                    db.session.add(new_campaign)
                    # No need to flush here, commit at the end handles it
                else:
                    new_campaign = None # Keep track if campaign was created for GameState

                # Create GamePlayers (using all fields)
                for gp_data in data.get('game_players', []):
                    user = User.query.get(gp_data['user_id'])
                    if user:
                        new_gp = GamePlayer(
                            user_id=user.id,
                            game_id=new_game.id,
                            character_description=gp_data.get('character_description'),
                            is_ready=gp_data.get('is_ready', False)
                            # join_date is handled by DB default
                        )
                        db.session.add(new_gp)

                # Create GameState if present (using all fields)
                if data.get('game_state'):
                    gs_data = data['game_state']
                    # Initialize GameState with only required __init__ args
                    new_gs = GameState(
                        game_id=new_game.id,
                        state_data=gs_data.get('state_data', {}) # Ensure state_data is at least an empty dict
                    )
                    # Set other attributes after initialization
                    new_gs.completed_objectives=gs_data.get('completed_objectives', [])
                    new_gs.discovered_locations=gs_data.get('discovered_locations', [])
                    new_gs.encountered_characters=gs_data.get('encountered_characters', [])
                    new_gs.completed_plot_points=gs_data.get('completed_plot_points', [])
                    new_gs.player_decisions=gs_data.get('player_decisions', [])
                    new_gs.current_branch=gs_data.get('current_branch', 'main')
                    new_gs.campaign_complete=gs_data.get('campaign_complete', False)
                    new_gs.game_log=gs_data.get('game_log', [])
                    new_gs.available_actions=gs_data.get('available_actions', [])
                    new_gs.visited_locations=gs_data.get('visited_locations', [])
                    # Timestamps are handled by DB defaults/onupdate

                    db.session.add(new_gs)

                db.session.commit()
                flash(f'Game "{new_game_name}" created successfully from seed.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error importing seed data: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_index'))

    return render_template('admin/admin.html', seed_files=seed_files)
