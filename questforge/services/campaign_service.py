import logging
from flask import current_app
from questforge.models.game import Game
from questforge.models.campaign import Campaign
from questforge.models.template import Template
from questforge.models.game_state import GameState
from questforge.extensions import db
from questforge.services.ai_service import ai_service # Import the singleton instance

def create_campaign(game_id: int, template_id: int, user_inputs: dict):
    """
    Creates a new campaign structure and initial game state for a given game,
    using a template and user inputs processed by the AI service.

    Args:
        game_id: The ID of the parent Game.
        template_id: The ID of the Template to use.
        user_inputs: A dictionary of user responses to template questions.

    Returns:
        The created Campaign object if successful, None otherwise.
    """
    logger = current_app.logger
    try:
        logger.info('Starting campaign creation process')
        logger.debug(f'Input parameters - game_id: {game_id}, template_id: {template_id}')
        # 1. Fetch necessary objects
        game = db.session.get(Game, game_id)
        if not game:
            logger.error(f"Game with id {game_id} not found")
            return None

        template = db.session.get(Template, template_id)
        if not template:
            logger.error(f"Template with id {template_id} not found")
            return None

        # 2. Generate campaign data using AI service
        logger.info(f"Requesting campaign generation for game {game_id} using template {template_id}")
        campaign_data = ai_service.generate_campaign(template, user_inputs)

        if not campaign_data:
            logger.error(f"AI service failed to generate campaign data for game {game_id}")
            return None

        logger.info("Received campaign data from AI")
        # logger.debug(f"AI Response Data: {campaign_data}") # Removed for less verbosity
        logger.info("Validating AI response structure using Template.validate_ai_response")

        # Validate the structure using the method on the Template model
        if not template.validate_ai_response(campaign_data):
            # The validate_ai_response method should print specific errors
            logger.error(f"AI response failed validation for game {game_id}. Check model validation logs.")
            # No need to rollback here as nothing has been added to the session yet
            return None

        logger.info("AI Response structure validation passed.")

        # 3. Create and save Campaign structure
        logger.info("Mapping AI response to Campaign model")
        # Map AI response to Campaign model fields (with placeholders for now)
        new_campaign = Campaign(
            game_id=game_id,
            template_id=template_id,
            campaign_data={'description': campaign_data.get('initial_description', 'No description provided.')}, # Store description here for now
            objectives=campaign_data.get('goals', []), # Map goals -> objectives
            key_characters=campaign_data.get('key_npcs', []), # Map key_npcs -> key_characters
            # --- Placeholders for fields not yet generated by AI ---
            conclusion_conditions={},
            key_locations={},
            major_plot_points=[],
            possible_branches={}
            # --- End Placeholders ---
        )
        db.session.add(new_campaign)
        # Flush to get the new_campaign.id for GameState
        db.session.flush()
        logger.info(f"Created Campaign object (ID: {new_campaign.id})")
        # Removed verbose debug logs for mapped fields

        # 4. Create initial GameState
        initial_state_data = campaign_data.get('initial_state')
        if not initial_state_data or not isinstance(initial_state_data, dict):
             logger.error(f"Invalid or missing 'initial_state' in AI response for game {game_id}")
             db.session.rollback() # Rollback campaign creation
             return None

        # Instantiate GameState using only game_id and state_data
        initial_game_state = GameState(
            game_id=game_id,
            state_data=initial_state_data
        )
        # Explicitly set current_location after object creation (if still needed - might be part of state_data now)
        initial_game_state.current_location = initial_state_data.get('location')
        db.session.add(initial_game_state)
        logger.info("Created initial GameState object")

        # 5. Commit transaction
        db.session.commit()
        logger.info(f"Successfully created campaign and initial state for game {game_id}")

        return new_campaign

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during campaign creation for game {game_id}: {str(e)}", exc_info=True)
        return None

def update_campaign_state(game_state: GameState, player_action: str):
    """
    Updates the campaign state based on the player's action and the AI's response.

    Args:
        game_state: The current GameState object.
        player_action: The action taken by the player (string).

    Returns:
        True if the state was updated successfully, False otherwise.
    """
    logger = current_app.logger
    try:
        logger.info(f"Updating campaign state for game {game_state.game_id}, campaign {game_state.campaign_id}")

        # 1. Get AI response
        ai_response = ai_service.get_response(game_state, player_action)
        if not ai_response:
            logger.error(f"AI service failed to generate response for game {game_state.game_id}")
            return False

        logger.debug(f"AI Response Data: {ai_response}")

        # 2. Update GameState
        state_changes = ai_response.get('state_changes')
        if state_changes:
            logger.info("Applying state changes from AI response")
            game_state.state_data.update(state_changes)
            db.session.add(game_state)
        else:
            logger.info("No state changes in AI response")

        # 3. Update current location
        new_location = ai_response.get('new_location')
        if new_location:
            logger.info(f"Updating current location to {new_location}")
            game_state.current_location = new_location

        # 4. Commit transaction
        db.session.commit()
        logger.info(f"Successfully updated campaign state for game {game_state.game_id}")
        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during campaign creation for game {game_state.game_id}: {str(e)}", exc_info=True)
        return False

def check_conclusion(game_state: GameState):
    """
    Checks if the game has reached a conclusion based on the current game state.

    Args:
        game_state: The current GameState object.

    Returns:
        True if the game has concluded, False otherwise.
    """
    logger = current_app.logger
    try:
        logger.info(f"Checking conclusion for game {game_state.game_id}, campaign {game_state.campaign_id}")

        # 1. Get campaign
        campaign = db.session.get(Campaign, game_state.campaign_id)
        if not campaign:
            logger.error(f"Campaign with id {game_state.campaign_id} not found")
            return False

        # 2. Get conclusion conditions from campaign
        conclusion_conditions = campaign.conclusion_conditions
        if not conclusion_conditions:
            logger.info("No conclusion conditions defined for this campaign")
            return False

        # 3. Check if conclusion conditions are met
        # This is a placeholder for more complex logic
        if game_state.state_data.get('victory') == True:
            logger.info("Victory condition met")
            return True
        else:
            logger.info("Victory condition not met")
            return False

    except Exception as e:
        logger.error(f"Error checking conclusion for game {game_state.game_id}: {str(e)}", exc_info=True)
        return False

# TODO: Implement other campaign service functions as needed
