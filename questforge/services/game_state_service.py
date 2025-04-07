from questforge.models.game_state import GameState
from questforge.models.user import User
from deepdiff import DeepDiff

class GameStateService:
    def __init__(self):
        self.active_games = {}  # game_id: {'players': set(), 'state': {}, 'version': 0}
        self.state_history = {}  # game_id: {version: state}
        
    def join_game(self, game_id, user_id):
        """Add player to game state"""
        if game_id not in self.active_games:
            self.active_games[game_id] = {
                'players': set(),
                'state': {},
                'version': 0
            }
        self.active_games[game_id]['players'].add(user_id)
        
    def leave_game(self, game_id, user_id):
        """Remove player from game state"""
        if game_id in self.active_games:
            self.active_games[game_id]['players'].discard(user_id)
            if not self.active_games[game_id]['players']:
                del self.active_games[game_id]
                if game_id in self.state_history:
                    del self.state_history[game_id]
                
    def get_state(self, game_id):
        """Get current game state with version and ensure all necessary data is included"""
        if game_id not in self.active_games:
            return {'version': 0, 'state': {}}

        # Ensure all necessary keys are present in the state
        game_state = self.active_games[game_id]['state'].copy()
        template = Template.query.get(GameState.query.filter_by(game_id=game_id).first().campaign_id)
        initial_state = template.initial_state

        for key in initial_state:
            if key not in game_state:
                game_state[key] = initial_state[key]

        return {
            'version': self.active_games[game_id]['version'],
            'state': game_state
        }
        
    def get_state_diff(self, game_id, from_version):
        """Get state changes since specified version"""
        current_state = self.get_state(game_id)
        if from_version >= current_state['version']:
            return {}
            
        # Get closest historical state
        base_state = self.state_history.get(game_id, {}).get(from_version)
        if not base_state:
            return current_state['state']  # Return full state if no history
            
        # Calculate delta
        diff = DeepDiff(
            base_state,
            current_state['state'],
            ignore_order=True,
            report_repetition=True
        )
        
        return {
            'from_version': from_version,
            'to_version': current_state['version'],
            'changes': diff
        }
        
    def get_player_state(self, game_id, user_id):
        """Get player-specific state"""
        return {
            'player_id': user_id,
            'game_state': self.get_state(game_id)
        }
        
    def update_state(self, game_id, state_changes, increment_version=False):
        """Update game state with new changes"""
        if game_id not in self.active_games:
            return

        # 1. Get the GameState object
        game_state = GameState.query.filter_by(game_id=game_id).first()
        if not game_state:
            app = current_app._get_current_object()
            app.logger.error(f"Game state not found for game {game_id}")
            return

        # 2. Get the Template object
        template = Template.query.get(game_state.campaign_id)
        if not template:
            app = current_app._get_current_object()
            app.logger.error(f"Template not found for campaign {game_state.campaign_id}")
            return

        # 3. Validate state changes against initial_state
        initial_state = template.initial_state
        for key, value in state_changes.items():
            if key not in initial_state:
                app = current_app._get_current_object()
                app.logger.warning(f"Invalid state change: Key '{key}' not found in initial state")
                return

            if not isinstance(value, type(initial_state[key])):
                app = current_app._get_current_object()
                app.logger.warning(f"Invalid state change: Value for key '{key}' has incorrect type")
                return

        # Store current state in history before updating
        current_version = self.active_games[game_id]['version']
        if game_id not in self.state_history:
            self.state_history[game_id] = {}
        self.state_history[game_id][current_version] = \
            self.active_games[game_id]['state'].copy()
            
        # Apply changes
        self.active_games[game_id]['state'].update(state_changes)
        
        # Increment version if requested
        if increment_version:
            self.active_games[game_id]['version'] += 1
        
        app = current_app._get_current_object()
        app.logger.debug(f"Updating game state for game {game_id} with changes: {state_changes}")
        return self.get_state(game_id)

# Singleton instance
game_state_service = GameStateService()
