import pytest
from unittest.mock import MagicMock, patch
from questforge.services.socket_service import SocketService
from questforge.models import Game, GameState, Campaign, GamePlayer, User # Import GamePlayer and User
from questforge.services.ai_service import ai_service
from questforge.extensions import db
from questforge import create_app
from flask import current_app
import sqlalchemy.orm.attributes
# Removed json as _json import, no longer needed with this mocking strategy
from questforge.extensions.socketio import get_socketio # Import get_socketio

# Define simple mock classes for complex objects
class MockCampaign:
    def __init__(self):
        self.id = 'mock_campaign_id'  # Add id attribute to fix AttributeError in check_conclusion
        self.campaign_data = {
            'generated_puzzles': [
                {
                    'puzzle_id': 'puzzle1',
                    'description': 'Test puzzle',
                    'completion_state_changes': {'test': 'value'},
                    'failure_consequences': {'test': 'fail_value'}
                }
            ],
            'campaign_summary': 'A test campaign summary.'
        }
        self.objectives = ["Find the treasure"]
        self.key_locations = []
        self.key_characters = []
        self.major_plot_points = [] # Will be populated by tests if needed
        self.conclusion_conditions = []

class MockGame:
    def __init__(self, game_id='game1', created_by='user1'):
        self.id = game_id
        self.name = 'Mock Game'  # Add name attribute to fix AttributeError in join_game
        self.created_by = created_by
        self.campaign = MockCampaign() # Use our mock campaign
        self.player_associations = [] # Will be populated by tests if needed
        self.creator_customizations = {}
        self.template_overrides = {}
        self.status = 'in_progress'
        self.current_difficulty = 'Normal' # Default difficulty

class MockUser:
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

class MockGamePlayer:
    def __init__(self, user_id, username, character_name=None, character_description=None):
        self.user_id = user_id
        self.user = MockUser(user_id, username)
        self.character_name = character_name
        self.character_description = character_description
        self.is_ready = True

class MockGameState:
    def __init__(self, game_id='game1'):
        self.game_id = game_id
        self.id = game_id # For db.session.get(GameState, game_id)
        self.state_data = {
            'active_puzzles': [],
            'completed_puzzles': [],
            'game_log': [],
            'current_location': 'Starting Area',
            'turns_since_plot_progress': 0,
            'historical_summary': [],
            'world_object_states': {},
            'player_inventories': {},
            'inventories': {'shared': []} # Ensure 'inventories' key exists for InventoryService
        }
        # These are direct columns on GameState model, not in state_data
        self.completed_objectives = [] 
        self.discovered_locations = []
        self.encountered_characters = []
        self.completed_plot_points = []
        self.player_decisions = []
        self.game_log = []
        self.available_actions = []
        self.visited_locations = []
        self.current_branch = 'main'
        self.campaign_complete = False
        self.version = 1 # Add a version attribute for mocking

        # Mock the 'game' relationship
        self._game = MockGame(game_id=game_id)

    @property
    def game(self):
        return self._game

@pytest.fixture(scope='module')
def app():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app

@pytest.fixture
def mock_game_state(app):
    # Return an instance of our custom mock class
    return MockGameState()

@pytest.fixture
def mock_campaign(app):
    # Return an instance of our custom mock class
    return MockCampaign()

@pytest.fixture
def mock_game(app):
    # Return an instance of our custom mock class
    return MockGame()

# Fixture to provide a Socket.IO test client and capture emitted events
@pytest.fixture
def socketio_test_client(app):
    from questforge.extensions.socketio import init_socketio, get_socketio
    
    # Initialize SocketIO with the app
    socketio_instance = init_socketio(app)
    
    # Register handlers with the actual SocketService
    with app.app_context():
        SocketService.register_handlers()

    # Create a test client
    client = socketio_instance.test_client(app)
    
    # Connect the client
    client.connect()
    
    yield client
    
    # Disconnect the client after the test
    client.disconnect()

def test_activate_puzzle_success(app, mock_game_state, mock_game, mock_campaign):
    with app.app_context(), \
         patch('questforge.extensions.db.session.query') as mock_query, \
         patch('sqlalchemy.orm.attributes.flag_modified') as mock_flag_modified:
        
        # Configure mock_query to return our mock objects
        mock_query.return_value.filter_by.return_value.first.side_effect = [
            mock_game_state, # First call for GameState
            mock_campaign    # Second call for Campaign
        ]
        
        result = SocketService.activate_puzzle('game1', 'puzzle1')
        
        assert result is True
        assert len(mock_game_state.state_data['active_puzzles']) == 1
        assert mock_game_state.state_data['active_puzzles'][0]['puzzle_id'] == 'puzzle1'
        mock_flag_modified.assert_called_once_with(mock_game_state, 'state_data')
        # Removed commit assertion because activate_puzzle no longer commits


