import os
import json # Add json import
from openai import OpenAI
from flask import current_app
from questforge.models.game import Game
from questforge.models.game_state import GameState
from questforge.models.template import Template
from questforge.models.campaign import Campaign # Import Campaign
from questforge.utils.prompt_builder import build_campaign_prompt, build_response_prompt, build_character_name_prompt, build_hint_prompt
from questforge.utils.context_manager import build_context
from typing import Dict, Optional, Tuple, Any 
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

    def generate_campaign(self, template: Template, template_overrides: Optional[Dict[str, Any]] = None, creator_customizations: Optional[Dict[str, Any]] = None, player_details: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Any]:
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate campaign.")
            return {"error": "AI service not available."}
        prompt = build_campaign_prompt(template, template_overrides, creator_customizations, player_details) 
        app.logger.debug(f"--- AI Service: Generating campaign with prompt ---\n{prompt}\n-------------------------------------------------")
        generated_content = ""
        try:
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-4o') 
            app.logger.debug(f"Using model from config for generate_campaign: {model_to_use}")
            response = self.client.chat.completions.create(
                model=model_to_use, 
                messages=[
                    {"role": "system", "content": "You are a creative game master designing the beginning of a text-based adventure game according to the user's template and inputs. Output ONLY the requested JSON object."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }, 
                temperature=self.temperature,
                max_tokens=2048 # Increased max_tokens for campaign generation
            )
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\n{generated_content}\n------------------------------------------")
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
            f"You are a game master starting a text adventure based on the following campaign:\n"
            f"Description: {campaign_desc}\n"
            f"Initial State: {initial_state_desc}\n\n"
            f"Generate the very first scene description (narrative) and the initial set of available actions for the player(s). "
            f"Output ONLY a JSON object with the keys 'narrative' (string, the opening scene description) and 'actions' (list of strings, the first available actions)."
        )
        app.logger.debug(f"--- AI Service: Generating initial scene with prompt ---\n{prompt}\n-------------------------------------------------")
        generated_content = ""
        try:
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
            app.logger.debug(f"Using model from config for generate_initial_scene: {model_to_use}")
            app.logger.info(f"Attempting OpenAI API call for initial scene (Game {game.id})...")
            response = self.client.chat.completions.create(
                model=model_to_use, 
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=self.temperature, 
                max_tokens=self.max_tokens
            )
            app.logger.info(f"OpenAI API call successful for initial scene (Game {game.id}).")
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw initial scene response ---\n{generated_content}\n------------------------------------------")
            app.logger.info(f"Attempting to parse JSON for initial scene (Game {game.id})...")
            parsed_data = json.loads(generated_content)
            app.logger.info(f"JSON parsing successful for initial scene (Game {game.id}).")
            if not all(k in parsed_data for k in ['narrative', 'actions']):
                 app.logger.error("Initial scene response missing required keys ('narrative', 'actions').")
                 return None
            if not isinstance(parsed_data.get('narrative'), str) or not isinstance(parsed_data.get('actions'), list):
                 app.logger.error("Initial scene response has incorrect types for 'narrative' or 'actions'.")
                 return None
            app.logger.info(f"--- AI Service: Parsed initial scene successfully for game {game.id} ---")
            return {'narrative': parsed_data['narrative'], 'actions': parsed_data['actions']}
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding initial scene JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error generating initial scene: {e}", exc_info=True)
            return None

    def get_response(self, game_state: GameState, player_action: str, is_stuck: bool = False, next_required_plot_point: Optional[str] = None) -> dict | None:
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot get response.")
            return None
        context = build_context(game_state, next_required_plot_point)
        if context.startswith("Error:"):
            app.logger.error(f"Error building context: {context}")
            return None
        app.logger.debug(f"--- AI Service: Context built for get_response ---\n{context}\n-------------------------------------------------")
        prompt = build_response_prompt(context, player_action, is_stuck, next_required_plot_point)
        app.logger.debug(f"--- AI Service: Getting response with prompt ---\n{prompt}\n---------------------------------------------")
        generated_content = ""
        try:
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
            app.logger.debug(f"Using model from config for get_response: {model_to_use}")
            response = self.client.chat.completions.create(
                model=model_to_use, 
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }, 
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            generated_content = response.choices[0].message.content
            app.logger.debug(f"--- AI Service: Received raw response ---\n{generated_content}\n------------------------------------------")
            parsed_data = json.loads(generated_content)
            if not all(k in parsed_data for k in ['content', 'state_changes', 'available_actions']):
                 app.logger.error("AI response missing required keys ('content', 'state_changes', 'available_actions').")
                 return None
            if not isinstance(parsed_data.get('state_changes'), dict):
                 app.logger.error("AI response 'state_changes' is not a dictionary.")
                 return None
            if not isinstance(parsed_data.get('available_actions'), list):
                 app.logger.error("AI response 'available_actions' is not a list.")
                 return None
            app.logger.info("--- AI Service: Parsed response data successfully ---")
            usage_data = response.usage if response.usage else None
            model_used = response.model
            response_dict = {
                'narrative': parsed_data['content'],
                'state_changes': parsed_data['state_changes'],
                'available_actions': parsed_data['available_actions']
            }
            return response_dict, model_used, usage_data
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding AI JSON response: {e}")
            app.logger.error(f"Raw content: {generated_content}")
            return None
        except Exception as e:
            app.logger.error(f"Error generating response: {e}", exc_info=True)
            return None

    def generate_character_name(self, description: str) -> str | None:
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot generate character name.")
            return None
        prompt = build_character_name_prompt(description)
        app.logger.debug(f"--- AI Service: Generating character name with prompt ---\n{prompt}\n-------------------------------------------------")
        generated_name = None
        try:
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-4o')
            app.logger.debug(f"Using model from config for generate_character_name: {model_to_use}")
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature, 
                max_tokens=50 
            )
            generated_name = response.choices[0].message.content.strip()
            app.logger.debug(f"--- AI Service: Received raw name response ---\n{generated_name}\n------------------------------------------")
            generated_name = generated_name.strip('"\'')
            if not generated_name:
                app.logger.warning("AI generated an empty character name.")
                return None
            app.logger.info(f"--- AI Service: Generated character name successfully: {generated_name} ---")
            return generated_name
        except Exception as e:
            app.logger.error(f"Error calling OpenAI API or processing name response: {e}", exc_info=True)
            return None

    def get_ai_hint(self, game_state: GameState, campaign: Campaign) -> Optional[Tuple[str, str, Optional[Dict[str, int]]]]:
        """
        Gets a hint from the AI based on the current game state and campaign.

        Args:
            game_state: The current GameState object.
            campaign: The current Campaign object.

        Returns:
            A tuple containing the hint text (str), model_used (str), and usage_data (dict),
            or None on failure.
        """
        app = current_app._get_current_object()
        if not self.client:
            app.logger.error("OpenAI client not initialized. Cannot get hint.")
            return None

        next_required_plot_point_desc = None
        state_data = game_state.state_data or {}
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
        
        app.logger.debug(f"--- AI Service: Context built for get_ai_hint ---\n{context_for_hint}\n-------------------------------------------------")

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
        app.logger.debug(f"--- AI Service: Getting hint with prompt ---\n{prompt}\n---------------------------------------------")

        generated_hint = ""
        try:
            model_to_use = app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo') 
            app.logger.debug(f"Using model from config for get_ai_hint: {model_to_use}")
            
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=150 
            )
            generated_hint = response.choices[0].message.content.strip()
            app.logger.debug(f"--- AI Service: Received raw hint response ---\n{generated_hint}\n------------------------------------------")

            if not generated_hint:
                app.logger.warning("AI generated an empty hint.")
                return None

            usage_data = response.usage if response.usage else None
            model_used = response.model
            
            if game_state.game_id and usage_data: 
                cost = calculate_cost(model_used, {'prompt_tokens': usage_data.prompt_tokens, 'completion_tokens': usage_data.completion_tokens})
                log_api_usage( # No player_id here
                    model_name=model_used,
                    prompt_tokens=usage_data.prompt_tokens,
                    completion_tokens=usage_data.completion_tokens,
                    total_tokens=usage_data.total_tokens,
                    cost=cost,
                    # endpoint='get_ai_hint', # Removed endpoint
                    game_id=game_state.game_id
                )
            
            return generated_hint, model_used, usage_data

        except Exception as e:
            app.logger.error(f"Error generating hint: {e}", exc_info=True)
            return None

