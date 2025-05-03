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
        # Added player_locations to active_games structure
        self.active_games = {}  # game_id: {'players': set(), 'state': {}, 'version': 0, 'log': [], 'actions': [], 'player_locations': {}}
        self.state_history = {}  # game_id: {version: state} # Consider if history needs log/actions too

    def join_game(self, game_id, user_id):
        """Add player to game state and initialize their location"""
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
                        'actions': db_game_state.available_actions or [],
                        'player_locations': {} # Initialize player locations
                    }
                    # If initial state has a location, set it for the joining player
                    initial_location = db_game_state.state_data.get('current_location')
                    if initial_location:
                         self.active_games[game_id]['player_locations'][user_id] = initial_location
                         current_app.logger.debug(f"Set initial location for player {user_id} in game {game_id}: {initial_location}")

                else:
                    # If not in DB either, initialize fresh
                    current_app.logger.info(f"Initializing new game state in memory for game {game_id} on join.")
                    self.active_games[game_id] = {
                        'players': set(),
                        'state': {},
                        'version': 0,
                        'log': [],
                        'actions': [],
                        'player_locations': {} # Initialize player locations
                    }
        # Add the player regardless of whether state was loaded or initialized
        self.active_games[game_id]['players'].add(user_id)
        current_app.logger.debug(f"Player {user_id} added to game {game_id}. Active players: {self.active_games[game_id]['players']}")


    def leave_game(self, game_id, user_id):
        """Remove player from game state and their location"""
        if game_id in self.active_games:
            self.active_games[game_id]['players'].discard(user_id)
            # Remove player's location
            if user_id in self.active_games[game_id].get('player_locations', {}):
                 del self.active_games[game_id]['player_locations'][user_id]
                 current_app.logger.debug(f"Player {user_id} location removed from game {game_id}.")

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
                         'actions': db_game_state.available_actions or [],
                         'player_locations': {} # Initialize player locations on load
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
                    'actions': mem_state.get('actions', []),
                    'player_locations': mem_state.get('player_locations', {}) # Include player_locations
                 }

            # Game state exists in DB, ensure memory is synced for log/actions
            current_memory_state = self.active_games[game_id]

            # Sync log and actions from DB to memory if they seem empty/missing in memory
            # Also sync state_data if memory seems empty
            if not current_memory_state.get('state') and db_game_state.state_data:
                 current_memory_state['state'] = db_game_state.state_data
                 current_app.logger.debug(f"Synced state_data from DB to memory for game {game_id}")
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
                'actions': current_memory_state['actions'],
                'player_locations': current_memory_state.get('player_locations', {}) # Include player_locations
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
        # This function now primarily updates the IN-MEMORY state.
        # The DB object modification happens within the caller's (socket_service) transaction.
        if game_id not in self.active_games:
            current_app.logger.warning(f"update_state called for inactive game_id: {game_id}")
            return None

        # Get the DB object within the current session context (passed from socket_service)
        # We assume the caller (socket_service) handles fetching/refreshing the object
        # and this function is called within the same transaction context before commit.
        db_game_state = db.session.query(GameState).filter_by(game_id=game_id).first()
        if not db_game_state:
            current_app.logger.error(f"update_state: GameState record not found in current session for game {game_id}")
            # This shouldn't happen if called correctly from socket_service
            return None

        """Update game state, log, and actions in DB and memory"""
        # This function now primarily updates the IN-MEMORY state.
        # The DB object modification happens within the caller's (socket_service) transaction.
        if game_id not in self.active_games:
            current_app.logger.warning(f"update_state called for inactive game_id: {game_id}")
            return None

        # Get the DB object within the current session context (passed from socket_service)
        # We assume the caller (socket_service) handles fetching/refreshing the object
        # and this function is called within the same transaction context before commit.
        db_game_state = db.session.query(GameState).filter_by(game_id=game_id).first()
        if not db_game_state:
            current_app.logger.error(f"update_state: GameState record not found in current session for game {game_id}")
            # This shouldn't happen if called correctly from socket_service
            return None

    def update_state(self, game_id, user_id, state_changes=None, log_entry=None, actions=None, increment_version=False):
        """Update game state, log, actions, and player location in DB and memory"""
        # This function now primarily updates the IN-MEMORY state.
        # The DB object modification happens within the caller's (socket_service) transaction.
        if game_id not in self.active_games:
            current_app.logger.warning(f"update_state called for inactive game_id: {game_id}")
            return None

        # Get the DB object within the current session context (passed from socket_service)
        # We assume the caller (socket_service) handles fetching/refreshing the object
        # and this function is called within the same transaction context before commit.
        db_game_state = db.session.query(GameState).filter_by(game_id=game_id).first()
        if not db_game_state:
            current_app.logger.error(f"update_state: GameState record not found in current session for game {game_id}")
            # This shouldn't happen if called correctly from socket_service
            return None

        # --- Update State Dictionary ---
        if state_changes:
            validated_changes = state_changes
            
            # --- Handle Location History Explicitly ---
            new_location = validated_changes.get('location')
            if new_location:
                current_app.logger.debug(f"Processing location change for game {game_id}: {new_location}")
                # Ensure visited_locations exists and is a list in the DB state
                if not isinstance(db_game_state.visited_locations, list):
                    db_game_state.visited_locations = []
                # Ensure visited_locations exists and is a list in memory state
                if not isinstance(self.active_games[game_id].get('visited_locations'), list):
                     self.active_games[game_id]['visited_locations'] = []
                
                # Append new location if not already visited
                if new_location not in db_game_state.visited_locations:
                    db_game_state.visited_locations.append(new_location)
                if new_location not in self.active_games[game_id]['visited_locations']:
                     self.active_games[game_id]['visited_locations'].append(new_location)
                current_app.logger.info(f"Updated visited_locations for game {game_id}: {db_game_state.visited_locations}")

                # --- Update Player Location ---
                # Assuming the location change in state_changes applies to the acting player (user_id)
                if 'player_locations' not in self.active_games[game_id] or not isinstance(self.active_games[game_id]['player_locations'], dict):
                     self.active_games[game_id]['player_locations'] = {}
                self.active_games[game_id]['player_locations'][user_id] = new_location
                current_app.logger.debug(f"Updated player {user_id} location to {new_location} in game {game_id}")
                # Note: player_locations is only tracked in memory for now as per spec Option B
            # --- End Location Handling ---

            # --- Handle Inventory Updates Explicitly ---
            items_to_add = validated_changes.pop('items_added', None) # Remove 'items_added' if present
            if items_to_add and isinstance(items_to_add, list):
                current_app.logger.debug(f"Processing items_added for game {game_id}: {items_to_add}")
                # Ensure 'current_inventory' exists and is a list in the DB state
                if not isinstance(db_game_state.state_data.get('current_inventory'), list):
                    db_game_state.state_data['current_inventory'] = []
                # Ensure 'current_inventory' exists and is a list in memory state
                if not isinstance(self.active_games[game_id]['state'].get('current_inventory'), list):
                     self.active_games[game_id]['state']['current_inventory'] = []
                
                # Append new items (avoiding duplicates for simplicity, could refine later)
                for item in items_to_add:
                    if item not in db_game_state.state_data['current_inventory']:
                        db_game_state.state_data['current_inventory'].append(item)
                    if item not in self.active_games[game_id]['state']['current_inventory']:
                         self.active_games[game_id]['state']['current_inventory'].append(item)
                current_app.logger.info(f"Updated current_inventory for game {game_id}: {db_game_state.state_data['current_inventory']}")
            # --- End Inventory Handling ---

            # Update the rest of the state changes
            # Update in-memory state first
            current_memory_state_dict = self.active_games[game_id]['state'] # Modify in place now
            current_memory_state_dict.update(validated_changes) # validated_changes no longer has items_added
            # self.active_games[game_id]['state'] = current_memory_state_dict # Not needed if modifying in place

            # Create a NEW dictionary for the DB object assignment to ensure change detection
            new_db_state_data = db_game_state.state_data.copy() # Start with potentially updated inventory
            new_db_state_data.update(validated_changes) # Apply remaining changes
            db_game_state.state_data = new_db_state_data # Assign the new dict
            
            current_app.logger.debug(f"Updated state dict (excluding handled items_added) for game {game_id}: {validated_changes}")
            # Note: flag_modified for state_data will be called in socket_service before commit

        # --- Update Log (AI Response) ---
        if log_entry is not None:
            log_object = {"type": "ai", "content": log_entry}
            # Update in-memory log
            if 'log' not in self.active_games[game_id] or not isinstance(self.active_games[game_id]['log'], list):
                 self.active_games[game_id]['log'] = []
            self.active_games[game_id]['log'].append(log_object)
            
            # Create a NEW list for the DB object assignment
            new_db_game_log = list(db_game_state.game_log or []) # Ensure it's a list
            new_db_game_log.append(log_object)
            db_game_state.game_log = new_db_game_log # Assign the new list
            
            current_app.logger.debug(f"Appended AI log entry for game {game_id}")
            # Note: flag_modified will be called in socket_service before commit

        # --- Update Actions ---
        if actions is not None:
             if isinstance(actions, list):
                 # Update in-memory actions
                 self.active_games[game_id]['actions'] = actions
                 # Assign the NEW list directly to the DB object
                 db_game_state.available_actions = actions # Assign the new list
                 current_app.logger.debug(f"Updated available actions for game {game_id}")
                 # Note: flag_modified will be called in socket_service before commit
             else:
                  current_app.logger.warning(f"update_state: 'actions' provided for game {game_id} was not a list. Ignoring.")

        # --- Increment Version (In-memory only) ---
        if increment_version:
            if game_id not in self.state_history:
                self.state_history[game_id] = {}
            # Store a copy of the state *before* this update
            self.state_history[game_id][self.active_games[game_id]['version']] = self.active_games[game_id]['state'].copy()
            self.active_games[game_id]['version'] += 1
            current_app.logger.info(f"Incremented version for game {game_id} to {self.active_games[game_id]['version']}")

        # Ensure visited_locations is part of the state dictionary being returned
        current_state_dict = self.active_games[game_id]['state']
        current_state_dict['visited_locations'] = self.active_games[game_id].get('visited_locations', [])
        # Optionally include player_locations if needed by consumers of the 'state' dict
        # current_state_dict['player_locations'] = self.active_games[game_id].get('player_locations', {})

        # Return the latest full state from memory (as DB commit happens later)
        # The 'state' dictionary now contains visited_locations
        return {
            'version': self.active_games[game_id]['version'],
            'state': current_state_dict, # This now includes visited_locations
            'log': self.active_games[game_id]['log'],
            'actions': self.active_games[game_id]['actions'],
            # Keep player_locations separate for now unless needed inside 'state'
            'player_locations': self.active_games[game_id].get('player_locations', {})
        }

# Singleton instance
game_state_service = GameStateService()
