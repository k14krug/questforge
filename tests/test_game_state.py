import pytest
from datetime import datetime
from questforge.models import GameState, Game, CampaignStructure

@pytest.fixture
def sample_game(db_session):
    """Fixture to create a sample Game."""
    game = Game(name="Test Game", template_id=1, created_by=1)
    db_session.add(game)
    db_session.commit()
    return game

@pytest.fixture
def sample_campaign(sample_game, db_session):
    """Fixture to create a sample CampaignStructure."""
    campaign = CampaignStructure(
        game_id=sample_game.id,
        template_id=1,
        campaign_data={},
        objectives=[],
        conclusion_conditions=[],
        key_locations=[],
        key_characters=[],
        major_plot_points=[],
        possible_branches=[]
    )
    db_session.add(campaign)
    db_session.commit()
    return campaign

def test_game_state_creation(sample_game, sample_campaign, db_session):
    """Test the creation of a GameState instance."""
    game_state = GameState(
        game_id=sample_game.id,
        campaign_structure_id=sample_campaign.id
    )
    db_session.add(game_state)
    db_session.commit()

    assert game_state.id is not None
    assert game_state.game_id == sample_game.id
    assert game_state.campaign_structure_id == sample_campaign.id
    assert game_state.current_location is None
    assert game_state.completed_objectives == []
    assert game_state.discovered_locations == []
    assert game_state.encountered_characters == []
    assert game_state.completed_plot_points == []
    assert game_state.current_branch == 'main'
    assert game_state.player_decisions == []
    assert game_state.campaign_complete is False
    assert isinstance(game_state.last_updated, datetime)

def test_game_state_relationships(sample_game, sample_campaign, db_session):
    """Test the relationships of GameState with Game and CampaignStructure."""
    game_state = GameState(
        game_id=sample_game.id,
        campaign_structure_id=sample_campaign.id
    )
    db_session.add(game_state)
    db_session.commit()

    # Test relationships
    assert game_state.game == sample_game
    assert game_state.campaign_structure == sample_campaign
    assert game_state in sample_game.game_states
    assert game_state in sample_campaign.game_states

def test_game_state_defaults(sample_game, sample_campaign, db_session):
    """Test the default values of GameState fields."""
    game_state = GameState(
        game_id=sample_game.id,
        campaign_structure_id=sample_campaign.id
    )
    db_session.add(game_state)
    db_session.commit()

    # Test default values
    assert game_state.completed_objectives == []
    assert game_state.discovered_locations == []
    assert game_state.encountered_characters == []
    assert game_state.completed_plot_points == []
    assert game_state.current_branch == 'main'
    assert game_state.player_decisions == []
    assert game_state.campaign_complete is False