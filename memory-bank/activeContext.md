# Active Context: Admin Seed Data Management Screen (03 May 2025)

## Current Focus

**NEW TASK:** Create an admin screen (Flask view and template) to manage game seed data for testing purposes.

**Functionality:**
1.  **Export Seed Data:**
    *   Allow admin to input an existing `game_id`.
    *   Allow admin to specify a name/identifier for the seed file.
    *   Export relevant data from `games`, `campaigns`, `game_players`, and `game_states` tables associated with the input `game_id`.
    *   Save the exported data as a JSON file in a designated directory (e.g., `instance/seed_data/`).
2.  **Import Seed Data:**
    *   List available seed data JSON files from the designated directory.
    *   Allow admin to select a seed file.
    *   Create a *new* game instance (new `game_id`) by populating the `games`, `campaigns`, `game_players`, and initial `game_states` tables based on the data in the selected JSON file.

**PREVIOUS TASK PAUSED:** Implementation and testing of narrative guidance features (required plot points, AI hints, objective enforcement) is paused. See `narrative_guidance_plan.md` and previous context in `progress.md` (Phase 5).

## Key Files for Current Task (Admin Screen)

*   **New Files:**
    *   `questforge/views/admin.py` (New Blueprint/routes)
    *   `questforge/templates/admin/admin.html` (New template)
    *   `instance/seed_data/` (New directory for JSON files - needs .gitignore update)
    *   `memory-bank/admin_seed_data.md` (New documentation file)
*   **Existing Files to Modify:**
    *   `questforge/__init__.py` (Register blueprint)
    *   `questforge/templates/partials/_navbar.html` (Add link to admin screen)
    *   `.gitignore` (Add `instance/seed_data/`)
*   **Models Used:** `Game`, `Campaign`, `GamePlayer`, `GameState`, `User`, `Template` (for relationships)

## Next Steps (New Task)

1.  Create the basic structure: Blueprint, route for `/admin`, and `admin.html` template.
2.  Implement the Export functionality (form, route logic, DB query, JSON serialization, file saving).
3.  Implement the Import functionality (list files, form, route logic, file reading, JSON parsing, DB object creation, commit).
4.  Add navigation link.
5.  Update `.gitignore`.
6.  Document the feature.
