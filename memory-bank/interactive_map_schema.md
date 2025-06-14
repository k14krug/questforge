# Interactive Map JSON Schema

This document provides a detailed JSON schema for the "node-based JSON structure of locations and their connections" for the interactive map within the QuestForge application. This schema will be part of the `Campaign Charter` and will define the structure for representing the campaign world's geography.

## 1. Overview

The interactive map is represented as a graph where `locations` are nodes and `connections` are edges. This structure allows for flexible and dynamic world generation and navigation.

## 2. JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Interactive Map Layout",
  "description": "A node-based JSON structure defining locations and their connections for the interactive campaign map.",
  "type": "object",
  "properties": {
    "locations": {
      "type": "array",
      "description": "A list of all unique locations (nodes) in the campaign map.",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string",
            "description": "Unique identifier for the location (e.g., 'forest_clearing', 'silverhaven_city'). This ID must be unique within the 'locations' array."
          },
          "name": {
            "type": "string",
            "description": "Human-readable name of the location."
          },
          "description": {
            "type": "string",
            "description": "A brief narrative description of the location, providing context and atmosphere."
          },
          "coordinates": {
            "type": "object",
            "description": "X, Y coordinates for rendering the location on a 2D interactive map. These coordinates are relative to the map's canvas.",
            "properties": {
              "x": {
                "type": "number",
                "description": "X-coordinate of the location on the map."
              },
              "y": {
                "type": "number",
                "description": "Y-coordinate of the location on the map."
              }
            },
            "required": ["x", "y"]
          },
          "type": {
            "type": "string",
            "description": "Categorization of the location (e.g., 'city', 'dungeon', 'wilderness', 'landmark'). This helps in rendering and AI understanding.",
            "enum": ["city", "town", "village", "dungeon", "wilderness", "landmark", "settlement", "ruin", "cave", "mountain", "forest", "river", "lake", "ocean", "other"]
          },
          "is_starting_location": {
            "type": "boolean",
            "description": "Indicates if this location is a potential starting point for player characters in a new game.",
            "default": false
          },
          "key_elements": {
            "type": "array",
            "description": "A list of important NPCs, items, or significant features present within this location. These can be references to other charter components.",
            "items": {
              "type": "string"
            },
            "default": []
          }
        },
        "required": ["id", "name", "description", "coordinates", "type"]
      },
      "minItems": 1,
      "uniqueItems": true
    },
    "connections": {
      "type": "array",
      "description": "A list of connections (edges) between locations, representing paths, roads, rivers, or other traversable routes.",
      "items": {
        "type": "object",
        "properties": {
          "from_location_id": {
            "type": "string",
            "description": "The ID of the starting location for this connection. Must refer to an 'id' in the 'locations' array."
          },
          "to_location_id": {
            "type": "string",
            "description": "The ID of the destination location for this connection. Must refer to an 'id' in the 'locations' array."
          },
          "description": {
            "type": "string",
            "description": "A brief narrative description of the connection (e.g., 'a winding forest path', 'a treacherous mountain pass', 'the swift river')."
          },
          "is_one_way": {
            "type": "boolean",
            "description": "If true, the connection can only be traversed from 'from_location_id' to 'to_location_id'. If false, it's a two-way connection.",
            "default": false
          },
          "difficulty": {
            "type": "string",
            "description": "Optional difficulty or challenge associated with traversing this connection, influencing AI narrative and potential skill checks.",
            "enum": ["easy", "medium", "hard", "dangerous", "deadly", "impossible"],
            "nullable": true
          },
          "required_skill_check": {
            "type": "object",
            "description": "Optional skill check required to traverse this connection. If present, players may need to pass this check.",
            "properties": {
              "skill": {
                "type": "string",
                "description": "The name of the skill required (e.g., 'Athletics', 'Stealth', 'Survival'). Must be one of the 'Core Skills' defined in the Campaign Template."
              },
              "difficulty_class": {
                "type": "integer",
                "description": "The Difficulty Class (DC) for the skill check. A higher number indicates a harder check."
              }
            },
            "required": ["skill", "difficulty_class"],
            "nullable": true
          }
        },
        "required": ["from_location_id", "to_location_id", "description"]
      },
      "uniqueItems": true
    }
  },
  "required": ["locations", "connections"]
}
