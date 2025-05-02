# Troubleshooting Guide

This document provides guidance for troubleshooting issues encountered during QuestForge development. Refer to the Memory Bank for overall project context and detailed specifications.

## Relevant Memory Bank Documents

*   **Active Context:** [../memory-bank/activeContext.md](../memory-bank/activeContext.md) - Current project focus and recent changes.
*   **Progress Tracker:** [../memory-bank/progress.md](../memory-bank/progress.md) - Overall project progress and completed phases.
*   **Project Intelligence:** [./clinerules.md](./clinerules.md) - General project patterns and conventions.
*   **Phase 5 Details:** [../memory-bank/phase-5-enhanced-game-creation.md](../memory-bank/phase-5-enhanced-game-creation.md) - Detailed tasks and goals for Phase 5 (Enhanced Game Creation).

## Key Files Modified in Recent Work (Enhanced Game Creation)

*   `questforge/models/template.py`: Removed `questions` field.
*   `migrations/versions/`: Reverted migration that added `questions` field.
*   `questforge/views/forms.py`: Removed `questions` field and validator from `TemplateForm`.
*   `questforge/views/template.py`: Removed `questions` handling from `create_template` and `edit_template`, removed `/api/templates/<id>/questions` endpoint, added `/api/templates/<int:template_id>/details` endpoint.
*   `questforge/templates/game/create.html`: Modified JavaScript to fetch template details and display editable override fields.
*   `questforge/views/game.py`: Modified `/api/games/create-game` to accept `template_overrides` and pass them to AI service.
*   `questforge/services/ai_service.py`: Modified `generate_campaign` to accept `template_overrides` and imported `Any`.
*   `questforge/utils/prompt_builder.py`: Modified `build_campaign_prompt` to accept and prioritize `template_overrides`.

## Troubleshooting Areas (Enhanced Game Creation)

### Application Startup Errors

*   **Problem:** Application fails to start after recent changes (e.g., `NameError`).
    *   **Check:**
        *   Review the traceback carefully. Identify the file and line number causing the error.
        *   Common errors like `NameError` often indicate missing imports. Ensure all necessary modules (e.g., `Any` from `typing`) are imported in the relevant files (`ai_service.py`, `prompt_builder.py`).

### Template Details Not Loading on Game Creation

*   **Problem:** When selecting a template on the game creation page, the template details override section does not appear or populate.
    *   **Check:**
        *   **Browser Console:** Look for JavaScript errors in `questforge/templates/game/create.html`.
        *   **Network Tab:** In browser developer tools, check if the `GET /api/templates/<template_id>/details` request is being sent when a template is selected. Verify the request URL is correct and the response status is 200.
        *   **Backend Logs:** Check `logs/questforge.log` for errors in the `get_template_details` function in `questforge/views/template.py`. Ensure the function is correctly querying the database and returning template data.
        *   **Database:** Verify that the selected template exists in the `templates` table and has data in the relevant fields (genre, core_conflict, etc.).

### Template Overrides Not Affecting Campaign Generation

*   **Problem:** Modifying template details on the game creation page does not seem to influence the generated campaign.
    *   **Check:**
        *   **Browser Console/Network Tab:** When submitting the game creation form, check the payload of the `POST /api/games/create-game` request. Verify that the `template_overrides` object is included in the request body and contains the expected modified values.
        *   **Backend Logs:** In `questforge/views/game.py`, check the `create_game_old` function. Log the incoming `data` dictionary to confirm `template_overrides` is received correctly.
        *   **Backend Logs:** In `questforge/services/ai_service.py`, check the `generate_campaign` function. Log the `template_overrides` argument to ensure it's being passed correctly from the view.
        *   **Backend Logs:** In `questforge/utils/prompt_builder.py`, check the `build_campaign_prompt` function. Log the `template_overrides` argument and the final generated `prompt` string to confirm that the overrides are being incorporated into the prompt sent to the AI.
        *   **AI Response:** If possible, log the raw AI response in `ai_service.py` to see if the AI's output reflects the template overrides.

### Database Migration Issues

*   **Problem:** Errors related to the `questions` column still appear after attempting to downgrade the migration.
    *   **Check:**
        *   **Terminal Output:** Rerun `flask db downgrade <migration_id>` and carefully review the output for any errors during the downgrade process.
        *   **Database Schema:** Connect to the database and verify that the `questions` column has been successfully removed from the `templates` table.
        *   **Alembic History:** Check the `alembic_version` table in the database and the `migrations/versions/` directory to ensure the downgrade was recorded correctly.

## General Troubleshooting Steps

1.  **Check Browser Console:** Always start by looking for JavaScript errors on the frontend.
2.  **Check Backend Logs:** Examine `logs/questforge.log` for Python errors, warnings, or debug messages. Increase logging level if necessary.
3.  **Use Browser Developer Tools:** Inspect network requests and responses to understand data flow between frontend and backend.
4.  **Inspect Database:** Verify data integrity and schema using a database client.
5.  **Refer to Memory Bank:** Consult relevant Memory Bank documents for context and specifications.
6.  **Review Recent Code Changes:** Carefully examine the code modified in the relevant files listed above.
