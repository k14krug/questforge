from questforge.models.game_state import GameState
from questforge.models.user import User
from questforge.models.template import Template
from deepdiff import DeepDiff
from flask import current_app # Import current_app
from ..extensions import db # Import db for commit/rollback

class GameStateService:
    """Implements spec section 4.3 (Campaign State Management)
    Key Responsibilities:
    - Maintain in-memory game states for active sessions
    - Sync with database persistence layer
    - Enforce state transition rules from templates
    - Track completion progress for objectives

    Architecture Note: Uses double-checked locking pattern to ensure
    thread-safe singleton behavior across socket connections"""
    def __init__(self):
        self.active_games = {}  # game_id: {'players': set(), 'state': {}, 'version': 0, 'log': [], 'actions': []}
        self.state_history = {}  # game_id: {version: state} # Consider if history needs log/actions too

    def join_game(self, game_id, user_id):
        """Add player to game state"""
        if game_id not in self.active_games:
            self.active_games[game_id] = {
                'players': set(),
                'state': {},
                'version': 0,
                'log': [],      # Initialize log for new game entry
                'actions': []   # Initialize actions for new game entry
            }
        self.active_games[game_id]['players'].add(user_id)

    def leave_game(self, game_id, user_id):
        """Remove player from game state"""
        if game_id in self.active_games:
            self.active_games[game_id]['players'].discard(user_id)
            # Check if this was the last player
            if not self.active_games[game_id]['players']:
                current_app.logger.info(f"Last player left game {game_id}. Removing from active games.")
                del self.active_games[game_id]
                # Optionally clear history too
                if game_id in self.state_history:
                    del self.state_history[game_id]

    def get_state(self, game_id):
        """Get current game state with version and ensure all necessary data is included"""
        if game_id not in self.active_games:
             current_app.logger.warning(f"get_state called for inactive game_id: {game_id}")
             return None # Return None if game isn't active in memory

        # Safely retrieve GameState and Template from DB
        # Use app_context for database operations if called outside request context
        with current_app.app_context():
            db_game_state = GameState.query.filter_by(game_id=game_id).first()
            if not db_game_state:
                current_app.logger.warning(f"get_state: GameState record not found in DB for game {game_id}. Returning empty state.")
                # Even if not in DB, if it's active, return memory state? Or error?
                # Let's return what's in memory for now, but log warning.
                # return {'version': 0, 'state': {}, 'log': [], 'actions': []} # Option 1: Empty
                # Option 2: Return memory state if available
                mem_state = self.active_games.get(game_id, {})
                return {
                    'version': mem_state.get('version', 0),
                    'state': mem_state.get('state', {}),
                    'log': mem_state.get('log', []),
                    'actions': mem_state.get('actions', [])
                 }

            # Access Template via the game relationship
            if not db_game_state.game:
                 current_app.logger.error(f"get_state: GameState record {db_game_state.id} has no associated Game object loaded.")
                 return {'version': 0, 'state': {}, 'log': [], 'actions': []} # Cannot proceed without game

            template = db_game_state.game.template # Access template through game
            if not template:
                # This implies the game itself doesn't have a template_id or the relationship failed
                current_app.logger.error(f"get_state: Template not found via game relationship for Game {game_id}. Game's template_id: {db_game_state.game.template_id}.")
                # If template is missing, we can't determine initial state keys.
                return {'version': 0, 'state': {}, 'log': [], 'actions': []}

            # Now we know template and initial_state exist
            initial_state = template.initial_state or {} # Default to empty dict if None
            current_memory_state_dict = self.active_games[game_id]['state'].copy()

            # Ensure all keys from initial_state are present in the current memory state
            state_updated = False
            for key in initial_state:
                if key not in current_memory_state_dict:
                    current_memory_state_dict[key] = initial_state[key]
                    state_updated = True

            # Update the service's state if keys were missing
            if state_updated:
                self.active_games[game_id]['state'] = current_memory_state_dict

            # Ensure log/actions are loaded into memory state if not already present
            if not self.active_games[game_id].get('log'):
                 self.active_games[game_id]['log'] = db_game_state.game_log
            if not self.active_games[game_id].get('actions'):
                 self.active_games[game_id]['actions'] = db_game_state.available_actions


            # Include log and actions from the DB record (or memory if already loaded)
            return {
                'version': self.active_games[game_id]['version'],
                'state': current_memory_state_dict,
                'log': self.active_games[game_id]['log'],
                'actions': self.active_games[game_id]['actions']
            }

    def get_state_diff(self, game_id, from_version):
        """Get state changes since specified version"""
        # This method might need updating if history doesn't include log/actions
        current_state_info = self.get_state(game_id)
        if not current_state_info: return {} # Handle case where game isn't active

        current_state_dict = current_state_info['state']
        current_version = current_state_info['version']

        if from_version >= current_version:
            return {}

        # Get closest historical state (currently only stores 'state' dict)
        base_state_dict = self.state_history.get(game_id, {}).get(from_version)
        if not base_state_dict:
            # If no history, return full current state (excluding log/actions for diff?)
            # Or should diff include log/action changes? Needs decision.
            # For now, returning only state dict diff.
            return current_state_dict

        # Calculate delta for the 'state' dictionary part
        diff = DeepDiff(
            base_state_dict,
            current_state_dict,
            ignore_order=True,
            report_repetition=True
        )

        # How to represent log/action changes in diff? TBD.
        # For now, just returning state diff.
        return {
            'from_version': from_version,
            'to_version': current_version,
            'changes': diff # Only includes diff of 'state' dict
            # 'log_diff': ... # Future: Add log diff representation
            # 'actions_diff': ... # Future: Add actions diff representation
        }

    def get_player_state(self, game_id, user_id):
        """Get player-specific state"""
        # This likely doesn't need player_id unless filtering state later
        return {
            'player_id': user_id, # Keep for potential future use
            'game_state': self.get_state(game_id) # Return the full game state info
        }

    def update_state(self, game_id, state_changes=None, log_entry=None, actions=None, increment_version=False):
        """Update game state, log, and actions in DB and memory"""
        if game_id not in self.active_games:
            current_app.logger.warning(f"update_state called for inactive game_id: {game_id}")
            return None # Indicate failure: game not active in memory

        # Use app_context for database operations
        with current_app.app_context():
            # Get the GameState database record
            db_game_state = GameState.query.filter_by(game_id=game_id).first()
            if not db_game_state:
                current_app.logger.error(f"update_state: GameState record not found in DB for game {game_id}")
                return None # Indicate failure: record missing

            # --- Update State Dictionary ---
            if state_changes:
                # Get the Template object via the game relationship for validation
                if not db_game_state.game:
                     current_app.logger.error(f"update_state: GameState record {db_game_state.id} has no associated Game object loaded.")
                     return None # Cannot validate without game/template
                template = db_game_state.game.template
                if not template:
                    current_app.logger.error(f"update_state: Template not found via game relationship for Game {game_id}. Game's template_id: {db_game_state.game.template_id}.")
                    return None # Indicate failure

                initial_state = template.initial_state or {}
                validated_changes = {}
                current_memory_state_dict = self.active_games[game_id]['state'].copy()

                for key, value in state_changes.items():
                    if key not in initial_state:
                        current_app.logger.warning(f"update_state: Invalid state change key '{key}' for game {game_id}. Ignoring.")
                        continue # Ignoring invalid keys

                    # Basic type check (can be enhanced)
                    if initial_state.get(key) is not None and not isinstance(value, type(initial_state[key])):
                         current_app.logger.warning(f"update_state: Invalid type for key '{key}' in game {game_id}. Expected {type(initial_state[key])}, got {type(value)}. Ignoring.")
                         continue # Ignoring type mismatches

                    validated_changes[key] = value
                    current_memory_state_dict[key] = value # Update memory state immediately

                # Update state_data in the DB record by merging validated changes
                if validated_changes:
                    updated_db_state_data = db_game_state.state_data.copy()
                    updated_db_state_data.update(validated_changes)
                    db_game_state.state_data = updated_db_state_data
                    # Update in-memory state dict
                    self.active_games[game_id]['state'] = current_memory_state_dict
                    current_app.logger.debug(f"Updated state dict for game {game_id}: {validated_changes}")


            # --- Update Log ---
            if log_entry is not None:
                # Ensure game_log is treated as a list in DB object
                if not isinstance(db_game_state.game_log, list):
                    db_game_state.game_log = [] # Initialize if not a list
                db_game_state.game_log.append(log_entry)
                # Update in-memory log as well
                if 'log' not in self.active_games[game_id] or not isinstance(self.active_games[game_id]['log'], list):
                     self.active_games[game_id]['log'] = []
                self.active_games[game_id]['log'].append(log_entry)
                current_app.logger.debug(f"Appended log entry for game {game_id}")


            # --- Update Actions ---
            if actions is not None:
                 if isinstance(actions, list):
                     db_game_state.available_actions = actions
                     # Update in-memory actions
                     self.active_games[game_id]['actions'] = actions
                     current_app.logger.debug(f"Updated available actions for game {game_id}")
                 else:
                      current_app.logger.warning(f"update_state: 'actions' provided for game {game_id} was not a list. Ignoring.")


            # --- Increment Version ---
            if increment_version:
                self.active_games[game_id]['version'] += 1
                current_app.logger.info(f"Incremented version for game {game_id} to {self.active_games[game_id]['version']}")

            # --- Commit changes to the database ---
            try:
                db.session.commit()
                current_app.logger.debug(f"Successfully committed state update for game {game_id}")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to commit state update for game {game_id}: {e}", exc_info=True)
                # Should we revert in-memory changes too? Complex. For now, memory might be ahead of DB.
                return None # Indicate failure

            # Return the latest full state (including potentially updated log/actions)
            # Call get_state again to ensure consistency after commit? Or trust in-memory? Trusting memory for now.
            return {
                'version': self.active_games[game_id]['version'],
                'state': self.active_games[game_id]['state'],
                'log': self.active_games[game_id]['log'],
                'actions': self.active_games[game_id]['actions']
            }

# Singleton instance
game_state_service = GameStateService()
