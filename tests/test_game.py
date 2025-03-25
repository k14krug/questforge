import pytest
from questforge.models import CampaignStructure, Game

@pytest.fixture
def sample_game(db_session):
    """Fixture to create a sample Game."""
    game = Game(name="Test Game", template_id=1, created_by=1)
    db_session.add(game)
    db_session.commit()
    return game

def test_campaign_structure_creation(sample_game, db_session):
    """Test the creation of a CampaignStructure instance."""
    campaign_data = {
        "game_id": sample_game.id,
        "template_id": 1,
        "campaign_data": {"key": "value"},
        "objectives": ["obj1", "obj2"],
        "conclusion_conditions": ["cond1"],
        "key_locations": ["loc1"],
        "key_characters": ["char1"],
        "major_plot_points": ["plot1"],
        "possible_branches": ["branch1"]
    }
    
    campaign = CampaignStructure(**campaign_data)
    db_session.add(campaign)
    db_session.commit()
    
    assert campaign.id is not None
    assert campaign.game_id == sample_game.id
    assert campaign.campaign_data == {"key": "value"}
    assert campaign.objectives == ["obj1", "obj2"]
    assert campaign.game == sample_game

def test_campaign_structure_relationships(sample_game, db_session):
    """Test the relationships of CampaignStructure with Game."""
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
    
    assert campaign.game == sample_game
    assert sample_game.campaign_structure == campaign