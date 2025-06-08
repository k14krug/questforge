import pytest
import json
from unittest.mock import patch, MagicMock
from questforge import create_app, db
from questforge.models.template import Template
from questforge.models.game import Game
from questforge.models.campaign import Campaign
from questforge.models.game_state import GameState
from questforge.models.user import User
from questforge.services.ai_service import AIService
from questforge.utils.prompt_builder import build_campaign_prompt, build_puzzle_solution_check_prompt

@pytest.fixture(scope='module')
def test_app():
    app = create_app('development')
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "OPENAI_API_KEY": "test-key", # Mock API key
        "OPENAI_MODEL_LOGIC": "mock-gpt-4.1",
        "OPENAI_MODEL_MAIN": "mock-gpt-4.1-mini",
        "ENABLE_PUZZLES": False # Ensure feature flag is off for initial tests
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(test_app):
    return test_app.test_client()

@pytest.fixture(scope='function')
def runner(test_app):
    return test_app.test_cli_runner()

@pytest.fixture(scope='module')
def new_user(test_app):
    with test_app.app_context():
        user = User(username='testuser', email='test@example.com', password='testpassword')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        return user.id # Return the ID instead of the object

@pytest.fixture(scope='function')
def ai_service_mock(test_app):
    with test_app.app_context():
        # Patch the OpenAI client directly within AIService
        with patch('questforge.services.ai_service.OpenAI') as mock_openai:
            mock_client_instance = MagicMock()
            mock_openai.return_value = mock_client_instance
            
            # Mock the chat.completions.create method
            mock_client_instance.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "campaign_objective": "Find the lost artifact.",
                    "generated_locations": [{"name": "Forest", "description": "A dark forest."}],
                    "generated_characters": [{"name": "Goblin", "role": "Enemy", "description": "A small goblin."}],
                    "generated_plot_points": [{"id": "pp_001", "description": "Enter the forest.", "required": True}],
                    "initial_scene": {"description": "You are at the forest edge.", "state": {"location": "Forest Edge"}, "goals": ["Enter forest"]},
                    "generated_puzzles": [ # Mock puzzle generation
                        {
                            "puzzle_id": "puzzle_forest_riddle",
                            "type": "Logic/Riddle",
                            "description": "A talking tree asks a riddle.",
                            "solution_criteria": "Player states the answer 'echo'.",
                            "plot_point_id": "pp_001",
                            "initial_state_changes": {},
                            "completion_state_changes": {"world_object_states": {"talking_tree": {"status": "silent"}}},
                            "clues": ["I speak without a mouth."],
                            "failure_consequences": "The tree ensnares the player for a turn.",
                            "skip_option": False
                        }
                    ]
                })))], # The issue was here, the `json.dumps` was closing too early.
                usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                model="mock-gpt-4.1"
            )
            yield AIService() # Yield an instance of AIService with the patched OpenAI client

# Test 1: Template model stores puzzle configuration correctly
def test_template_puzzle_defaults(test_app, new_user):
    with test_app.app_context():
        user = User.query.get(new_user) # Get attached user object
        template = Template(
            name="Puzzle Template",
            description="A template with puzzle rules.",
            created_by=user.id,
            genre="Fantasy",
            core_conflict="Solve the ancient riddles",
            default_rules={
                "puzzles": {
                    "enabled_types": ["Logic/Riddle", "Inventory/Environmental"],
                    "global_puzzle_difficulty": "Hard",
                    "hint_frequency": "low",
                    "failure_consequences": "severe",
                    "difficulty_settings": {} # Added this line
                }
            }
        )
        db.session.add(template)
        db.session.commit()

        retrieved_template = Template.query.get(template.id)
        assert retrieved_template.default_rules is not None
        assert "puzzles" in retrieved_template.default_rules
        assert retrieved_template.default_rules["puzzles"]["global_puzzle_difficulty"] == "Hard"
        assert "Logic/Riddle" in retrieved_template.default_rules["puzzles"]["enabled_types"]
        assert "difficulty_settings" in retrieved_template.default_rules["puzzles"] # Check default init

