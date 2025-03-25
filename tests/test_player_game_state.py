import pytest
from questforge.models import PlayerGameState, User, GameState

@pytest.fixture
def sample_user(db_session):
    """Fixture to create a sample User."""
    user = User(id=1, username="test_user", email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_game_state(db_session):
    """Fixture to create a sample GameState."""
    game_state = GameState(game_id=1, campaign_structure_id=1)
    db_session.add(game_state)
    db_session.commit()
    return game_state

def test_player_game_state_creation(sample_user, sample_game_state, db_session):
    """Test the creation of a PlayerGameState instance."""
    player_game_state = PlayerGameState(user_id=sample_user.id, game_state_id=sample_game_state.id)
    db_session.add(player_game_state)
    db_session.commit()

    assert player_game_state.id is not None
    assert player_game_state.user_id == sample_user.id
    assert player_game_state.game_state_id == sample_game_state.id
    assert player_game_state.user == sample_user
    assert player_game_state.game_state == sample_game_state