# Helper functions for API calls and cost calculation (moved from game.py)
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
        "response_format": { "type": "json_object" } 
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
    pricing = current_app.config.get('OPENAI_PRICING', {})
    prompt_tokens = usage.get('prompt_tokens', 0)
    completion_tokens = usage.get('completion_tokens', 0)
    prompt_cost_per_million = pricing.get(model, {}).get('prompt', 0)
    completion_cost_per_million = pricing.get(model, {}).get('completion', 0)
    prompt_cost = (Decimal(prompt_tokens) / Decimal(1_000_000)) * Decimal(prompt_cost_per_million)
    completion_cost = (Decimal(completion_tokens) / Decimal(1_000_000)) * Decimal(completion_cost_per_million)
    total_cost = prompt_cost + completion_cost
    return total_cost.quantize(Decimal('0.000001'))

def log_api_usage(model_name: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, cost: Decimal, game_id: Optional[int] = None): # Removed endpoint from signature
    """
    Logs API usage to the database.
    
    Args:
        model_name: The name of the AI model used.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens: Total number of tokens.
        cost: The calculated cost of the API call.
        # endpoint: A string identifying the API endpoint or action. # Removed endpoint from docstring
        game_id: Optional ID of the game associated with the usage.
    """
    log_entry = ApiUsageLog( # No player_id here
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        # endpoint=endpoint, # Removed endpoint from instantiation
        game_id=game_id
    )
    db.session.add(log_entry)
    db.session.commit()

# Singleton instance
ai_service = AIService()