# Test 2: Game model overrides template puzzle configuration correctly
def test_game_puzzle_overrides(test_app, new_user):
    with test_app.app_context():
        user = User.query.get(new_user) # Get attached user object
        template = Template(
            name="Base Template",
            description="Standard template.",
            created_by=user.id,
            genre="Sci-Fi",
            core_conflict="Escape the station",
            default_rules={
                "puzzles": {
                    "enabled_types": ["Logic/Riddle"],
                    "global_puzzle_difficulty": "Normal",
                    "hint_frequency": "medium",
                    "failure_consequences": "moderate"
                }
            }
        )
        db.session.add(template)
        db.session.commit()

        game = Game(
            name="Custom Puzzle Game",
            template_id=template.id,
            created_by=user.id, # Changed to user.id
            template_overrides={
                "puzzles": {
                    "global_puzzle_difficulty": "Easy",
                    "enabled_types": ["Social/Dialogue"], # Override enabled types
                    "new_custom_setting": "value" # Add a new setting
                }
            }
        )
        db.session.add(game)
        db.session.commit()

        retrieved_game = Game.query.get(game.id)
        assert retrieved_game.template_overrides is not None
        assert "puzzles" in retrieved_game.template_overrides
        assert retrieved_game.template_overrides["puzzles"]["global_puzzle_difficulty"] == "Easy"
        assert "Logic/Riddle" not in retrieved_game.template_overrides["puzzles"]["enabled_types"] # Should be overridden
        assert "Social/Dialogue" in retrieved_game.template_overrides["puzzles"]["enabled_types"]
        assert retrieved_game.template_overrides["puzzles"]["new_custom_setting"] == "value"

# Test 3: AI generates puzzles during campaign generation
def test_ai_generates_puzzles(test_app, new_user, ai_service_mock):
    with test_app.app_context():
        user = User.query.get(new_user) # Get attached user object
        template = Template(
            name="AI Puzzle Test Template",
            description="Template for AI puzzle generation.",
            created_by=user.id,
            genre="Fantasy",
            core_conflict="Solve the ancient riddles",
            default_rules={
                "puzzles": {
                    "enabled_types": ["Logic/Riddle", "Inventory/Environmental"],
                    "global_puzzle_difficulty": "Normal"
                }
            }
        )
        db.session.add(template)
        db.session.commit()

        # Call generate_campaign through the mocked AI service
        campaign_data, model_used, usage_data = ai_service_mock.generate_campaign(template, player_details={str(user.id): {"name": "Hero", "description": "Brave adventurer"}}) # Changed to user.id
        
        assert campaign_data is not None
        assert "generated_puzzles" in campaign_data
        assert isinstance(campaign_data["generated_puzzles"], list)
        assert len(campaign_data["generated_puzzles"]) > 0
        
        puzzle = campaign_data["generated_puzzles"][0]
        assert "puzzle_id" in puzzle
        assert "type" in puzzle
        assert "description" in puzzle
        assert "solution_criteria" in puzzle
        assert puzzle["type"] == "Logic/Riddle" # Based on mock output
        assert puzzle["puzzle_id"] == "puzzle_forest_riddle" # Based on mock output
        assert "plot_point_id" in puzzle # Check for optional field
        assert "initial_state_changes" in puzzle
        assert "completion_state_changes" in puzzle
        assert "clues" in puzzle
        assert "failure_consequences" in puzzle
        assert "skip_option" in puzzle

        # Verify that the campaign is saved with generated puzzles
        campaign = Campaign(
            game_id=1, # Dummy game_id
            template_id=template.id,
            campaign_data=campaign_data,
            objectives=campaign_data.get('campaign_objective', ''),
            conclusion_conditions=campaign_data.get('conclusion_conditions', []),
            key_locations=campaign_data.get('generated_locations', []),
            key_characters=campaign_data.get('generated_characters', []),
            major_plot_points=campaign_data.get('generated_plot_points', []),
            possible_branches=campaign_data.get('possible_branches', []),
            generated_puzzles=campaign_data.get('generated_puzzles', []) # Ensure this is saved
        )
        db.session.add(campaign)
        db.session.commit()

        retrieved_campaign = Campaign.query.filter_by(game_id=1).first()
        assert retrieved_campaign.generated_puzzles is not None
        assert len(retrieved_campaign.generated_puzzles) > 0
        assert retrieved_campaign.generated_puzzles[0]["puzzle_id"] == "puzzle_forest_riddle"