def test_handle_player_action_with_puzzle(app, mock_game_state, mock_game, socketio_test_client):
    client = socketio_test_client

    # Setup test data
    mock_game_state.state_data['active_puzzles'] = [{
        'puzzle_id': 'puzzle1',
        'description': 'Test puzzle',
        'completion_state_changes': {'test': 'value'},
        'failure_consequences': {'test': 'fail_value'}
    }]
    
    # Mock AI response for puzzle check
    ai_service.check_puzzle_solution = MagicMock(return_value={
        'puzzle_id': 'puzzle1',
        'solved': True,
        'confidence_score': 0.8,
        'narrative': 'You solved the puzzle!'
    })
    
    # Mock other required methods
    with app.app_context(), \
         patch('questforge.extensions.db.session.query') as mock_query, \
         patch('flask.current_app') as mock_current_app, \
         patch('sqlalchemy.orm.attributes.flag_modified') as mock_flag_modified, \
         patch('questforge.extensions.db.session.commit') as mock_commit, \
         patch('questforge.services.socket_service.db.session.get') as mock_db_get:
        
        # Configure mock_query to return our mock objects
        mock_query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_game_state
        
        # Mock GamePlayer query for player_name resolution
        mock_game_player = MockGamePlayer(user_id='user1', username='TestUser', character_name='TestPlayer')
        mock_query.return_value.filter_by.return_value.options.return_value.first.return_value = mock_game_player

        # Patch db.session.get to return mock Game and User for join_game and other calls
        def side_effect(model, id):
            if model.__name__ == 'Game' and id == 'game1':
                return mock_game
            if model.__name__ == 'User' and id == 'user1':
                return MockUser('user1', 'TestUser')
            return None
        mock_db_get.side_effect = side_effect

        mock_current_app.logger = MagicMock() # Mock the logger attribute

        # Join the game room so the client receives events
        client.emit('join_game', {'game_id': 'game1', 'user_id': 'user1'})

        # Wait briefly to allow join_game processing
        import time
        time.sleep(0.1)

        # Simulate player action by emitting through the test client
        data = {
            'game_id': 'game1',
            'user_id': 'user1',
            'action': 'solve puzzle'
        }
        
        client.emit('player_action', data)
        
        # Verify puzzle was processed
        assert len(mock_game_state.state_data['completed_puzzles']) == 1
        assert mock_game_state.state_data['completed_puzzles'][0]['puzzle_id'] == 'puzzle1'
        assert 'test' in mock_game_state.state_data
        assert mock_game_state.state_data['test'] == 'value'
        mock_flag_modified.assert_called_with(mock_game_state, 'state_data')
        assert mock_commit.call_count >= 1
        
        # Verify puzzle events were emitted by checking received messages
        received = client.get_received()
        print("Received events:", received)
        
        # Find the 'puzzle_solved' event
        puzzle_solved_event = next((msg for msg in received if msg['name'] == 'puzzle_solved'), None)
        assert puzzle_solved_event is not None, "puzzle_solved event not emitted"
        assert puzzle_solved_event['args'][0]['puzzle_id'] == 'puzzle1'
        assert puzzle_solved_event['args'][0]['narrative'] == 'You solved the puzzle!'
        assert puzzle_solved_event['args'][0]['state_changes'] == {'test': 'value'}
        
        # Find the 'game_state_update' event
        game_state_update_event = next((msg for msg in received if msg['name'] == 'game_state_update'), None)
        assert game_state_update_event is not None, "game_state_update event not emitted"
        assert game_state_update_event['args'][0]['game_id'] == 'game1'
        assert game_state_update_event['args'][0]['state']['test'] == 'value' # Verify state change in broadcast


