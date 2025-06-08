import os
import json
import re
from openai import OpenAI
from flask import current_app
from questforge.models.game import Game
from questforge.models.game_state import GameState
from questforge.models.template import Template
from questforge.models.campaign import Campaign
from questforge.utils.prompt_builder import build_campaign_prompt, build_response_prompt, build_character_name_prompt, build_hint_prompt, build_plot_completion_check_prompt, build_summary_prompt # Added build_summary_prompt
from questforge.utils.context_manager import build_context
from typing import Dict, Optional, Tuple, Any, List
import requests
from decimal import Decimal
from ..models.api_usage_log import ApiUsageLog
from ..extensions import db

class AIService:
    """Service for handling AI interactions, including campaign generation and responses."""

    def __init__(self):
        """Initializes the AI service, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                app = current_app._get_current_object()
                app.logger.warning("OPENAI_API_KEY environment variable not set. AI service may not function.")
            except RuntimeError:
                print("Warning: OPENAI_API_KEY not set and running outside Flask app context.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE") or 0.7)
            self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS") or 1024)

    def _check_plot_point_atomicity(self, plot_point_description: str) -> Tuple[bool, List[str]]:
        issues = []

        conjunction_patterns = [
            r'\\band\\b', r'\\bthen\\b', r'\\bwhile\\b', r'\\bafter\\b', r'\\bbefore\\b',
            r'\\bas well as\\b', r'\\balong with\\b', r'\\bin addition to\\b'
        ]

        for pattern in conjunction_patterns:
            if re.search(pattern, plot_point_description.lower()):
                issues.append(f"Contains conjunction '{re.search(pattern, plot_point_description.lower()).group(0)}' that may indicate multiple actions")

        action_verb_pairs = [
            (r'\\bfind\\b.*\\buse\\b', "contains 'find' and 'use' verbs"),
            (r'\\bgo\\b.*\\btalk\\b', "contains 'go' and 'talk' verbs"),
            (r'\\bcollect\\b.*\\bbring\\b', "contains 'collect' and 'bring' verbs"),
            (r'\\bsolve\\b.*\\bobtain\\b', "contains 'solve' and 'obtain' verbs"),
            (r'\\benter\\b.*\\bactivate\\b', "contains 'enter' and 'activate' verbs"),
            (r'\\bfind\\b.*\\bdeliver\\b', "contains 'find' and 'deliver' verbs"),
            (r'\\brescue\\b.*\\bescape\\b', "contains 'rescue' and 'escape' verbs")
        ]

        for pattern, message in action_verb_pairs:
            if re.search(pattern, plot_point_description.lower()):
                issues.append(f"Multiple action verbs: {message}")

        compound_phrases = [
            r'\\bin order to\\b', r'\\bso that\\b', r'\\bto enable\\b', r'\\bwhich allows\\b',
            r'\\bto unlock\\b', r'\\bto access\\b', r'\\bto proceed\\b'
        ]

        for pattern in compound_phrases:
            if re.search(pattern, plot_point_description.lower()):
                issues.append(f"Contains phrase '{re.search(pattern, plot_point_description.lower()).group(0)}' that may indicate a multi-step objective")

        location_pattern = r'from\\s+\\w+\\s+to\\s+\\w+'
        if re.search(location_pattern, plot_point_description.lower()):
            issues.append("Contains multiple locations (from X to Y pattern)")

        list_indicators = [',', ';', 'both', 'all of', 'any of', 'either']
        for indicator in list_indicators:
            if indicator in plot_point_description.lower():
                issues.append(f"Contains potential list indicator '{indicator}'")

        return len(issues) == 0, issues

    def generate_campaign(self, template: Template, template_overrides: Optional[Dict[str, Any]] = None, creator_customizations: Optional[Dict[str, Any]] = None, player_details: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate campaign.")
            return {"error": "AI service not available."}
        prompt = build_campaign_prompt(template, template_overrides, creator_customizations, player_details)
        app.logger.debug(f"--- AI Service: Generating campaign with prompt ---\\n{prompt}\\n-------------------------------------------------")
        generated_content = ""
        try:
            # Use OPENAI_MODEL_LOGIC for critical logic-heavy calls
            model_to_use = app.config.get('OPENAI_MODEL_LOGIC', 'gpt-4o')
            app.logger.debug(f"Using OPENAI_MODEL_LOGIC for generate_campaign: {model_to_use}")
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": "You are a creative game master designing the beginning of a text-based adventure game according to the user's template and inputs. Output ONLY the requested JSON object."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": self.temperature,
                "max_tokens": 2048
            }
            log_ai_debug_payload("Generate campaign from template", payload, "campaign", 1)
            response = self.client.chat.completions.create(**payload)
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\\n{generated_content}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (generate_campaign) completed. Model: {model_used}, Usage Data: {usage_data}")
            parsed_data = json.loads(generated_content)
            required_top_level_keys = ['campaign_objective', 'generated_locations', 'generated_characters', 'generated_plot_points', 'initial_scene']
            missing_keys = [k for k in required_top_level_keys if k not in parsed_data]
            if missing_keys:
                app.logger.error(f"AI campaign response missing required top-level keys: {missing_keys}")
                app.logger.debug(f"Received data: {parsed_data}")
                return {"error": f"AI response missing required keys: {', '.join(missing_keys)}"}
            initial_scene = parsed_data.get('initial_scene', {})
            if not isinstance(initial_scene, dict) or not all(k in initial_scene for k in ['description', 'state', 'goals']):
                app.logger.error("AI campaign response 'initial_scene' is missing required keys ('description', 'state', 'goals') or is not a dictionary.")
                app.logger.debug(f"Received initial_scene: {initial_scene}")
                return {"error": "Invalid 'initial_scene' structure in AI response."}
            if not isinstance(initial_scene.get('state'), dict):
                app.logger.error("AI campaign response 'initial_scene.state' is not a dictionary.")
                app.logger.debug(f"Received initial_scene state: {initial_scene.get('state')}")
                return {"error": "Invalid 'initial_scene.state' structure in AI response."}
            if not isinstance(initial_scene.get('goals'), list):
                app.logger.error("AI campaign response 'initial_scene.goals' is not a list.")
                app.logger.debug(f"Received initial_scene goals: {initial_scene.get('goals')}")
                return {"error": "Invalid 'initial_scene.goals' structure in AI response."}
            if not isinstance(parsed_data.get('generated_locations'), list):
                app.logger.warning("AI campaign response 'generated_locations' is not a list.")
            if not isinstance(parsed_data.get('generated_characters'), list):
                app.logger.warning("AI campaign response 'generated_characters' is not a list.")
            plot_points = parsed_data.get('generated_plot_points')
            if not isinstance(plot_points, list):
                app.logger.error("AI campaign response 'generated_plot_points' is not a list.")
                return {"error": "Invalid 'generated_plot_points' structure: not a list."}
            seen_ids = set()
            for i, pp in enumerate(plot_points):
                if not isinstance(pp, dict) or not all(k in pp for k in ['id', 'description', 'required']):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} is not a dict or missing 'id'/'description'/'required' keys.")
                    return {"error": f"Invalid 'generated_plot_points' item structure at index {i} (missing id, description, or required)."}
                plot_id = pp.get('id')
                if not isinstance(plot_id, str) or not plot_id.strip():
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} 'id' is not a non-empty string.")
                    return {"error": f"Invalid 'generated_plot_points' item {i} 'id' type or empty."}
                if plot_id in seen_ids:
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} has duplicate 'id': {plot_id}.")
                    return {"error": f"Duplicate 'id' ({plot_id}) found in 'generated_plot_points'."}
                seen_ids.add(plot_id)
                if not isinstance(pp.get('description'), str):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} 'description' is not a string.")
                    return {"error": f"Invalid 'generated_plot_points' item {i} 'description' type."}
                if not isinstance(pp.get('required'), bool):
                    app.logger.error(f"AI campaign response 'generated_plot_points' item {i} 'required' is not a boolean.")
                    return {"error": f"Invalid 'generated_plot_points' item {i} 'required' type."}

            app.logger.info("Validating plot point atomicity...")
            non_atomic_plot_points = []
            for i, pp in enumerate(plot_points):
                plot_id = pp.get('id')
                description = pp.get('description')
                is_atomic, issues = self._check_plot_point_atomicity(description)

                if not is_atomic:
                    non_atomic_plot_points.append({
                        'id': plot_id,
                        'description': description,
                        'issues': issues
                    })
                    issue_str = "; ".join(issues)
                    app.logger.warning(f"Plot point '{plot_id}' may not be atomic: {issue_str}")
                    app.logger.warning(f"  Description: '{description}'")

            if non_atomic_plot_points:
                app.logger.warning(f"Found {len(non_atomic_plot_points)} potentially non-atomic plot points out of {len(plot_points)} total.")
            else:
                app.logger.info("All plot points appear to be atomic.")

            app.logger.info("--- AI Service: Parsed campaign data successfully (new structure) ---")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            return parsed_data, model_used, usage_data
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content that failed JSON parsing: {generated_content}")
            return {"error": "AI response content is not valid JSON", "raw_content": generated_content}
        except Exception as e:
            app.logger.error(f"Error calling OpenAI API or processing response: {e}", exc_info=True)
            return {"error": f"Failed to call AI service: {e}"}

    def generate_initial_scene(self, game: Game) -> dict | None:
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate initial scene.")
            return None
        if not game.campaign:
            app.logger.error(f"Game {game.id} has no associated campaign loaded. Cannot generate initial scene.")
            return None
        game_state = GameState.query.filter_by(game_id=game.id).first()
        if not game_state:
            app.logger.error(f"Cannot generate initial scene for game {game.id}: Corresponding GameState not found.")
            return None
        campaign_data_dict = game.campaign.campaign_data or {}
        campaign_desc = campaign_data_dict.get('description', "A new adventure.")
        initial_state_dict = game_state.state_data or {}
        initial_state_desc = json.dumps(initial_state_dict, indent=2)
        prompt = (
            f"You are a game master starting a text adventure based on the following campaign:\\n"
            f"Description: {campaign_desc}\\n"
            f"Initial State: {initial_state_desc}\\n\\n"
            f"Generate the very first scene description (narrative) and the initial set of available actions for the player(s). "
            f"Output ONLY a JSON object with the keys 'narrative' (string, the opening scene description) and 'actions' (list of strings, the first available actions)."
        )
        app.logger.debug(f"--- AI Service: Generating initial scene with prompt ---\\n{prompt}\\n-------------------------------------------------")
        generated_content = ""
        try:
            # Use OPENAI_MODEL_LOGIC for critical logic-heavy calls
            model_to_use = app.config.get('OPENAI_MODEL_LOGIC', 'gpt-4o')
            app.logger.debug(f"Using OPENAI_MODEL_LOGIC for generate_initial_scene: {model_to_use}")
            app.logger.info(f"Attempting OpenAI API call for initial scene (Game {game.id})...")
            payload = {
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            log_ai_debug_payload("Generate initial scene", payload, "initial_scene", 1)
            response = self.client.chat.completions.create(**payload)
            app.logger.info(f"OpenAI API call successful for initial scene (Game {game.id}).")
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw initial scene response ---\\n{generated_content}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (generate_initial_scene) completed. Model: {model_used}, Usage Data: {usage_data}")
            parsed_data = json.loads(generated_content)
            app.logger.info(f"Attempting to parse JSON for initial scene (Game {game.id})...")
            app.logger.info(f"JSON parsing successful for initial scene (Game {game.id}).")
            if not all(k in parsed_data for k in ['narrative', 'actions']):
                app.logger.error("Initial scene response missing required keys ('narrative', 'actions').")
                return None
            if not isinstance(parsed_data.get('narrative'), str) or not isinstance(parsed_data.get('actions'), list):
                app.logger.error("Initial scene response has incorrect types for 'narrative' or 'actions'.")
                return None
            app.logger.info(f"--- AI Service: Parsed initial scene successfully for game {game.id} ---")
            return {'narrative': parsed_data['narrative'], 'actions': parsed_data['actions']}, model_used, usage_data
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding initial scene JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None, None, None
        except Exception as e:
            app.logger.error(f"Error generating initial scene: {e}", exc_info=True)
            return None, None, None

    def get_response(self, game_state: GameState, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None, current_difficulty: Optional[str] = None) -> dict | None:
        """Get AI response for player action in current game state, handling enhanced NPC and object states.
        
        Args:
            game_state: Current game state with enhanced NPC/object states
            player_action: Player's action text
            is_stuck: Whether player is stuck and needs guidance
            next_required_plot_point: Next required plot point description
            current_difficulty: Current game difficulty level
            
        Returns:
            Dict containing:
                - narrative: AI narrative response
                - state_changes: Dict of state updates including:
                    - npc_status: Updated NPC states with memory/interactions
                    - world_object_states: Updated object states/conditions
                - new_location: Optional new location
                - available_actions: Updated actions
        """
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot get response.")
            return None
        context = build_context(game_state, next_required_plot_point)
        if context.startswith("Error:"):
            app.logger.error(f"Error building context: {context}")
            return None
        app.logger.debug(f"--- AI Service: Context built for get_response ---\\n{context}\\n-------------------------------------------------")
        prompt = build_response_prompt(context, player_action, is_stuck, next_required_plot_point, current_difficulty)
        app.logger.debug(f"--- AI Service: Getting response with prompt ---\\n{prompt}\\n---------------------------------------------")
        generated_content = ""
        try:
            # Use OPENAI_MODEL_LOGIC for critical logic-heavy calls
            model_to_use = app.config.get('OPENAI_MODEL_LOGIC', 'gpt-4o')
            app.logger.debug(f"Using OPENAI_MODEL_LOGIC for get_response: {model_to_use}")
            payload = {
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            log_ai_debug_payload("Get AI response for player action", payload, "response", 1)
            response = self.client.chat.completions.create(**payload)
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\\n{generated_content}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (get_response) completed. Model: {model_used}, Usage Data: {usage_data}")
            parsed_data = json.loads(generated_content)

            if not isinstance(parsed_data.get('content'), str):
                app.logger.error("AI Stage 1 response 'content' (narrative) is missing or not a string.")
                return None
            if not isinstance(parsed_data.get('available_actions'), list):
                app.logger.error("AI Stage 1 response 'available_actions' is missing or not a list.")
                return None
            if not isinstance(parsed_data.get('available_actions'), list):
                app.logger.error("AI Stage 1 response 'available_actions' is missing or not a list.")
                return None

            ai_state_changes = parsed_data.get('state_changes', {})
            if not isinstance(ai_state_changes, dict):
                app.logger.error("AI Stage 1 response 'state_changes' is not a dictionary. Using empty state changes.")
                ai_state_changes = {}

            final_state_changes = {}
            previous_state_data = game_state.state_data or {}

            new_location = ai_state_changes.get('location')
            if isinstance(new_location, str) and new_location.strip():
                final_state_changes['location'] = new_location.strip()
            else:
                if 'location' in ai_state_changes:
                    app.logger.warning(f"AI provided invalid location: '{new_location}'. Falling back to previous location.")
                else:
                    app.logger.warning("AI did not provide 'location' in state_changes. Falling back to previous location.")
                final_state_changes['location'] = previous_state_data.get('location', "Unknown Location")

            # Handle inventory changes (items_added, items_removed)
            inventory_changes_from_ai = ai_state_changes.get('inventory_changes')
            current_inventory = previous_state_data.get('inventories', {}).get('shared', []) # Get current inventory from new structure

            if isinstance(inventory_changes_from_ai, dict):
                items_added = inventory_changes_from_ai.get('items_added', [])
                items_removed = inventory_changes_from_ai.get('items_removed', [])

                if isinstance(items_added, list) and all(isinstance(item, dict) and 'name' in item and isinstance(item['name'], str) for item in items_added):
                    # Add new items to inventory (only name for now, full object might be needed later)
                    for item_to_add in items_added:
                        if item_to_add['name'] not in current_inventory: # Avoid duplicates by name
                            current_inventory.append(item_to_add['name'])
                    app.logger.debug(f"Added items to inventory: {[item['name'] for item in items_added]}. Current inventory: {current_inventory}")
                else:
                    app.logger.warning(f"AI provided invalid 'items_added' format: '{items_added}'. Skipping additions.")

                if isinstance(items_removed, list) and all(isinstance(item, str) for item in items_removed):
                    # Remove items from inventory
                    current_inventory = [item for item in current_inventory if item not in items_removed]
                    app.logger.debug(f"Removed items from inventory: {items_removed}. Current inventory: {current_inventory}")
                else:
                    app.logger.warning(f"AI provided invalid 'items_removed' format: '{items_removed}'. Skipping removals.")
                
                # Removed: final_state_changes['inventory'] = current_inventory # This was the legacy inventory key
            else:
                # If AI didn't provide inventory_changes, or it was invalid, ensure no legacy 'inventory' key is added.
                if 'inventory_changes' in ai_state_changes:
                    app.logger.warning(f"AI provided invalid 'inventory_changes' (not a dict): '{inventory_changes_from_ai}'. Not updating inventory via AI.")
                else:
                    app.logger.debug("AI did not provide 'inventory_changes'. No inventory updates from AI for this turn.")
                # Ensure the legacy 'inventory' key is NOT added to final_state_changes
                # The 'inventories' object is managed by InventoryService and passed separately.

            new_npc_status = ai_state_changes.get('npc_status') # Changed from 'npc_states'
            if isinstance(new_npc_status, dict):
                valid_npc_status = True
                for npc_id, npc_data in new_npc_status.items():
                    if not isinstance(npc_id, str) or not isinstance(npc_data, dict):
                        valid_npc_status = False
                        break
                if valid_npc_status:
                    final_state_changes['npc_status'] = new_npc_status # Changed from 'npc_states'
                else:
                    app.logger.warning(f"AI provided 'npc_status' with invalid structure: '{new_npc_status}'. Falling back.")
                    final_state_changes['npc_status'] = previous_state_data.get('npc_status', {}) # Changed from 'npc_states'
            else:
                if 'npc_status' in ai_state_changes: # Changed from 'npc_states'
                    app.logger.warning(f"AI provided invalid npc_status (not a dict): '{new_npc_status}'. Falling back.")
                else:
                    app.logger.debug("AI did not provide 'npc_status'. Using previous or default.")
                final_state_changes['npc_status'] = previous_state_data.get('npc_status', {}) # Changed from 'npc_states'

            new_world_object_states = ai_state_changes.get('world_object_states') # Changed from 'world_objects'
            if isinstance(new_world_object_states, dict):
                valid_world_object_states = True
                for obj_id, obj_data in new_world_object_states.items():
                    if not isinstance(obj_id, str) or not isinstance(obj_data, dict):
                        valid_world_object_states = False
                        break
                if valid_world_object_states:
                    final_state_changes['world_object_states'] = new_world_object_states # Changed from 'world_objects'
                else:
                    app.logger.warning(f"AI provided 'world_object_states' with invalid structure: '{new_world_object_states}'. Falling back.")
                    final_state_changes['world_object_states'] = previous_state_data.get('world_object_states', {}) # Changed from 'world_objects'
            else:
                if 'world_object_states' in ai_state_changes: # Changed from 'world_objects'
                    app.logger.warning(f"AI provided invalid world_object_states (not a dict): '{new_world_object_states}'. Falling back.")
                else:
                    app.logger.debug("AI did not provide 'world_object_states'. Using previous or default.")
                final_state_changes['world_object_states'] = previous_state_data.get('world_object_states', {}) # Changed from 'world_objects'

            standard_keys = {'location', 'inventory', 'npc_status', 'world_object_states', 'achieved_plot_point_id'}
            for key, value in ai_state_changes.items():
                if key not in standard_keys:
                    final_state_changes[key] = value
                    app.logger.debug(f"Merged custom AI state key '{key}'.")

            if 'achieved_plot_point_id' in final_state_changes:
                app.logger.warning("AI Stage 1 response unexpectedly included 'achieved_plot_point_id'. This should be handled by Stage 3. Removing it.")
                del final_state_changes['achieved_plot_point_id']

            app.logger.info("--- AI Service: Processed and validated Stage 1 response data successfully ---")
            usage_data = response.usage if response.usage else None
            model_used = response.model

            stage_one_ai_output = {
                'narrative': parsed_data['content'],
                'state_changes': final_state_changes,
                'available_actions': parsed_data['available_actions']
            }
            return stage_one_ai_output, model_used, usage_data
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI Stage 1 JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error generating response: {e}", exc_info=True)
            return None

    def generate_character_name(self, description: str) -> str | None:
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate character name.")
            return None
        prompt = build_character_name_prompt(description)
        app.logger.debug(f"--- AI Service: Generating character name with prompt ---\\n{prompt}\\n-------------------------------------------------")
        generated_name = None
        try:
            # Use OPENAI_MODEL_MAIN for less critical calls
            model_to_use = app.config.get('OPENAI_MODEL_MAIN', 'gpt-4o-mini')
            app.logger.debug(f"Using OPENAI_MODEL_MAIN for generate_character_name: {model_to_use}")
            payload = {
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": 50
            }
            log_ai_debug_payload("Generate character name", payload, "charactername", 1)
            response = self.client.chat.completions.create(**payload)
            generated_name = response.choices[0].message.content.strip()
            app.logger.debug(f"--- AI Service: Received raw name response ---\\n{generated_name}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (generate_character_name) completed. Model: {model_used}, Usage Data: {usage_data}")
            generated_name = generated_name.strip('"\'')

            if not generated_name:
                app.logger.warning("AI generated an empty character name.")
                return None
            app.logger.info(f"--- AI Service: Generated character name successfully: {generated_name} ---")
            return generated_name
        except Exception as e:
            app.logger.error(f"Error calling OpenAI API or processing name response: {e}", exc_info=True)
            return None

    def generate_character_image(self, description: str) -> str | None:
        """Generate a character portrait image from a text description."""
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate image.")
            return None
        try:
            response = self.client.images.generate(prompt=description, n=1, size="512x512")
            url = response.data[0].url if response.data else None
            app.logger.info(f"Generated image for description '{description[:30]}...' -> {url}")
            return url
        except Exception as e:
            app.logger.error(f"Error generating character image: {e}", exc_info=True)
            return None

    def get_ai_hint(self, game_state: GameState, campaign: Campaign) -> Optional[Tuple[str, str, Optional[Dict[str, int]]]]:
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot get hint.")
            return None

        next_required_plot_point_desc = None
        state_data = game_state.state_data or {}
        if 'inventory' in state_data:
            app.logger.error("Legacy inventory format detected - rejecting request")
            return None
            
        completed_plot_points_data = state_data.get('completed_plot_points', [])
        if not isinstance(completed_plot_points_data, list):
            completed_plot_points_data = []
        completed_plot_point_ids = [pp.get('id') for pp in completed_plot_points_data if isinstance(pp, dict) and pp.get('id')]

        major_plot_points_list = campaign.major_plot_points
        if not isinstance(major_plot_points_list, list):
            major_plot_points_list = []

        for plot_point in major_plot_points_list:
            if isinstance(plot_point, dict) and plot_point.get('required') and plot_point.get('id') not in completed_plot_point_ids:
                next_required_plot_point_desc = plot_point.get('description')
                break

        context_for_hint = build_context(game_state, next_required_plot_point_desc)
        if context_for_hint.startswith("Error:"):
            app.logger.error(f"Error building context for hint: {context_for_hint}")
            return None

        app.logger.debug(f"--- AI Service: Context built for get_ai_hint ---\\n{context_for_hint}\\n-------------------------------------------------")

        campaign_objective_text = "Achieve the campaign goal."
        if campaign.campaign_data:
            campaign_data_dict = campaign.campaign_data
            if isinstance(campaign.campaign_data, str):
                try:
                    campaign_data_dict = json.loads(campaign.campaign_data)
                except json.JSONDecodeError:
                    app.logger.error(f"Failed to parse campaign.campaign_data string for game {game_state.game_id} in get_ai_hint.")
                    campaign_data_dict = {}

            if isinstance(campaign_data_dict, dict):
                campaign_objective_text = campaign_data_dict.get('campaign_objective', campaign_objective_text)
            else:
                app.logger.warning(f"campaign.campaign_data for game {game_state.game_id} is not a dict after potential parse in get_ai_hint.")

        prompt = build_hint_prompt(
            context=context_for_hint,
            campaign_objective=campaign_objective_text,
            next_required_plot_point_desc=next_required_plot_point_desc
        )
        app.logger.debug(f"--- AI Service: Getting hint with prompt ---\\n{prompt}\\n---------------------------------------------")

        generated_hint = ""
        try:
            # Use OPENAI_MODEL_MAIN for less critical calls
            model_to_use = app.config.get('OPENAI_MODEL_MAIN', 'gpt-4o-mini')
            app.logger.debug(f"Using OPENAI_MODEL_MAIN for get_ai_hint: {model_to_use}")

            payload = {
                "model": model_to_use,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": 150
            }
            log_ai_debug_payload("Get AI hint", payload, "hint", 1)
            response = self.client.chat.completions.create(**payload)
            generated_hint = response.choices[0].message.content.strip()
            app.logger.debug(f"--- AI Service: Received raw hint response ---\\n{generated_hint}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (get_ai_hint) completed. Model: {model_used}, Usage Data: {usage_data}")

            if not generated_hint:
                app.logger.warning("AI generated an empty hint.")
                return None

            if game_state.game_id and usage_data:
                cost = calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens, 'completion_tokens': usage_data.completion_tokens})
                log_api_usage(
                    model_name=model_used,
                    prompt_tokens=usage_data.prompt_tokens,
                    completion_tokens=usage_data.completion_tokens,
                    total_tokens=usage_data.total_tokens,
                    cost=cost,
                    game_id=game_state.game_id
                )

            return generated_hint, model_used, usage_data

        except Exception as e:
            app.logger.error(f"Error generating hint: {e}", exc_info=True)
            return None

    def check_atomic_plot_completion(
        self,
        plot_point_id: str,
        plot_point_description: str,
        current_game_state_data: Dict[str, Any],
        player_action: str,
        stage_one_narrative: str,
        game_id: Optional[int] = None
    ) -> Dict[str, Any] | None:
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot check plot point completion.")
            return None

        prompt = build_plot_completion_check_prompt(
            plot_point_id=plot_point_id,
            plot_point_description=plot_point_description,
            current_game_state_data=current_game_state_data,
            player_action=player_action,
            stage_one_narrative=stage_one_narrative
        )
        app.logger.debug(f"--- AI Service: Checking plot point completion with prompt ---\\n{prompt}\\n-------------------------------------------------")
        generated_content = ""
        try:
            # Use OPENAI_MODEL_MAIN for less critical calls; remove OPENAI_MODEL_PLOT_CHECK usage
            model_to_use = app.config.get('OPENAI_MODEL_MAIN', 'gpt-4o-mini')
            app.logger.debug(f"Using OPENAI_MODEL_MAIN for check_atomic_plot_completion: {model_to_use}")

            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": "You are an analytical AI assistant. Evaluate the game event based on the provided objective and context. Respond ONLY with the requested JSON object."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": 256
            }
            log_ai_debug_payload("Check atomic plot completion", payload, "plotcheck", 1)
            response = self.client.chat.completions.create(**payload)
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw plot check response ---\\n{generated_content}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (check_atomic_plot_completion) completed. Model: {model_used}, Usage Data: {usage_data}")

            parsed_data = json.loads(generated_content)

            required_keys = ['plot_point_id', 'completed', 'confidence_score']
            missing_keys = [k for k in required_keys if k not in parsed_data]
            if missing_keys:
                app.logger.error(f"AI plot check response missing required keys: {missing_keys}. Data: {parsed_data}")
                return {"error": f"AI response missing required keys: {', '.join(missing_keys)}", "raw_content": generated_content}

            if not isinstance(parsed_data.get('plot_point_id'), str) or parsed_data.get('plot_point_id') != plot_point_id:
                app.logger.error(f"AI plot check response 'plot_point_id' mismatch or not a string. Expected: {plot_point_id}, Got: {parsed_data.get('plot_point_id')}")
                return {"error": "Invalid 'plot_point_id' in AI response", "raw_content": generated_content}
            if not isinstance(parsed_data.get('completed'), bool):
                app.logger.error(f"AI plot check response 'completed' is not a boolean. Got: {parsed_data.get('completed')}")
                return {"error": "Invalid 'completed' type in AI response", "raw_content": generated_content}
            if not isinstance(parsed_data.get('confidence_score'), (float, int)):
                app.logger.error(f"AI plot check response 'confidence_score' is not a float/int. Got: {parsed_data.get('confidence_score')}")
                return {"error": "Invalid 'confidence_score' type in AI response", "raw_content": generated_content}

            confidence = float(parsed_data['confidence_score'])
            if not (0.0 <= confidence <= 1.0):
                app.logger.error(f"AI plot check response 'confidence_score' out of range (0.0-1.0). Got: {confidence}")
                return {"error": "'confidence_score' out of range", "raw_content": generated_content}
            parsed_data['confidence_score'] = confidence

            app.logger.info(f"--- AI Service: Parsed plot check data successfully for {plot_point_id} ---")

            usage_data = response.usage if response.usage else None
            model_used = response.model

            if game_id and usage_data:
                cost = calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens, 'completion_tokens': usage_data.completion_tokens})
                log_api_usage(
                    model_name=model_used,
                    prompt_tokens=usage_data.prompt_tokens,
                    completion_tokens=usage_data.completion_tokens,
                    total_tokens=usage_data.total_tokens,
                    cost=cost,
                    game_id=game_id
                )

            return {
                'plot_point_id': parsed_data['plot_point_id'],
                'completed': parsed_data['completed'],
                'confidence_score': parsed_data['confidence_score'],
                'model_used': model_used,
                'usage_data': {
                    'prompt_tokens': usage_data.prompt_tokens if usage_data else 0,
                    'completion_tokens': usage_data.completion_tokens if usage_data else 0,
                    'total_tokens': usage_data.total_tokens if usage_data else 0,
                } if usage_data else None
            }

        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI plot check JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return {"error": "AI response content is not valid JSON", "raw_content": generated_content}
        except Exception as e:
            app.logger.error(f"Error in check_atomic_plot_completion for {plot_point_id}: {e}", exc_info=True)
            return {"error": f"Failed to check plot point completion: {e}"}

    def generate_historical_summary(self, player_action: str, stage_one_narrative: str, state_changes: Dict[str, Any], game_id: Optional[int] = None) -> Optional[str]:
        """
        Generates a detailed historical summary of a game turn using a secondary AI model.
        The summary includes key actions, state changes, and notable events in 2-3 paragraphs.
        """
        from questforge.utils.ai_debug_logger import log_ai_debug_payload
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate historical summary.")
            return None

        prompt = build_summary_prompt(
            player_action=player_action,
            stage_one_narrative=stage_one_narrative,
            state_changes=state_changes
        )
        app.logger.debug(f"--- AI Service: Generating historical summary with prompt ---\\n{prompt}\\n-------------------------------------------------")
        
        generated_summary = ""
        try:
            model_to_use = app.config.get('OPENAI_MODEL_MAIN', 'gpt-4o-mini') # Use OPENAI_MODEL_MAIN
            app.logger.debug(f"Using OPENAI_MODEL_MAIN for generate_historical_summary: {model_to_use}")
            
            payload = {
                "model": model_to_use,
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that summarizes game events in rich detail. Output ONLY the summary text."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5, # Slightly lower temperature for more factual summary
                "max_tokens": 300 # Increased tokens for detailed summaries
            }

            response = self.client.chat.completions.create(**payload)
            generated_summary = response.choices[0].message.content.strip()
            
            app.logger.debug(f"--- AI Service: Received raw summary response ---\\n{generated_summary}\\n------------------------------------------")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            app.logger.info(f"AI call (generate_historical_summary) completed. Model: {model_used}, Usage Data: {usage_data}")

            if not generated_summary:
                app.logger.warning("AI generated an empty historical summary.")
                return None

            # Log API usage
            if game_id and usage_data:
                cost = calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens, 'completion_tokens': usage_data.completion_tokens})
                log_api_usage(
                    model_name=model_used,
                    prompt_tokens=usage_data.prompt_tokens,
                    completion_tokens=usage_data.completion_tokens,
                    total_tokens=usage_data.total_tokens,
                    cost=cost,
                    game_id=game_id
                )
                app.logger.info(f"Logged API usage for historical summary (Game {game_id}). Cost: {cost}")
            
            return generated_summary

        except Exception as e:
            app.logger.error(f"Error generating historical summary: {e}", exc_info=True)
            return None


def call_openai_api(prompt: str, model: str = 'gpt-4o') -> Tuple[Dict[str, Any], Decimal]:
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not configured.")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        cost = calculate_cost(model, response_data.get('usage', {}))
        return response_data, cost
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        raise


def calculate_cost(model: str, usage: Dict[str, int]) -> Decimal:
    app = current_app._get_current_object()
    pricing_config = app.config.get('OPENAI_PRICING', {})
    
    pricing_info = None
    
    # 1. Try exact match first
    if model in pricing_config:
        pricing_info = pricing_config[model]
        app.logger.debug(f"Found exact pricing key '{model}' for model '{model}'")
    else:
        # 2. Iteratively remove suffix components
        model_parts = model.split('-')
        for i in range(len(model_parts) - 1, 0, -1):
            potential_key = '-'.join(model_parts[:i])
            if potential_key in pricing_config:
                pricing_info = pricing_config[potential_key]
                app.logger.debug(f"Found partial pricing key '{potential_key}' for model '{model}'")
                break # Use the first partial match found
    
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    
    cost = Decimal('0.0')
    if pricing_info:
        prompt_cost_per_million = pricing_info.get('prompt', 0)
        completion_cost_per_million = pricing_info.get('completion', 0)
        
        prompt_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * Decimal(prompt_cost_per_million)
        completion_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * Decimal(completion_cost_per_million)
        cost = prompt_cost + completion_cost
        app.logger.debug(f"Calculated cost for model '{model}': prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, cost={cost}")
    else:
        app.logger.warning(f"No pricing info found for model '{model}'. Cost will be 0.")
        
    return cost.quantize(Decimal('0.000001'))


def log_api_usage(model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: Decimal, game_id: Optional[int] = None):
    """
    Logs API usage to the database.

    Args:
        model_name: The name of the AI model used.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total number of tokens.
        cost: The calculated cost of the API call.
        game_id: Optional ID of the game associated with the usage.
    """
    log_entry = ApiUsageLog(
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        game_id=game_id
    )
    db.session.add(log_entry)
    try:
        db.session.commit()
        current_app.logger.info(f"Successfully logged API usage for model {model_name} (Game ID: {game_id}). Cost: {cost}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to commit API usage log for model {model_name} (Game ID: {game_id}): {e}", exc_info=True)


ai_service = AIService()
