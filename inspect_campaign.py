import sys
import json
from questforge import create_app
from questforge.models.campaign import Campaign
from questforge.models.game_state import GameState # Import GameState
from questforge.models.template import Template # Import Template
from questforge.extensions import db
from sqlalchemy import desc # Import desc for ordering

def print_json_nicely(data, indent=2):
    """Helper function to print JSON data with indentation."""
    try:
        print(json.dumps(data, indent=indent))
    except TypeError:
        # Handle cases where data might not be JSON serializable directly
        print(data)

def print_structured_data(data):
    """Helper function to print structured data (list of dicts) nicely."""
    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                print(f"\n--- Item {i+1} ---")
                for key, value in item.items():
                    print(f"  {key}: {value}")
            else:
                print(f"{i+1}. {item}") # Handle simple lists
    else:
        print_json_nicely(data)

def print_campaign_details(campaign_id):
    """
    Retrieves and prints the details of a specific campaign and its 
    latest game state from the database.
    """
    app = create_app()
    with app.app_context():
        print(f"--- Inspecting Campaign ID: {campaign_id} ---")
        
        campaign = db.session.get(Campaign, campaign_id)
        
        if not campaign:
            print(f"\nERROR: Campaign with ID {campaign_id} not found.")
            return
        
        # Fetch the Template object
        template = db.session.get(Template, campaign.template_id)
        if template:
            print(f"\nTemplate Difficulty: {template.difficulty}")
        else:
            print("\nTemplate Difficulty: Not Found")

        # Fetch the latest GameState associated with this campaign's game
        latest_game_state = GameState.query.filter_by(game_id=campaign.game_id)\
                                           .order_by(desc(GameState.last_updated))\
                                           .first()

        print(f"\nGame ID: {campaign.game_id}")
        print(f"Template ID: {campaign.template_id}")
        
        if latest_game_state:
             print(f"Latest Game State ID: {latest_game_state.id}")
             print(f"Last Updated: {latest_game_state.last_updated}")
        else:
             print("Latest Game State: Not Found")

        print("\n=== Campaign Structure ===")
        print("\n--- Campaign Data (Summary/Details) ---")
        print_json_nicely(campaign.campaign_data)

        print("\n--- Objectives ---")
        print_structured_data(campaign.objectives)

        print("\n--- Key Locations ---")
        print_structured_data(campaign.key_locations)

        print("\n--- Key Characters ---")
        print_structured_data(campaign.key_characters)

        print("\n--- Major Plot Points ---")
        print_structured_data(campaign.major_plot_points)

        print("\n--- Conclusion Conditions ---")
        print_json_nicely(campaign.conclusion_conditions)

        print("\n--- Possible Branches ---")
        print_json_nicely(campaign.possible_branches)

        if latest_game_state:
            print("\n=== Latest Game State ===")
            print("\n--- Current State Data ---")
            print_json_nicely(latest_game_state.state_data)
            
            print("\n--- Game Log (Player Actions/Narrative) ---")
            game_log = latest_game_state.game_log
            if game_log:
                if isinstance(game_log, str):
                    game_log = [game_log]  # Convert to list if it's a single string
                for i, entry in enumerate(game_log):
                    print(f"{i+1}. {entry}")
            else:
                print("No game log entries found.")

            print("\n--- Current Available Actions ---")
            if latest_game_state.available_actions and isinstance(latest_game_state.available_actions, list):
                 for action in latest_game_state.available_actions:
                      print(f"- {action}")
            elif latest_game_state.available_actions:
                 print(latest_game_state.available_actions) # Print as is if not a list
            else:
                 print("No available actions listed.")
        else:
             print("\n=== Latest Game State: Not Found ===")


        print("\n--- End of Details ---")

        # Debugging: Print all game states for the campaign's game
        print("\n=== All Game States for Game ID: {} ===".format(campaign.game_id))
        all_game_states = GameState.query.filter_by(game_id=campaign.game_id).order_by(desc(GameState.last_updated)).all()
        for state in all_game_states:
            print(f"\n--- GameState ID: {state.id} ---")
            print(f"Last Updated: {state.last_updated}")
            print_json_nicely(state.state_data)
            print("\nGame Log:")
            print_structured_data(state.game_log)
            print("\nAvailable Actions:")
            print_structured_data(state.available_actions)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python inspect_campaign.py <campaign_id>")
        sys.exit(1)
        
    try:
        campaign_id_to_inspect = int(sys.argv[1])
    except ValueError:
        print("Error: Please provide a valid integer for campaign_id.")
        sys.exit(1)
        
    print_campaign_details(campaign_id_to_inspect)
