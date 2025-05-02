import logging
from flask import current_app
from questforge.models.game import Game
from questforge.models.campaign import Campaign
from questforge.models.template import Template
from questforge.models.game_state import GameState
from questforge.models.api_usage_log import ApiUsageLog # Import the new model
from questforge.extensions import db
from questforge.services.ai_service import ai_service # Import the singleton instance
from typing import Dict, List, Optional, Tuple # Import typing helpers
from decimal import Decimal # For accurate cost calculation

# --- Commenting out the old create_campaign function ---
# def create_campaign(game_id: int, template_id: int, user_inputs: dict):
#     """
#     Creates a new campaign structure and initial game state for a given game,
#     using a template and user inputs processed by the AI service.
#     (DEPRECATED in favor of generate_campaign_structure)
#     """
#     logger = current_app.logger
#     try:
#         logger.info('Starting campaign creation process')
#         logger.debug(f'Input parameters - game_id: {game_id}, template_id: {template_id}')
#         # ... (rest of old implementation) ...
#         return None


def generate_campaign_structure(game: Game, template: Template, player_descriptions: Dict[str, str], creator_customizations: Optional[Dict] = None) -> bool:
    """
    Generates the full campaign structure and initial game state using the AI service,
    triggered after players are ready in the lobby.

    Args:
        game: The Game object.
        template: The Template object being used.
        player_descriptions: A dictionary mapping user_id (str) to character description (str).
        creator_customizations: An optional dictionary containing creator-provided customizations.

    Returns:
        True if campaign and initial state were successfully generated and saved, False otherwise.
    using a template and user inputs processed by the AI service.

    """
    logger = current_app.logger
    game_id = game.id # Get game_id from the game object
    try:
        logger.info(f"Starting campaign structure generation for game {game_id}")

        # 1. Generate campaign data using AI service
        # Note: ai_service.generate_campaign will need updating in Phase 3
        # to accept player_descriptions and use the revised prompt builder.
        # For now, we pass player_descriptions, assuming the service/prompt handles it.
        logger.info(f"Requesting campaign generation for game {game_id} using template {template.id}")
        # Update call to handle new return signature: (parsed_data, model_used, usage_data)
        ai_result = ai_service.generate_campaign(template, player_descriptions, creator_customizations) # Pass descriptions and customizations

        if not ai_result:
            logger.error(f"AI service failed to generate campaign data for game {game_id}")
            return False
            
        # Unpack the result
        ai_response_data, model_used, usage_data = ai_result

        logger.info(f"Received campaign data from AI ({model_used}) for game {game_id}")
        # logger.debug(f"AI Response Data: {ai_response_data}") # Optional detailed logging

        # Log API Usage
        if usage_data:
            try:
                logger.info(f"Attempting to log usage for model: '{model_used}'") 
                
                # Revised Pricing Lookup Logic
                pricing_config = current_app.config.get('OPENAI_PRICING', {})
                pricing_info = None
                matched_key = None

                # 1. Try exact match first
                if model_used in pricing_config:
                    pricing_info = pricing_config[model_used]
                    matched_key = model_used
                    logger.info(f"Found exact pricing key '{matched_key}' for model '{model_used}'")
                else:
                    # 2. Iteratively remove suffix components
                    model_parts = model_used.split('-')
                    for i in range(len(model_parts) - 1, 0, -1):
                        potential_key = '-'.join(model_parts[:i])
                        if potential_key in pricing_config:
                            pricing_info = pricing_config[potential_key]
                            matched_key = potential_key
                            logger.info(f"Found partial pricing key '{matched_key}' for model '{model_used}'")
                            break # Use the first partial match found

                cost = None
                prompt_tokens = usage_data.prompt_tokens
                completion_tokens = usage_data.completion_tokens
                total_tokens = usage_data.total_tokens

                if pricing_info:
                    prompt_cost = (Decimal(prompt_tokens) / 1000) * Decimal(pricing_info['prompt'])
                    completion_cost = (Decimal(completion_tokens) / 1000) * Decimal(pricing_info['completion'])
                    cost = prompt_cost + completion_cost
                    logger.info(f"Calculated cost for game {game_id} API call: ${cost:.6f}")
                else:
                    logger.warning(f"No pricing info found for model '{model_used}'. Cost will be null.")

                usage_log = ApiUsageLog(
                    game_id=game_id,
                    model_name=model_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost
                )
                db.session.add(usage_log)
                # Don't commit yet, part of the larger transaction
                logger.info(f"Created ApiUsageLog entry for game {game_id} (Initial Campaign Gen)")
            except Exception as log_e:
                logger.error(f"Failed to create ApiUsageLog entry for game {game_id}: {log_e}", exc_info=True)
                # Decide if this should prevent campaign creation (maybe not?)
        else:
            logger.warning(f"No usage data returned from AI service for game {game_id} campaign generation.")


        # 2. Validate AI response (using placeholder validation for now)
        # TODO: Update template.validate_ai_response in Phase 3 for the new structure
        # Use ai_response_data now
        if not template.validate_ai_response(ai_response_data):
            logger.error(f"AI response failed validation for game {game_id}. Check model validation logs.")
            return False
        logger.info(f"AI Response structure validation passed (using placeholder validation) for game {game_id}.")

        # 3. Create and save Campaign structure
        logger.info(f"Mapping AI response to Campaign model for game {game_id}")
        # Map AI response to Campaign model fields based on the *expected* new structure
        # Use ai_response_data now
        new_campaign = Campaign(
            game_id=game_id,
            template_id=template.id, # Store template ID for reference
            campaign_data=ai_response_data.get('campaign_summary', {}), # Or a more structured summary
            objectives=ai_response_data.get('campaign_objective', []),
            key_locations=ai_response_data.get('generated_locations', []),
            key_characters=ai_response_data.get('generated_characters', []),
            major_plot_points=ai_response_data.get('generated_plot_points', []),
            conclusion_conditions=ai_response_data.get('conclusion_conditions', {}),
            possible_branches=ai_response_data.get('possible_branches', {}) # If AI generates branches
        )
        db.session.add(new_campaign)
        db.session.flush() # Flush to get the new_campaign.id for GameState
        logger.info(f"Created Campaign object (ID: {new_campaign.id}) for game {game_id}")

        # 4. Create initial GameState
        # Use ai_response_data now
        initial_scene_data = ai_response_data.get('initial_scene', {}) # Expecting a dict like {'description': '...', 'state': {...}, 'goals': [...]}
        initial_state_dict = initial_scene_data.get('state', {})
        initial_narrative = initial_scene_data.get('description', 'The adventure begins...')
        initial_actions = initial_scene_data.get('goals', []) # Use initial goals as first actions

        if not initial_state_dict or not isinstance(initial_state_dict, dict):
             logger.error(f"Invalid or missing 'initial_scene.state' in AI response for game {game_id}")
             db.session.rollback() # Rollback campaign creation
             return False

        initial_game_state = GameState(
            game_id=game_id,
            state_data=initial_state_dict
        )
        # Set attributes *after* object creation
        initial_game_state.campaign_id = new_campaign.id
        initial_game_state.current_location = initial_state_dict.get('location')
        initial_game_state.game_log = [initial_narrative]
        initial_game_state.available_actions = initial_actions
        db.session.add(initial_game_state)
        logger.info(f"Created initial GameState object for game {game_id}")

        # 5. Commit transaction
        db.session.commit()
        logger.info(f"Successfully created campaign and initial state for game {game_id} in DB.")

        # 6. Initialize state in GameStateService memory
        # Import the service instance here to avoid circular import at top level
        from .game_state_service import game_state_service
        game_state_service.join_game(game_id, 'system') # Ensure game entry exists
        game_state_service.active_games[game_id]['state'] = initial_state_dict
        game_state_service.active_games[game_id]['log'] = [initial_narrative]
        game_state_service.active_games[game_id]['actions'] = initial_actions
        game_state_service.active_games[game_id]['version'] = 1 # Initial version
        logger.info(f"Initialized game state in memory for game {game_id}")

        return True

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during campaign structure generation for game {game_id}: {str(e)}", exc_info=True)
        return False

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
            return False # No conditions defined, game cannot conclude based on this check.

        # 3. Check if conclusion conditions are met
        if not isinstance(conclusion_conditions, list):
            logger.warning(f"Conclusion conditions for campaign {campaign.id} are not a list: {conclusion_conditions}. Cannot evaluate.")
            return False

        all_conditions_met = True # Assume true until a condition fails
        state_data = game_state.state_data or {} # Ensure state_data is a dict

        for condition in conclusion_conditions:
            if not isinstance(condition, dict):
                logger.warning(f"Skipping invalid condition (not a dict): {condition}")
                all_conditions_met = False
                break # If one condition is invalid, we can't be sure, so fail the check

            condition_type = condition.get('type')
            condition_met = False # Assume false for this specific condition

            try:
                if condition_type == 'state_key_equals':
                    key = condition.get('key')
                    expected_value = condition.get('value')
                    if key is not None:
                        condition_met = state_data.get(key) == expected_value
                        logger.debug(f"Checking state_key_equals: key='{key}', expected='{expected_value}', actual='{state_data.get(key)}', met={condition_met}")
                    else:
                        logger.warning(f"Invalid state_key_equals condition (missing key): {condition}")

                elif condition_type == 'state_key_exists':
                    key = condition.get('key')
                    if key is not None:
                        condition_met = key in state_data
                        logger.debug(f"Checking state_key_exists: key='{key}', met={condition_met}")
                    else:
                        logger.warning(f"Invalid state_key_exists condition (missing key): {condition}")

                elif condition_type == 'state_key_contains':
                    key = condition.get('key')
                    value_to_contain = condition.get('value')
                    if key is not None and value_to_contain is not None:
                        actual_value = state_data.get(key)
                        if isinstance(actual_value, (list, str)):
                            condition_met = value_to_contain in actual_value
                            logger.debug(f"Checking state_key_contains: key='{key}', expected_to_contain='{value_to_contain}', actual='{actual_value}', met={condition_met}")
                        else:
                            logger.debug(f"Checking state_key_contains: key='{key}' value is not list or string: {actual_value}")
                    else:
                        logger.warning(f"Invalid state_key_contains condition (missing key or value): {condition}")

                elif condition_type == 'location_visited':
                    location_name = condition.get('location')
                    visited_locations = state_data.get('visited_locations', []) # Assume visited_locations is stored in state_data
                    if location_name is not None and isinstance(visited_locations, list):
                        condition_met = location_name in visited_locations
                        logger.debug(f"Checking location_visited: location='{location_name}', visited={visited_locations}, met={condition_met}")
                    elif not isinstance(visited_locations, list):
                         logger.warning(f"Invalid location_visited check: 'visited_locations' in state_data is not a list.")
                    else:
                        logger.warning(f"Invalid location_visited condition (missing location): {condition}")

                else:
                    logger.warning(f"Unsupported conclusion condition type: {condition_type}")

            except Exception as eval_e:
                 logger.error(f"Error evaluating condition {condition}: {eval_e}", exc_info=True)
                 condition_met = False # Treat evaluation errors as condition not met

            if not condition_met:
                all_conditions_met = False
                logger.info(f"Conclusion check failed: Condition not met: {condition}")
                break # No need to check further if one condition fails

        if all_conditions_met:
            logger.info(f"All conclusion conditions met for game {game_state.game_id}.")
            return True
        else:
            # logger.info(f"Not all conclusion conditions met for game {game_state.game_id}.") # Already logged which one failed
            return False

    except Exception as e:
        logger.error(f"Error checking conclusion for game {game_state.game_id}: {str(e)}", exc_info=True)
        return False

# TODO: Implement other campaign service functions as needed
