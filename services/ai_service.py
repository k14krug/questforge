import json
import os
import logging
import random
import uuid
import openai # Import the OpenAI library
from openai import OpenAI # Import the OpenAI client class

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIService:
    def __init__(self, app_config):
        self.app_config = app_config
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.pricing = self.app_config.get('OPENAI_PRICING', {})
        self.default_logic_model = self.app_config.get('OPENAI_MODEL_LOGIC', 'gpt-4o')
        self.default_main_model = self.app_config.get('OPENAI_MODEL_MAIN', 'gpt-4o-mini')
        self.default_temperature = self.app_config.get('OPENAI_TEMPERATURE', 0.7)
        self.default_max_tokens = self.app_config.get('OPENAI_MAX_TOKENS', 1024)

    def calculate_cost(self, model_name, prompt_tokens, completion_tokens):
        """Calculates the cost of an AI call based on token usage using pricing from app_config."""
        model_pricing = self.pricing.get(model_name)
        if not model_pricing:
            logging.warning(f"Cost calculation failed: Model '{model_name}' pricing not found in config.")
            return 0.0

        input_cost_per_thousand_tokens = model_pricing.get('prompt', 0.0)
        output_cost_per_thousand_tokens = model_pricing.get('completion', 0.0)

        cost = (prompt_tokens / 1000 * input_cost_per_thousand_tokens) + \
               (completion_tokens / 1000 * output_cost_per_thousand_tokens)
        return cost

    def generate_text(self, model_name, prompt, max_tokens=None, temperature=None):
        """
        Generates text using the OpenAI Chat Completions API.
        """
        model_name = model_name or self.default_main_model
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature

        messages = [
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for text generation with model: {model_name}")
            logging.debug(f"Prompt: {prompt[:200]}...") # Log first 200 chars of prompt

            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            generated_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI text generation cost: {cost:.4f}")
            return generated_text, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during text generation: {e}")
            return None, 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during text generation: {e}")
            return None, 0.0, 0, 0

    def generate_campaign_charter(self, template_data, game_settings):
        """
        Generates a Campaign Charter in a more reliable two-step process.
        Step 1: Generate the core narrative content.
        Step 2: Generate the interactive map based on the narrative content.
        Returns: (charter, cost, prompt_tokens, completion_tokens, models_used)
        """
        total_cost = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        models_used = []

        # Step 1: Generate the core narrative content (without the map)
        narrative_charter, cost, p_tokens, c_tokens, model = self._generate_narrative_charter(template_data, game_settings)
        total_cost += cost
        total_prompt_tokens += p_tokens
        total_completion_tokens += c_tokens
        if model:
            models_used.append(model)

        if not narrative_charter:
            logging.error("Failed to generate narrative charter in Step 1. Aborting.")
            return {}, total_cost, total_prompt_tokens, total_completion_tokens, models_used

        # Step 2: Generate the interactive map based on the setting description
        setting_description = narrative_charter.get("setting_description", "")
        if setting_description:
            map_layout, cost, p_tokens, c_tokens, model = self._generate_interactive_map_layout(setting_description)
            total_cost += cost
            total_prompt_tokens += p_tokens
            total_completion_tokens += c_tokens
            if model:
                models_used.append(model)
            narrative_charter['interactive_map_layout'] = map_layout
        else:
            logging.warning("No setting_description found in narrative charter. Skipping map generation.")
            narrative_charter['interactive_map_layout'] = {"nodes": [], "edges": []} # Add empty map

        return narrative_charter, total_cost, total_prompt_tokens, total_completion_tokens, models_used

    def generate_character_sheet(self, character_keywords, core_skills):
        """
        Generates a character sheet using the OpenAI Chat Completions API.
        The AI is instructed to output a JSON object.
        """
        model_name = self.default_main_model # Use a secondary model for this utility task
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        prompt = f"""
        Generate a character sheet in JSON format based on the provided character keywords and core skills.
        The character sheet should include a "skills" object where each core skill is assigned a numerical value (e.g., -2 to 3).

        Character Keywords: {character_keywords}
        Core Skills for Campaign: {core_skills}

        The JSON output should strictly follow this structure:
        {{
            "character_sheet": {{
                "skills": {{
                    "SkillName1": integer,
                    "SkillName2": integer
                }},
                "attributes": {{
                    "Strength": integer,
                    "Dexterity": integer,
                    "Constitution": integer,
                    "Intelligence": integer,
                    "Wisdom": integer,
                    "Charisma": integer
                }},
                "inventory": [],
                "equipment": [],
                "abilities": []
            }}
        }}

        Ensure all core skills are present in the "skills" object. Populate other fields with reasonable defaults or creative suggestions.
        """

        messages = [
            {"role": "system", "content": "You are an AI that generates structured JSON for RPG character sheets."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for character sheet generation with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"} # Ensure JSON output
            )

            generated_json_str = response.choices[0].message.content
            character_sheet_data = json.loads(generated_json_str)
            
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI character sheet generation cost: {cost:.4f}")
            return character_sheet_data, cost, prompt_tokens, completion_tokens, model_name

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during character sheet generation: {e}")
            return {"character_sheet": {"skills": {}}}, 0.0, 0, 0, None
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error from OpenAI response: {e}. Response: {generated_json_str[:500]}...")
            return {"character_sheet": {"skills": {}}}, 0.0, 0, 0, None
        except Exception as e:
            logging.error(f"An unexpected error occurred during character sheet generation: {e}")
            return {"character_sheet": {"skills": {}}}, 0.0, 0, 0, None

    def _generate_narrative_charter(self, template_data, game_settings):
        model_name = self.default_logic_model
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        prompt = f"""
        Generate the narrative part of a Campaign Charter in JSON format based on the provided data.

        Template Data: {json.dumps(template_data, indent=2)}
        Game Settings: {json.dumps(game_settings, indent=2)}

        The JSON output should strictly follow this structure, omitting the map layout:
        {{
            "campaign_name": "string",
            "setting_description": "string",
            "core_conflict": "string",
            "initial_player_context": "string",
            "ai_directives": {{...}},
            "game_rules": {{...}},
            "initial_state_elements": {{
                "starting_location": "string",
                "key_npcs": [{{...}}]
            }},
            "critical_path_objectives": ["string"],
            "core_skills_for_campaign": ["string"],
            "ai_gm_persona_for_campaign": "string",
            "game_settings_at_charter_creation": {{}}
        }}

        CRITICAL JSON RULES:
        1. The entire output MUST be a single, valid JSON object.
        2. Ensure all string values are properly escaped (e.g., " for quotes).
        """
        messages = [
            {"role": "system", "content": "You generate structured JSON for the narrative part of RPG campaign charters."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for narrative charter with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            narrative_charter = json.loads(response.choices[0].message.content)
            cost = self.calculate_cost(model_name, response.usage.prompt_tokens, response.usage.completion_tokens)
            return narrative_charter, cost, response.usage.prompt_tokens, response.usage.completion_tokens, model_name
        except Exception as e:
            logging.error(f"Error in _generate_narrative_charter: {e}")
            return {}, 0.0, 0, 0, None
            return None, 0.0, 0, 0

    def _generate_interactive_map_layout(self, setting_description):
        model_name = self.default_logic_model
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        prompt = f"""
        Based on the following setting description, generate an interactive map layout with 3-5 key locations (nodes) and the connections between them (edges).

        Setting Description: {setting_description}

        The JSON output must strictly follow this structure:
        {{
            "nodes": [
                {{"id": "string (unique identifier)", "name": "string", "description": "string"}}
            ],
            "edges": [
                {{"from": "string (node id)", "to": "string (node id)", "description": "string (e.g., a locked door, a hallway)"}}
            ]
        }}

        CRITICAL JSON RULES:
        1. The entire output MUST be a single, valid JSON object.
        2. Ensure all string values are properly escaped.
        """
        messages = [
            {"role": "system", "content": "You generate structured JSON for RPG map layouts."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for interactive map layout with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            map_layout = json.loads(response.choices[0].message.content)
            cost = self.calculate_cost(model_name, response.usage.prompt_tokens, response.usage.completion_tokens)
            return map_layout, cost, response.usage.prompt_tokens, response.usage.completion_tokens, model_name
        except Exception as e:
            logging.error(f"Error in _generate_interactive_map_layout: {e}")
            return {"nodes": [], "edges": []}, 0.0, 0, 0, None

    def generate_player_npc_image_url(self, description, entity_type="character"):
        """
        Generates an image URL for a player or NPC using the OpenAI DALL-E API.
        """
        # DALL-E models don't use the same pricing model as chat completions,
        # so cost calculation here is a placeholder or needs a separate pricing structure.
        # For simplicity, we'll use a fixed cost or 0 for now.
        model_name = "dall-e-3" # Assuming dall-e-3 for image generation
        
        prompt = f"Generate a realistic image for an RPG {entity_type} based on this description: {description}. Focus on a fantasy art style."

        try:
            logging.info(f"Calling OpenAI DALL-E for image generation for {entity_type}: {description[:50]}...")
            response = self.client.images.generate(
                model=model_name,
                prompt=prompt,
                n=1, # Number of images to generate
                size="1024x1024" # Image size
            )

            image_url = response.data[0].url
            # DALL-E pricing is per image, not tokens. This is a placeholder cost.
            # A more accurate cost would come from a DALL-E specific pricing config.
            cost = self.pricing.get(model_name, {}).get('cost_per_image', 0.02) # Example cost for DALL-E 3
            prompt_tokens = len(prompt.split()) # Rough estimate for logging
            completion_tokens = 0 # No completion tokens for image generation

            logging.info(f"OpenAI DALL-E image generation cost: {cost:.4f}")
            return image_url, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during image generation: {e}")
            return None, 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during image generation: {e}")
            return None, 0.0, 0, 0

    def generate_ai_assisted_backstory(self, character_name, character_description, game_context):
        """
        Generates an AI-assisted backstory using the OpenAI Chat Completions API.
        """
        model_name = self.default_main_model # Use a secondary model for this utility task
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        prompt = f"""
        Generate a concise and engaging backstory for a character in an RPG.
        Character Name: {character_name}
        Character Description: {character_description}
        Game Context (World Description, Core Conflict, etc.): {json.dumps(game_context, indent=2)}

        The backstory should be about 3-5 paragraphs long and fit within the provided game context.
        """

        messages = [
            {"role": "system", "content": "You are a creative AI that generates RPG character backstories."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for AI-assisted backstory generation for {character_name} with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            generated_backstory = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI AI-assisted backstory generation cost: {cost:.4f}")
            return generated_backstory, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during backstory generation: {e}")
            return "A mysterious past awaits discovery.", 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during backstory generation: {e}")
            return "A mysterious past awaits discovery.", 0.0, 0, 0

    def generate_story_summary(self, game_log_entries, game_state_snapshot, charter):
        """
        Generates a "Story So Far" summary using the OpenAI Chat Completions API.
        """
        model_name = self.default_main_model # Use a secondary model for this utility task
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        # Condense game_log_entries for prompt efficiency if too long
        condensed_log = []
        if game_log_entries:
            # Take recent entries and perhaps a few key early ones
            if len(game_log_entries) > 10: # Example threshold
                condensed_log = game_log_entries[:3] + game_log_entries[-7:]
            else:
                condensed_log = game_log_entries

        prompt = f"""
        Generate a concise "Story So Far" summary for an RPG campaign.
        Focus on key events, player progress, and the current state of the world.

        Campaign Charter (for context):
        {json.dumps(charter, indent=2)}

        Current Game State Snapshot:
        {json.dumps(game_state_snapshot, indent=2)}

        Recent Game Log Entries (condensed if necessary):
        {json.dumps(condensed_log, indent=2)}

        Summarize the narrative in 2-4 paragraphs, highlighting the most important developments.
        """

        messages = [
            {"role": "system", "content": "You are an AI that generates concise RPG story summaries."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for 'Story So Far' summary generation with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            generated_summary = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI 'Story So Far' summary generation cost: {cost:.4f}")
            return generated_summary, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during story summary generation: {e}")
            return "The story continues...", 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during story summary generation: {e}")
            return "The story continues...", 0.0, 0, 0

    def process_action_step1_check_identification(self, player_action_text, game_state, charter, character_sheet):
        """
        AI Step 1: Check Identification.
        AI analyzes player action and responds with structured JSON for skill checks using OpenAI.
        """
        model_name = self.default_logic_model # Primary model for core game logic
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        # Directive of Adherence: AI strictly adheres to Campaign Charter and GameState.
        # This is implicitly handled by including game_state and charter in the prompt.
        
        prompt = f"""
        Analyze the player's action and determine if a skill check is required in the context of the game.
        If a skill check is required, you MUST choose a skill from the character's actual skill list.

        Player Action: "{player_action_text}"
        Current Game State: {json.dumps(game_state, indent=2)}
        Campaign Charter: {json.dumps(charter, indent=2)}
        Character Sheet: {json.dumps(character_sheet, indent=2)}

        IMPORTANT CONTEXT:
        - Current Location: {game_state.get('current_location', 'Unknown')}
        - Critical Path Objectives: {', '.join(charter.get('critical_path_objectives', []))}
        - Interactive Map Available: {'Yes' if charter.get('interactive_map_layout', {}).get('nodes') else 'No'}
        - Current Inventory: {game_state.get('inventory', [])}
        
        INVENTORY VALIDATION RULES:
        - If the player tries to use a specific item (like "hammer", "rope", "flashlight"), check if it exists in the inventory
        - Items in the character sheet are starting equipment, NOT current inventory
        - Only allow use of items that are currently in the inventory list
        - If player tries to use an item not in inventory, the narration should indicate they don't have that item
        
        NARRATIVE GUIDANCE:
        - If the player is moving between locations, acknowledge the new environment
        - Introduce appropriate challenges, discoveries, or NPCs for the new location
        - Progress the story meaningfully rather than giving generic "continue moving" responses
        - Reference specific map locations and their descriptions when relevant
        - Create meaningful obstacles or discoveries that advance the critical path objectives

        Output a JSON object strictly following this structure:
        {{
            "action_requires_roll": boolean,
            "skill": "string (e.g., Athletics, Persuasion, Combat)",
            "difficulty": integer (10-25),
            "narration_prompt": "string"
        }}

        If no roll is required, set "action_requires_roll" to false, and provide a detailed narration prompt that advances the story meaningfully.
        """

        messages = [
            {"role": "system", "content": "You are an AI Game Master assisting in action resolution. Your task is to determine if a player action requires a skill check and provide structured JSON output."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for AI Step 1 (Check Identification) for action: '{player_action_text[:50]}...' with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"} # Ensure JSON output
            )

            generated_json_str = response.choices[0].message.content
            ai_response_json = json.loads(generated_json_str)
            
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI AI Step 1 cost: {cost:.4f}")
            return ai_response_json, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during AI Step 1: {e}")
            return {"action_requires_roll": False, "narration_prompt": "Your action had an unexpected outcome due to an AI error."}, 0.0, 0, 0
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error from OpenAI response in AI Step 1: {e}. Response: {generated_json_str[:500]}...")
            return {"action_requires_roll": False, "narration_prompt": "Your action had an unexpected outcome due to an AI response format error."}, 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during AI Step 1: {e}")
            return {"action_requires_roll": False, "narration_prompt": "Your action had an unexpected outcome due to an internal error."}, 0.0, 0, 0

    def process_action_step2_outcome_narration(self, roll_result, narration_prompt, game_state, charter):
        """
        AI Step 2: Outcome Narration.
        AI receives roll result and narration_prompt, then generates narrative outcome using OpenAI.
        Integrates Narrative Redirection and Deviation Budget directives.
        """
        model_name = self.default_logic_model # Primary model for core game logic
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        # Directive of Adherence: AI strictly adheres to Campaign Charter and GameState.
        # This is implicitly handled by including game_state and charter in the prompt.
        
        # Narrative Redirection & Deviation Budget logic will be incorporated into the prompt
        # to guide the AI's generation.

        ai_gm_persona = charter.get('ai_gm_persona_for_campaign', 'The Chronicler')
        critical_path_objectives = charter.get('critical_path_objectives') or charter.get('initial_state_elements', {}).get('initial_quests', [])
        current_location = game_state.get('current_location', 'an unknown location')

        system_message_content = f"""
        You are an AI Game Master. Your task is to narrate the outcome of a player's action, incorporating the result of a skill check.
        Adhere strictly to the Campaign Charter and the current Game State.
        
        AI GM Persona: {ai_gm_persona}. This persona influences your narrative style and tendency for deviation.
        
        Current Critical Path Objectives: {', '.join(critical_path_objectives) if critical_path_objectives else 'None defined'}.
        Current Player Location: {current_location}.
        
        IMPORTANT NARRATIVE REQUIREMENTS:
        - Create meaningful story progression, not generic responses
        - If the player has moved to a new location, describe the new environment in detail
        - Introduce location-specific challenges, NPCs, or discoveries
        - Reference the interactive map layout and location descriptions from the Campaign Charter
        - Advance at least one critical path objective when possible
        - Avoid repetitive "continue moving" narratives - create actual story beats
        
        If the player seems to be deviating significantly from the critical path objectives, subtly guide the narrative back towards them.
        You have a conceptual "Deviation Budget" to introduce minor, unscripted elements or twists. A '{ai_gm_persona}' persona might have a {'higher' if ai_gm_persona != 'The Chronicler' else 'moderate'} implicit budget. Use this sparingly to add emergent gameplay, but do not derail the main narrative.
        """

        prompt = f"""
        Based on the following skill check result and initial narration prompt, generate a detailed narrative outcome.

        Skill Check Result: {json.dumps(roll_result, indent=2)}
        Initial Narration Prompt: "{narration_prompt}"
        Current Game State: {json.dumps(game_state, indent=2)}
        Campaign Charter: {json.dumps(charter, indent=2)}

        Generate a narrative outcome that is consistent with the game world, the skill check result, and the AI directives.
        """

        messages = [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info(f"Calling OpenAI for AI Step 2 (Outcome Narration) for outcome: {roll_result['outcome']} with model: {model_name}")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            outcome_message = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI AI Step 2 cost: {cost:.4f}")
            return outcome_message, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during AI Step 2: {e}")
            return "An unexpected narrative outcome occurred due to an AI error.", 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during AI Step 2: {e}")
            return "An unexpected narrative outcome occurred due to an internal error.", 0.0, 0, 0

    def generate_epilogue(self, final_game_state, campaign_charter, player_characters_data):
        """
        Generates a Post-Campaign Epilogue using the OpenAI Chat Completions API.
        This method integrates the Post-Campaign Epilogue directive.
        """
        model_name = self.default_logic_model # Primary model for narrative generation
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        prompt = f"""
        Generate a concise and satisfying Post-Campaign Epilogue for an RPG campaign.
        The epilogue should summarize the campaign's conclusion, reflecting player choices, the final game state, and the ultimate fates of characters.

        Final Game State:
        {json.dumps(final_game_state, indent=2)}

        Campaign Charter:
        {json.dumps(campaign_charter, indent=2)}

        Player Characters Data:
        {json.dumps(player_characters_data, indent=2)}

        Content Elements to include:
        - Character Fates: What happened to the player characters and key NPCs.
        - World State: How the campaign's core conflict was resolved and the lasting impact on the world.
        - Consequences: A reflection of the major choices made by the players and their ultimate outcomes.
        - Tone: The tone should align with the overall campaign genre and the final outcome (e.g., triumphant, bittersweet, tragic).

        Generate the epilogue in 3-5 paragraphs.
        """

        messages = [
            {"role": "system", "content": "You are an AI Game Master that generates compelling post-campaign epilogues."},
            {"role": "user", "content": prompt}
        ]

        try:
            logging.info("Calling OpenAI for Post-Campaign Epilogue generation.")
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            epilogue_text = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            cost = self.calculate_cost(model_name, prompt_tokens, completion_tokens)

            logging.info(f"OpenAI Post-Campaign Epilogue generation cost: {cost:.4f}")
            return epilogue_text, cost, prompt_tokens, completion_tokens

        except openai.APIError as e:
            logging.error(f"OpenAI API Error during epilogue generation: {e}")
            return "The campaign concluded, leaving many tales untold due to an AI error.", 0.0, 0, 0
        except Exception as e:
            logging.error(f"An unexpected error occurred during epilogue generation: {e}")
            return "The campaign concluded, leaving many tales untold due to an internal error.", 0.0, 0, 0