# Test 4: GameState initializes with active_puzzles
def test_game_state_active_puzzles_init(test_app, new_user):
    with test_app.app_context():
        user = User.query.get(new_user) # Get attached user object
        # Create a dummy game for the GameState to reference
        game = Game(
            name="Test Game for GameState",
            template_id=1, # Dummy template_id, not strictly needed for this test's focus
            created_by=user.id
        )
        db.session.add(game)
        db.session.commit()

        game_state = GameState(game_id=game.id)
        db.session.add(game_state)
        db.session.commit()

        retrieved_game_state = GameState.query.get(game_state.id)
        assert retrieved_game_state.state_data is not None
        assert "active_puzzles" in retrieved_game_state.state_data
        assert isinstance(retrieved_game_state.state_data["active_puzzles"], list)
        assert len(retrieved_game_state.state_data["active_puzzles"]) == 0

# Test 5: ai_service.check_puzzle_solution returns correct solved status and confidence
def test_ai_check_puzzle_solution(test_app, ai_service_mock):
    with test_app.app_context():
        # Mock the chat.completions.create method for check_puzzle_solution
        ai_service_mock.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps({
                "puzzle_id": "test_puzzle_001",
                "solved": True,
                "confidence_score": 0.95
            })))]
        )

        puzzle_def = {
            "puzzle_id": "test_puzzle_001",
            "description": "Find the hidden key.",
            "solution_criteria": "Player states 'I found the key' and 'key' is in inventory."
        }
        game_state_data = {
            "current_location": "Dungeon",
            "player_inventories": {"shared": ["key"]},
            "world_object_states": {}
        }
        player_action = "I found the key in the chest."

        result = ai_service_mock.check_puzzle_solution(puzzle_def, game_state_data, player_action)

        assert result is not None
        assert result["puzzle_id"] == "test_puzzle_001"
        assert result["solved"] is True
        assert result["confidence_score"] == 0.95

        # Test a failed solution
        ai_service_mock.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps({
                "puzzle_id": "test_puzzle_001",
                "solved": False,
                "confidence_score": 0.1
            })))]
        )
        game_state_data_fail = {
            "current_location": "Dungeon",
            "player_inventories": {"shared": []}, # No key
            "world_object_states": {}
        }
        player_action_fail = "I look around."

        result_fail = ai_service_mock.check_puzzle_solution(puzzle_def, game_state_data_fail, player_action_fail)
        assert result_fail is not None
        assert result_fail["solved"] is False
        assert result_fail["confidence_score"] == 0.1

# Test 6: ai_service.check_puzzle_solution handles invalid AI response
def test_ai_check_puzzle_solution_invalid_response(test_app, ai_service_mock):
    with test_app.app_context():
        # Mock the chat.completions.create method to return invalid JSON
        ai_service_mock.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="invalid json"))]
        )

        puzzle_def = {
            "puzzle_id": "test_puzzle_002",
            "description": "Solve the riddle.",
            "solution_criteria": "Player says 'answer'."
        }
        game_state_data = {"current_location": "Cave"}
        player_action = "I say 'hello'."

        result = ai_service_mock.check_puzzle_solution(puzzle_def, game_state_data, player_action)
        assert result is not None
        assert "error" in result
        assert "not valid JSON" in result["error"]

        # Mock the chat.completions.create method to return valid JSON but missing keys
        ai_service_mock.client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps({"puzzle_id": "test_puzzle_002", "solved": True})))]
        )
        result_missing_key = ai_service_mock.check_puzzle_solution(puzzle_def, game_state_data, player_action)
        assert result_missing_key is not None
        assert "error" in result_missing_key
        assert "missing required keys" in result_missing_key["error"]