def test_handle_player_action_with_failed_puzzle(app, mock_game_state, mock_game, socketio_test_client):
    client = socketio_test_client

    # Setup test data
    mock_game_state.state_data['active_puzzles'] = [{
        'puzzle_id': 'puzzle1',
        'description': 'Test puzzle',
        'completion_state_changes': {'test': 'value'},
        'failure_consequences': {'test': 'fail_value'}
    }]
    
    # Mock AI response for failed puzzle check
    from questforge.services.ai_service import ai_service
    ai_service.check_puzzle_solution = MagicMock(return_value={
        'puzzle_id': 'puzzle1',
        'solved': False,
        'confidence_score': 0.3,
        'narrative': 'Try again!'
    })
    
    with app.app_context(), \
         patch('questforge.extensions.db.session.query') as mock_query, \
         patch('flask.current_app') as mock_current_app, \
         patch('sqlalchemy.orm.attributes.flag_modified') as mock_flag_modified, \
         patch('questforge.extensions.db.session.commit') as mock_commit:
        
        # Configure mock_query to return our mock objects
        mock_query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_game_state
        
        # Mock GamePlayer query for player_name resolution
        mock_game_player = MockGamePlayer(user_id='user1', username='TestUser', character_name='TestPlayer')
        mock_query.return_value.filter_by.return_value.options.return_value.first.return_value = mock_game_player

        mock_current_app.logger = MagicMock()
        
        data = {
            'game_id': 'game1',
            'user_id': 'user1',
            'action': 'try puzzle'
        }
        
        client.emit('player_action', data)
        
        assert len(mock_game_state.state_data['completed_puzzles']) == 0
        assert 'test' in mock_game_state.state_data
        assert mock_game_state.state_data['test'] == 'fail_value'
        mock_flag_modified.assert_called_with(mock_game_state, 'state_data')
        mock_commit.assert_called_once()
        
        received = client.get_received()
        
        puzzle_feedback_event = next((msg for msg in received if msg['name'] == 'puzzle_feedback'), None)
        assert puzzle_feedback_event is not None, "puzzle_feedback event not emitted"
        assert puzzle_feedback_event['args'][0]['puzzle_id'] == 'puzzle1'
        assert puzzle_feedback_event['args'][0]['narrative'] == 'Try again!'
        assert puzzle_feedback_event['args'][0]['state_changes'] == {'test': 'fail_value'}
        
        game_state_update_event = next((msg for msg in received if msg['name'] == 'game_state_update'), None)
        assert game_state_update_event is not None, "game_state_update event not emitted"
        assert game_state_update_event['args'][0]['game_id'] == 'game1'
        assert game_state_update_event['args'][0]['state']['test'] == 'fail_value'

def test_puzzle_gating_plot_points(app, mock_game_state, mock_game, socketio_test_client):
    client = socketio_test_client

    mock_game_state.state_data['active_puzzles'] = [{
        'puzzle_id': 'puzzle1',
        'description': 'Test puzzle'
    }]
    
    with app.app_context(), \
         patch('questforge.extensions.db.session.query') as mock_query, \
         patch('flask.current_app') as mock_current_app, \
         patch('sqlalchemy.orm.attributes.flag_modified') as mock_flag_modified, \
         patch('questforge.extensions.db.session.commit') as mock_commit:

        # Configure mock_query to return our mock objects
        mock_query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_game_state
        
        # Mock GamePlayer query for player_name resolution
        mock_game_player = MockGamePlayer(user_id='user1', username='TestUser', character_name='TestPlayer')
        mock_query.return_value.filter_by.return_value.options.return_value.first.return_value = mock_game_player

        mock_current_app.logger = MagicMock()
        
        from questforge.services.ai_service import ai_service
        ai_service.check_puzzle_solution = MagicMock(return_value={
            'puzzle_id': 'puzzle1',
            'solved': False,
            'confidence_score': 0.3
        })
        
        data = {
            'game_id': 'game1',
            'user_id': 'user1',
            'action': 'try puzzle'
        }
        
        client.emit('player_action', data)
        
        # Verify that a game_state_update event was emitted
        received = client.get_received()
        game_state_update_event = next((msg for msg in received if msg['name'] == 'game_state_update'), None)
        assert game_state_update_event is not None, "game_state_update event not emitted"
        assert game_state_update_event['args'][0]['game_id'] == 'game1'
        
        # Assert that the log message indicating skipping plot point evaluation is present
        # This requires inspecting the logger mock, which is outside the client.get_received()
        # We need to ensure mock_current_app.logger.info was called with the specific message.
        # The exact message is "Skipping plot point evaluation due to X unsolved puzzles"
        # from socket_service.py.
        mock_current_app.logger.info.assert_any_call(
            "Skipping plot point evaluation due to 1 unsolved puzzles"
        )

        mock_commit.assert_called_once()
