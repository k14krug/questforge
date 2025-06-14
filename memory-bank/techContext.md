# Tech Context

## Technologies Used:
- **Backend:** Python (e.g., Flask)
- **Real-time Communication:** Socket.IO
- **AI Language Models:**
    - Primary Models: State-of-the-art models (e.g., GPT-4o)
    - Secondary Models: Faster, lower-cost models (e.g., GPT-3.5 Turbo)
- **Password Hashing:** bcrypt
- **Data Storage:** (Implied by models and JSON fields, specific database not mentioned but likely relational or document-based for JSON fields)
- **Frontend:** Native web technologies (HTML, CSS, Vanilla JavaScript). Modern frameworks like React, Vue, or Angular are explicitly excluded.

## Development Setup:
- **AI Model Configuration:** A `config.json` file serves as the single source of truth for available AI models, their tier, API identifiers, and token costs. This file is developer-maintained.

## Technical Constraints & Dependencies:
- Reliance on external AI model APIs.
- Real-time communication requires Socket.IO server and client setup.
- Secure password management necessitates bcrypt library.

## Tool Usage Patterns:
- **AI Service Layer (`AIService`):** Manages all interactions with external AI models.
- **`GameStateService`:** Responsible for executing game mechanics, including dice rolls and skill checks, and interacting with the AI for outcome narration.
- **Socket.IO:** Used for broadcasting real-time updates to clients (e.g., skill check requests, dice roll simulations, results).
