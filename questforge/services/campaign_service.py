import logging
from flask import current_app
from questforge.models.game import Game, GamePlayer # Added GamePlayer
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


def generate_campaign_structure(game: Game, template: Template, player_details: Dict[str, Dict[str, str]], creator_customizations: Optional[Dict] = None, template_overrides: Optional[Dict] = None) -> bool:
    """
    Generates the full campaign structure and initial game state using the AI service,
    triggered after players are ready in the lobby.

    Args:
        game: The Game object.
        template: The Template object being used.
        player_details: A dictionary mapping user_id (str) to a dict containing 'name' and 'description'.
        creator_customizations: An optional dictionary containing creator-provided customizations.
        template_overrides: An optional dictionary containing template field overrides.

    Returns:
        True if campaign and initial state were successfully generated and saved, False otherwise.
    using a template and user inputs processed by the AI service.

    """
    logger = current_app.logger
    game_id = game.id # Get game_id from the game object
    try:
        logger.info(f"Starting campaign structure generation for game {game_id}")

        # --- AI Character Name Generation (Before main campaign gen) ---
        logger.info(f"Checking for players needing AI-generated names in game {game_id}...")
        players_to_update = []
        # Ensure player associations are loaded if not already eager-loaded
        # Assuming they might be loaded from the caller (socket_service)
        for player_assoc in game.player_associations:
            if not player_assoc.character_name and player_assoc.character_description:
                logger.info(f"Player {player_assoc.user_id} needs a character name generated based on description: '{player_assoc.character_description}'")
                try:
                    generated_name = ai_service.generate_character_name(player_assoc.character_description)
                    if generated_name:
                        player_assoc.character_name = generated_name
                        players_to_update.append(player_assoc)
                        logger.info(f"AI generated name '{generated_name}' for player {player_assoc.user_id}")
                    else:
                        logger.warning(f"AI failed to generate a name for player {player_assoc.user_id}. They will proceed without an AI-generated name.")
                except Exception as name_gen_e:
                    logger.error(f"Error during AI name generation for player {player_assoc.user_id}: {name_gen_e}", exc_info=True)
                    # Continue without generated name for this player

        # Commit any generated names before proceeding
        if players_to_update:
            try:
                db.session.commit()
                logger.info(f"Successfully committed generated character names for {len(players_to_update)} players in game {game_id}.")
            except Exception as commit_e:
                db.session.rollback()
                logger.error(f"Error committing generated character names for game {game_id}: {commit_e}", exc_info=True)
                # Decide if this is fatal? For now, log and continue, campaign gen might still work.

        # --- End AI Character Name Generation ---


        # 1. Generate campaign data using AI service
        # Note: ai_service.generate_campaign will need updating in Phase 3 # TODO: This comment is outdated.
        # to accept player_descriptions and use the revised prompt builder.
        # For now, we pass player_descriptions, assuming the service/prompt handles it. # TODO: This comment is now outdated.
        logger.info(f"Requesting campaign generation for game {game_id} using template {template.id}")
        # Update call to handle new return signature: (parsed_data, model_used, usage_data)
        # Pass player_details along with other parameters
        ai_result = ai_service.generate_campaign(
            template=template,
            template_overrides=template_overrides,
            creator_customizations=creator_customizations,
            player_details=player_details
        )

        # Improved error checking for ai_result
        if isinstance(ai_result, dict) and 'error' in ai_result:
            logger.error(f"AI service returned an error during campaign generation for game {game_id}: {ai_result.get('error')}")
            if 'raw_content' in ai_result: # Log raw content if available from JSON error
                logger.error(f"Raw content from AI that caused error: {ai_result.get('raw_content')}")
            return False # Campaign generation failed
        
        # If no error, then it should be the 3-tuple, so unpack it
        try:
            ai_response_data, model_used, usage_data = ai_result
        except ValueError as e: # Catch if it's still not a 3-tuple for some reason (e.g. ai_service changes its error return)
            logger.error(f"Failed to unpack ai_result for game {game_id}. Expected 3 values, got: {type(ai_result)}. Error: {e}", exc_info=True)
            logger.debug(f"Content of ai_result that failed unpacking: {ai_result}")
            return False

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

        # --- START: New logic for initial historical summary ---
        if initial_state_dict and initial_narrative: # Ensure we have data to summarize
            logger.info(f"Generating initial historical summary for game {game_id}...")
            initial_event_action = "The adventure begins." # Placeholder action for game start

            summary_text = ai_service.generate_historical_summary(
                player_action=initial_event_action,
                stage_one_narrative=initial_narrative,
                state_changes=initial_state_dict, # Pass the full initial state
                game_id=game_id
            )

            # Ensure 'historical_summary' key exists in initial_state_dict and is a list
            if not isinstance(initial_state_dict.get('historical_summary'), list):
                initial_state_dict['historical_summary'] = []

            if summary_text:
                initial_state_dict['historical_summary'].append(summary_text)

                # Enforce MAX_HISTORICAL_SUMMARIES
                max_summaries = current_app.config.get('MAX_HISTORICAL_SUMMARIES', 10) # Get from app config
                if len(initial_state_dict['historical_summary']) > max_summaries:
                    initial_state_dict['historical_summary'] = initial_state_dict['historical_summary'][-max_summaries:] # Keep the last N items

                logger.info(f"Successfully added initial historical summary to state_data for game {game_id}.")
            else:
                logger.warning(f"Failed to generate or empty initial historical summary for game {game_id}.")
        else:
            logger.warning(f"Missing initial_state_dict or initial_narrative for game {game_id}. Skipping initial summary generation.")
            # Ensure historical_summary list exists even if we skip, if not already present
            if 'historical_summary' not in initial_state_dict:
                initial_state_dict['historical_summary'] = []
        # --- END: New logic for initial historical summary ---

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
        initial_game_state.game_log = [{'type': 'ai', 'content': initial_narrative}]
        initial_game_state.available_actions = initial_actions
        db.session.add(initial_game_state)
        logger.info(f"Created initial GameState object for game {game_id}")

        # --- Auto-complete first required plot point (ID-based) ---
        if new_campaign.major_plot_points and isinstance(new_campaign.major_plot_points, list) and len(new_campaign.major_plot_points) > 0:
            first_plot_point = new_campaign.major_plot_points[0]
            if isinstance(first_plot_point, dict) and first_plot_point.get('required') is True:
                if 'completed_plot_points' not in initial_game_state.state_data or not isinstance(initial_game_state.state_data['completed_plot_points'], list):
                    initial_game_state.state_data['completed_plot_points'] = []
                
                # Ensure it's not already added (should not happen here, but good practice)
                already_completed = False
                for cpp in initial_game_state.state_data['completed_plot_points']:
                    if isinstance(cpp, dict) and cpp.get('id') == first_plot_point.get('id'):
                        already_completed = True
                        break
                
                if not already_completed:
                    initial_game_state.state_data['completed_plot_points'].append(first_plot_point)
                    # Mark the GameState as modified if state_data was changed
                    if db.session.is_modified(initial_game_state):
                        logger.info(f"GameState.state_data marked as modified due to auto-completing first plot point.")
                    else: # Explicitly mark if direct dict mutation doesn't trigger it
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(initial_game_state, "state_data")
                        logger.info(f"Explicitly marked GameState.state_data as modified for auto-completing first plot point.")

                    logger.info(f"Auto-completed first required plot point (ID: {first_plot_point.get('id')}, Desc: {first_plot_point.get('description')}) for game {game_id}.")
                else:
                    logger.info(f"First required plot point (ID: {first_plot_point.get('id')}) was already in completed_plot_points for game {game_id}.")
            else:
                logger.info(f"First plot point for game {game_id} is not marked as required or is not a valid dict. Not auto-completing.")
        else:
            logger.info(f"No major plot points found or not a list for game {game_id}. Cannot auto-complete first plot point.")
        # --- End auto-complete ---

        # 5. Commit transaction
        db.session.commit()
        logger.info(f"Successfully created campaign and initial state for game {game_id} in DB.")

        # 6. Initialize state in GameStateService memory
        # Import the service instance here to avoid circular import at top level
        from .game_state_service import game_state_service
        game_state_service.join_game(game_id, 'system') # Ensure game entry exists
        game_state_service.active_games[game_id]['state'] = initial_state_dict
        game_state_service.active_games[game_id]['log'] = [{'type': 'ai', 'content': initial_narrative}]
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
        # Ensure game and campaign relationships are loaded or accessible
        if not game_state.game:
            logger.error(f"GameState {game_state.id} has no associated game. Cannot check conclusion.")
            return False
        if not game_state.game.campaign: # This implies campaign_id would also be missing or campaign not loaded
            logger.error(f"Game {game_state.game.id} has no associated campaign. Cannot check conclusion.")
            return False
            
        # Correctly access campaign's ID via game_state.game.campaign.id for logging
        # And campaign object via game_state.game.campaign
        logger.info(f"--- Debug: Starting check_conclusion for game {game_state.game_id}, campaign ID {game_state.game.campaign.id} ---")

        # 1. Get campaign directly from the loaded relationship
        campaign = game_state.game.campaign
        # The check 'if not campaign:' is implicitly handled by 'if not game_state.game.campaign:' above.
        
        state_data = game_state.state_data or {} # Ensure state_data is a dict
        logger.debug(f"--- Debug: state_data: {state_data} (type: {type(state_data)}) ---")

        # --- ID-Based Pre-Check: Ensure all required plot points are completed ---
        major_plot_points_list = campaign.major_plot_points
        logger.debug(f"--- Debug: Campaign Major Plot Points (for ID check): {major_plot_points_list} (type: {type(major_plot_points_list)}) ---")
        if not isinstance(major_plot_points_list, list):
            logger.warning(f"Campaign {campaign.id} major_plot_points is not a list. Cannot check required plot points by ID.")
            major_plot_points_list = [] 

        completed_plot_points_data = state_data.get('completed_plot_points', [])
        logger.debug(f"--- Debug: GameState completed_plot_points (for ID check): {completed_plot_points_data} (type: {type(completed_plot_points_data)}) ---")
        if not isinstance(completed_plot_points_data, list):
            logger.warning(f"GameState {game_state.id} completed_plot_points is not a list. Cannot check required plot points by ID.")
            completed_plot_points_data = []

        # Extract IDs of completed plot points (assuming they are stored as objects with an 'id' key)
        completed_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id') is not None]
        logger.debug(f"--- Debug: Extracted completed_ids: {completed_ids} ---")

        all_required_completed = True
        missing_required_plot_point_id = None
        missing_required_plot_point_desc = None

        for plot_point in major_plot_points_list:
            if isinstance(plot_point, dict) and plot_point.get('required') is True: # Explicitly check for True
                pp_id = plot_point.get('id')
                pp_description = plot_point.get('description', 'N/A') # Get description for logging
                if pp_id is None: # Should not happen if campaign generation is correct
                    logger.warning(f"--- Debug: Required plot point found without an ID: {plot_point}. Skipping ID check for this one. ---")
                    continue 
                if pp_id not in completed_ids:
                    all_required_completed = False
                    missing_required_plot_point_id = pp_id
                    missing_required_plot_point_desc = pp_description
                    logger.info(f"--- Debug: Conclusion pre-check (ID-based) failed: Required plot point ID '{pp_id}' (Desc: '{pp_description}') not found in completed_ids: {completed_ids}. ---")
                    break 
        
        logger.debug(f"--- Debug: all_required_completed (ID-based): {all_required_completed} ---")
        if not all_required_completed:
            logger.info(f"--- Debug: Returning False because not all required plot points completed (ID-based). Missing ID: '{missing_required_plot_point_id}', Desc: '{missing_required_plot_point_desc}' ---")
            return False 
        
        logger.info(f"--- Debug: All required plot points completed (ID-based) for game {game_state.game_id}. Proceeding to check conclusion_conditions. ---")
        # --- End ID-Based Pre-Check ---

        # 2. Get conclusion conditions from campaign
        conclusion_conditions = campaign.conclusion_conditions
        logger.debug(f"--- Debug: campaign.conclusion_conditions: {conclusion_conditions} (type: {type(conclusion_conditions)}) ---")

        if not conclusion_conditions: # This includes empty list or None
            logger.info("--- Debug: No conclusion conditions defined for this campaign, and all required plot points are done. Considering concluded. ---")
            logger.info(f"--- Debug: Returning True (no specific conditions, all required met) ---")
            return True 

        # 3. Check if conclusion conditions are met
        if not isinstance(conclusion_conditions, list):
            logger.warning(f"Conclusion conditions for campaign {campaign.id} are not a list: {conclusion_conditions}. Cannot evaluate.")
            logger.info(f"--- Debug: Returning False (conclusion_conditions not a list) ---")
            return False

        all_conditions_met = True # Assume true until a condition fails
        
        for i, condition in enumerate(conclusion_conditions):
            logger.debug(f"--- Debug: Evaluating condition #{i+1}: {condition} ---")
            if not isinstance(condition, dict):
                logger.warning(f"Skipping invalid condition (not a dict): {condition}")
                all_conditions_met = False
                logger.debug(f"--- Debug: Condition #{i+1} is not a dict. all_conditions_met set to False. ---")
                break 

            condition_type = condition.get('type')
            condition_met = False 

            try:
                if condition_type == 'state_key_equals':
                    key = condition.get('key')
                    expected_value = condition.get('value')
                    actual_value = state_data.get(key)
                    if key is not None:
                        condition_met = actual_value == expected_value
                        logger.debug(f"--- Debug: Condition type 'state_key_equals': key='{key}', expected='{expected_value}', actual='{actual_value}', met={condition_met} ---")
                    else:
                        logger.warning(f"Invalid state_key_equals condition (missing key): {condition}")
                        logger.debug(f"--- Debug: Condition type 'state_key_equals' invalid (missing key). ---")

                elif condition_type == 'state_key_exists':
                    key = condition.get('key')
                    if key is not None:
                        condition_met = key in state_data
                        logger.debug(f"--- Debug: Condition type 'state_key_exists': key='{key}', present={condition_met}, met={condition_met} ---")
                    else:
                        logger.warning(f"Invalid state_key_exists condition (missing key): {condition}")
                        logger.debug(f"--- Debug: Condition type 'state_key_exists' invalid (missing key). ---")

                elif condition_type == 'state_key_contains':
                    key = condition.get('key')
                    value_to_contain = condition.get('value')
                    actual_value = state_data.get(key)
                    if key is not None and value_to_contain is not None:
                        if isinstance(actual_value, list):
                            # Fuzzy match for lists: check if any item in actual_value (list) contains value_to_contain (string)
                            condition_met = any(str(value_to_contain).lower() in str(item).lower() for item in actual_value)
                            logger.debug(f"--- Debug: Condition type 'state_key_contains' (list): key='{key}', expected_to_contain='{value_to_contain}', actual='{actual_value}', met={condition_met} (fuzzy) ---")
                        elif isinstance(actual_value, str):
                            # Fuzzy match for strings: check if actual_value (string) contains value_to_contain (string)
                            condition_met = str(value_to_contain).lower() in str(actual_value).lower()
                            logger.debug(f"--- Debug: Condition type 'state_key_contains' (string): key='{key}', expected_to_contain='{value_to_contain}', actual='{actual_value}', met={condition_met} (fuzzy) ---")
                        else:
                            logger.debug(f"--- Debug: Condition type 'state_key_contains': key='{key}' value is not list or string: {actual_value}. Condition not met. ---")
                    else:
                        logger.warning(f"Invalid state_key_contains condition (missing key or value): {condition}")
                        logger.debug(f"--- Debug: Condition type 'state_key_contains' invalid (missing key or value). ---")

                elif condition_type == 'location_visited':
                    location_name_condition = condition.get('location') # The location name from the condition
                    visited_locations_state = state_data.get('visited_locations', []) # The list of visited locations from state
                    if location_name_condition is not None and isinstance(visited_locations_state, list):
                        # Fuzzy match: check if any visited location string contains the condition location string
                        condition_met = any(str(location_name_condition).lower() in str(visited_loc).lower() for visited_loc in visited_locations_state)
                        logger.debug(f"--- Debug: Condition type 'location_visited': condition_location='{location_name_condition}', visited_in_state='{visited_locations_state}', met={condition_met} (fuzzy) ---")
                    elif not isinstance(visited_locations_state, list):
                         logger.warning(f"Invalid location_visited check: 'visited_locations' in state_data is not a list: {visited_locations_state}")
                         logger.debug(f"--- Debug: Condition type 'location_visited' invalid ('visited_locations' not a list). ---")
                    else:
                        logger.warning(f"Invalid location_visited condition (missing location): {condition}")
                        logger.debug(f"--- Debug: Condition type 'location_visited' invalid (missing location name). ---")
                else:
                    logger.warning(f"Unsupported conclusion condition type: {condition_type}")
                    logger.debug(f"--- Debug: Unsupported condition type '{condition_type}'. Condition not met. ---")

            except Exception as eval_e:
                 logger.error(f"Error evaluating condition {condition}: {eval_e}", exc_info=True)
                 condition_met = False 
                 logger.debug(f"--- Debug: Exception during evaluation of condition #{i+1}. Condition met set to False. ---")
            
            logger.debug(f"--- Debug: Result of condition #{i+1} ('{condition.get('type')}', details: {condition}): {condition_met} ---")
            if not condition_met:
                all_conditions_met = False
                logger.info(f"--- Debug: Conclusion check failed: Condition #{i+1} not met: {condition} ---")
                break 

        if all_conditions_met:
            logger.info(f"--- Debug: All conclusion conditions met for game {game_state.game_id}. ---")
            logger.info(f"--- Debug: Returning True (all conditions met) ---")
            return True
        else:
            logger.info(f"--- Debug: Not all conclusion conditions met for game {game_state.game_id}. ---")
            logger.info(f"--- Debug: Returning False (not all conditions met) ---")
            return False

    except Exception as e:
        logger.error(f"Error checking conclusion for game {game_state.game_id}: {str(e)}", exc_info=True)
        logger.info(f"--- Debug: Returning False (exception in check_conclusion) ---")
        return False

# TODO: Implement other campaign service functions as needed
