import pytest
from questforge.models import Game, CampaignStructure, GameState, Template, User
from uuid import uuid4

@pytest.fixture
def sample_user(db_session):
    """Fixture to create a sample User."""
    unique_username = f"test_user_{uuid4()}"  # Generate a unique username
    unique_email = f"{unique_username}@example.com"
    user = User(username=unique_username, email=unique_email, password="password123")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_template(sample_user, db_session):
    """Fixture to create a sample Template."""
    template = Template(name="Test Template", description="A test template", created_by=sample_user.id)
    db_session.add(template)
    db_session.commit()
    return template

@pytest.fixture
def sample_game(sample_template, sample_user, db_session):
    """Fixture to create a sample Game."""
    game = Game(name="Test Game", template_id=sample_template.id, created_by=sample_user.id)
    db_session.add(game)
    db_session.commit()
    return game

@pytest.fixture
def sample_campaign_structure(sample_game, db_session):
    """Fixture to create a sample CampaignStructure."""
    campaign = CampaignStructure(
        game_id=sample_game.id,
        template_id=sample_game.template_id,
        campaign_data={"key": "value"},
        objectives=["obj1", "obj2"],
        conclusion_conditions=["cond1"],
        key_locations=["loc1"],
        key_characters=["char1"],
        major_plot_points=["plot1"],
        possible_branches=["branch1"]
    )
    db_session.add(campaign)
    db_session.commit()
    return campaign

def test_game_to_campaign_structure_relationship(sample_game, sample_campaign_structure):
    """Test the relationship between Game and CampaignStructure."""
    assert sample_campaign_structure.game == sample_game
    assert sample_game.campaign_structure == sample_campaign_structure

def test_campaign_structure_to_game_state_relationship(sample_campaign_structure, db_session):
    """Test the relationship between CampaignStructure and GameState."""
    game_state = GameState(
        game_id=sample_campaign_structure.game_id,
        campaign_structure_id=sample_campaign_structure.id
    )
    db_session.add(game_state)
    db_session.commit()

    assert game_state.campaign_structure == sample_campaign_structure
    assert game_state in sample_campaign_structure.game_states

def test_game_to_game_state_relationship(sample_game, db_session):
    """Test the relationship between Game and GameState."""
    game_state = GameState(
        game_id=sample_game.id,
        campaign_structure_id=None  # No campaign structure for this test
    )
    db_session.add(game_state)
    db_session.commit()

    assert game_state.game == sample_game
    assert game_state in sample_game.game_states

def test_user_to_game_relationship(sample_user, sample_game):
    """Test the relationship between User and Game."""
    assert sample_game.creator == sample_user
    assert sample_game in sample_user.created_games

def test_user_to_template_relationship(sample_user, sample_template):
    """Test the relationship between User and Template."""
    assert sample_template.creator == sample_user
    assert sample_template in sample_user.created_templates

# Additional Tests
def test_template_to_game_relationship(sample_template, sample_game):
    """Test the relationship between Template and Game."""
    assert sample_game.template == sample_template
    assert sample_game in sample_template.games

def test_campaign_structure_data_integrity(sample_campaign_structure):
    """Test the integrity of CampaignStructure data."""
    assert sample_campaign_structure.campaign_data == {"key": "value"}
    assert sample_campaign_structure.objectives == ["obj1", "obj2"]
    assert sample_campaign_structure.conclusion_conditions == ["cond1"]
    assert sample_campaign_structure.key_locations == ["loc1"]
    assert sample_campaign_structure.key_characters == ["char1"]
    assert sample_campaign_structure.major_plot_points == ["plot1"]
    assert sample_campaign_structure.possible_branches == ["branch1"]