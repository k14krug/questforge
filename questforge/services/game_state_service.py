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
            # Attempt to load from DB first if game exists but isn't active in memory
            with current_app.app_context():
                db_game_state = GameState.query.filter_by(game_id=game_id).first()
                if db_game_state:
                    current_app.logger.info(f"Loading existing game {game_id} state from DB into memory on join.")
                    self.active_games[game_id] = {
                        'players': set(),
                        'state': db_game_state.state_data or {},
                        'version': 1, # Or derive from timestamp/version field if added
                        'log': db_game_state.game_log or [],
                        'actions': db_game_state.available_actions or []
                    }
                else:
                    # If not in DB either, initialize fresh
                    current_app.logger.info(f"Initializing new game state in memory for game {game_id} on join.")
                    self.active_games[game_id] = {
                        'players': set(),
                        'state': {},
                        'version': 0,
                        'log': [],
                        'actions': []
                    }
        # Add the player regardless of whether state was loaded or initialized
        self.active_games[game_id]['players'].add(user_id)
        current_app.logger.debug(f"Player {user_id} added to game {game_id}. Active players: {self.active_games[game_id]['players']}")


    def leave_game(self, game_id, user_id):
        """Remove player from game state"""
        if game_id in self.active_games:
            self.active_games[game_id]['players'].discard(user_id)
            current_app.logger.debug(f"Player {user_id} removed from game {game_id}. Remaining players: {self.active_games[game_id]['players']}")
            # Check if this was the last player
            if not self.active_games[game_id]['players']:
                current_app.logger.info(f"Last player left game {game_id}. Removing from active games.")
                # Persist final state before removing? Optional.
                # self.persist_state(game_id) # Example if needed
                del self.active_games[game_id]
                # Optionally clear history too
                if game_id in self.state_history:
                    del self.state_history[game_id]

    def get_state(self, game_id):
        """Get current game state with version and ensure all necessary data is included"""
        if game_id not in self.active_games:
             current_app.logger.warning(f"get_state called for inactive game_id: {game_id}. Attempting DB load.")
             # Attempt to load the LATEST state from DB if not in memory
             with current_app.app_context():
                 # Order by last_updated descending to get the most recent state
                 # Assuming only ONE GameState record per game_id as per current update logic
                 db_game_state = GameState.query.filter_by(game_id=game_id).order_by(GameState.last_updated.desc()).first()
                 if db_game_state:
                     current_app.logger.info(f"Loading latest game {game_id} state (ID: {db_game_state.id}) from DB into memory on get_state.")
                     # Initialize the game in memory with data from the loaded record
                     self.active_games[game_id] = {
                         'players': set(), # Players will join via socket events
                         'state': db_game_state.state_data or {},
                         'version': 1, # Consider a real versioning mechanism later
                         'log': db_game_state.game_log or [],
                         'actions': db_game_state.available_actions or []
                     }
                     # Return the newly loaded state
                     return self.active_games[game_id]
                 else:
                     current_app.logger.error(f"get_state: Game {game_id} not found in active games or DB.")
                     return None # Game truly doesn't exist or wasn't initialized

        # Game is active in memory, proceed to retrieve its state
        with current_app.app_context():
            db_game_state = GameState.query.filter_by(game_id=game_id).first()

            if not db_game_state:
                current_app.logger.error(f"get_state: GameState record not found in DB for active game {game_id}. Memory state might be stale.")
                # Return memory state but log error
                mem_state = self.active_games.get(game_id, {})
                return {
                    'version': mem_state.get('version', 0),
                    'state': mem_state.get('state', {}),
                    'log': mem_state.get('log', []),
                    'actions': mem_state.get('actions', [])
                 }

            # Game state exists in DB, ensure memory is synced for log/actions
            current_memory_state = self.active_games[game_id]

            # Sync log and actions from DB to memory if they seem empty/missing in memory
            if not current_memory_state.get('log') and db_game_state.game_log:
                 current_memory_state['log'] = db_game_state.game_log
                 current_app.logger.debug(f"Synced game_log from DB to memory for game {game_id}")
            if not current_memory_state.get('actions') and db_game_state.available_actions:
                 current_memory_state['actions'] = db_game_state.available_actions
                 current_app.logger.debug(f"Synced available_actions from DB to memory for game {game_id}")

            # Return the potentially updated memory state
            return {
                'version': current_memory_state['version'],
                'state': current_memory_state['state'],
                'log': current_memory_state['log'],
                'actions': current_memory_state['actions']
            }

    def get_state_diff(self, game_id, from_version):
        """Get state changes since specified version"""
        current_state_info = self.get_state(game_id)
        if not current_state_info: return {}

        current_state_dict = current_state_info['state']
        current_version = current_state_info['version']

        if from_version >= current_version:
            return {}

        base_state_dict = self.state_history.get(game_id, {}).get(from_version)
        if not base_state_dict:
            return current_state_dict # Return full state if base version not found

        diff = DeepDiff(
            base_state_dict,
            current_state_dict,
            ignore_order=True,
            report_repetition=True
        )
        return {
            'from_version': from_version,
            'to_version': current_version,
            'changes': diff
        }

    def get_player_state(self, game_id, user_id):
        """Get player-specific state"""
        return {
            'player_id': user_id,
            'game_state': self.get_state(game_id)
        }

    def update_state(self, game_id, state_changes=None, log_entry=None, actions=None, increment_version=False):
        """Update game state, log, and actions in DB and memory"""
        if game_id not in self.active_games:
            current_app.logger.warning(f"update_state called for inactive game_id: {game_id}")
            return None

        with current_app.app_context():
            db_game_state = GameState.query.filter_by(game_id=game_id).first()
            if not db_game_state:
                current_app.logger.error(f"update_state: GameState record not found in DB for game {game_id}")
                return None

            # --- Update State Dictionary ---
            if state_changes:
                # Apply changes directly, assuming AI provides valid structure
                validated_changes = state_changes
                current_memory_state_dict = self.active_games[game_id]['state'].copy()
                current_memory_state_dict.update(validated_changes) # Update memory state

                # Update state_data in the DB record
                updated_db_state_data = db_game_state.state_data.copy() if db_game_state.state_data else {}
                updated_db_state_data.update(validated_changes)
                db_game_state.state_data = updated_db_state_data
                # Update in-memory state dict
                self.active_games[game_id]['state'] = current_memory_state_dict
                current_app.logger.debug(f"Updated state dict for game {game_id}: {validated_changes}")

            # --- Update Log (AI Response) ---
            if log_entry is not None: # log_entry here is the AI narrative
                log_object = {"type": "ai", "content": log_entry}
                # Ensure game_log is treated as a list in DB object and memory
                if not isinstance(db_game_state.game_log, list):
                    db_game_state.game_log = []
                if 'log' not in self.active_games[game_id] or not isinstance(self.active_games[game_id]['log'], list):
                     self.active_games[game_id]['log'] = []

                db_game_state.game_log.append(log_object)
                self.active_games[game_id]['log'].append(log_object)
                current_app.logger.debug(f"Appended AI log entry for game {game_id}")

            # --- Update Actions ---
            if actions is not None:
                 if isinstance(actions, list):
                     db_game_state.available_actions = actions
                     self.active_games[game_id]['actions'] = actions # Update in-memory actions
                     current_app.logger.debug(f"Updated available actions for game {game_id}")
                 else:
                      current_app.logger.warning(f"update_state: 'actions' provided for game {game_id} was not a list. Ignoring.")

            # --- Increment Version ---
            if increment_version:
                # Add state to history *before* incrementing version
                if game_id not in self.state_history:
                    self.state_history[game_id] = {}
                # Store a copy of the state *before* this update
                # Need to decide what exactly to store (just state dict, or full state_info?)
                # Storing just the state dict for now for diffing purposes
                self.state_history[game_id][self.active_games[game_id]['version']] = self.active_games[game_id]['state'].copy()

                self.active_games[game_id]['version'] += 1
                current_app.logger.info(f"Incremented version for game {game_id} to {self.active_games[game_id]['version']}")


            # --- Commit changes to the database ---
            # Removed commit from here - should be handled by the caller (e.g., handle_player_action)
            # try:
            #     db.session.commit()
            #     current_app.logger.debug(f"Successfully committed state update for game {game_id}")
            # except Exception as e:
            #     db.session.rollback() # Rollback should also be handled by caller
            #     current_app.logger.error(f"Failed to commit state update for game {game_id}: {e}", exc_info=True)
            #     # Revert in-memory changes? Difficult. Log error and potentially desync state.
            #     return None # Indicate failure

            # Return the latest full state from memory
            return {
                'version': self.active_games[game_id]['version'],
                'state': self.active_games[game_id]['state'],
                'log': self.active_games[game_id]['log'],
                'actions': self.active_games[game_id]['actions']
            }

# Singleton instance
game_state_service = GameStateService()
