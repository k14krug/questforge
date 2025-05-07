**Task: Implement ID-Based Plot Point System Upgrade**

**Objective:**
Refactor the QuestForge application to use a robust ID-based system for tracking Major Plot Point completion. This upgrade aims to improve the reliability of plot progression and campaign conclusion logic.

**Context & Plan:**
The primary guide for this task is the consolidated plan document: `memory-bank/id_based_plot_point_upgrade_plan.md`.
This document details:
1.  The current system's limitations with description-based plot point tracking.
2.  The objective to upgrade to an ID-based system.
3.  A phased action plan for implementing this upgrade, covering changes to AI prompts, campaign generation, game state management, action handling, and conclusion checking.
4.  A verification strategy for each phase.

**Key Requirements:**
1.  Modify campaign generation to assign unique IDs to each Major Plot Point.
2.  Update AI prompts to request and process plot point IDs (instead of descriptions) for tracking completion.
3.  Adjust game state logic to store and check completed plot points using these IDs.
4.  Ensure the `check_conclusion` function in `campaign_service.py` correctly verifies all `required: true` plot points (by ID) AND all other `conclusion_conditions` are met.
5.  Verify that the AI is still correctly prompted to set boolean state flags (e.g., `bomb_disabled: true`) for `conclusion_conditions` when narratively appropriate.
6.  Follow the phased implementation and verification strategy outlined in `memory-bank/id_based_plot_point_upgrade_plan.md`.

**Important Note:** This task assumes the codebase has been reverted to its state *before* any recent attempts to fix campaign conclusion issues. All changes described in the `id_based_plot_point_upgrade_plan.md` need to be implemented as part of this task.
