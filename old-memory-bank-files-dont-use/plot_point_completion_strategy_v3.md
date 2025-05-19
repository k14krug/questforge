# Plot Point Completion Strategy v3

## 1. The Problem (The "Why")

The v2 strategy for determining plot point completion in QuestForge was a significant improvement over the original system, but real-world testing has revealed several issues:

*   **Narrative-Plot Point Disconnect:** In some cases, plot points defined during campaign generation aren't properly reflected in the game narrative. For example, a plot point about "rescuing Dr. Elias Trent trapped in the Engine Room" wasn't properly integrated - when the player reached the Engine Room, Dr. Trent was there but didn't need rescuing.

*   **Missed Completion Recognition:** The system sometimes fails to recognize when player actions should satisfy a plot point. For example, a plot point about "Players must split up to explore different locations for supplies and escape options" wasn't marked as completed when the player split up from Dr. Trent to find tools in the Cargo Hold.

*   **Plausibility Check Limitations:** The current heuristic for determining which plot points to check for completion (Stage 2) is too simplistic, relying on basic word matching that may miss semantically relevant plot points.

*   **Confidence Threshold Issues:** The confidence threshold for marking plot points as completed may be too high, causing valid completions to be missed.

*   **Insufficient State Context:** The game state might not contain enough information for accurate plot point evaluation, or the AI might not be properly considering all relevant state information.

**Goal of this Revision:** To enhance the v2 strategy to address these specific issues, improving the reliability and accuracy of plot point completion detection while maintaining the core multi-stage approach.

## 2. The Solution (The "How"): Enhanced Multi-Stage AI Processing

This strategy builds upon the v2 approach, maintaining the four-stage process but enhancing each stage to address the identified issues.

### Core Principle 1: Improved Atomic Plot Point Design

The concept of atomic plot points remains central, but we need to provide clearer guidance to the AI during campaign generation to ensure plot points are truly atomic and properly integrated into the narrative.

*   **Enhanced Campaign Generation Prompt:**
    *   Provide more explicit examples of good atomic plot points
    *   Emphasize the importance of integrating plot points into the narrative
    *   Add validation checks to ensure plot points are atomic and clearly defined
    *   Analyze frequently problematic plot point patterns from AI generation and use this to refine `build_campaign_prompt`.

### Core Principle 2: Semantic-Aware Evaluation

Move beyond simple word matching to consider semantic meaning and context when evaluating plot point completion.

### The Enhanced Multi-Stage Process per Turn:

**Stage 1: Narrative Generation & Enriched State Update (Main AI Call)**
*   **Enhancements:**
    *   Update `build_response_prompt` to encourage more detailed state updates
    *   Add specific instructions for tracking NPC locations, relationships, and status
    *   Ensure location changes, inventory updates, and NPC interactions are properly recorded
    *   Emphasize the importance of maintaining narrative consistency with defined plot points

**Stage 2: Improved System-Side "Plausibility Check"**
*   **Enhancements:**
    *   Implement a more sophisticated matching algorithm that considers semantic similarity (e.g., exploring TF-IDF, keyword expansion with synonyms, or lightweight semantic similarity approaches)
    *   Add location-based relevance (check plot points related to the current location)
    *   Include plot points that mention NPCs currently present
    *   Lower the threshold for what's considered "plausible" to catch more potential completions
    *   Consider checking all pending plot points for critical game moments

**Stage 3: Enhanced Focused AI Completion Analysis**
*   **Enhancements:**
    *   Update `build_plot_completion_check_prompt` to provide clearer criteria for completion
    *   Add examples of what constitutes completion for different types of plot points
    *   Emphasize the importance of considering the full game state
    *   Consider using a more capable AI model for this analytical task
    *   Success heavily relies on the richness and accuracy of `current_game_state_data` provided by Stage 1.

**Stage 4: Refined System Aggregation & Final State Update**
*   **Enhancements:**
    *   Adjust the confidence threshold (`PLOT_COMPLETION_CONFIDENCE_THRESHOLD`) to an appropriate level
    *   Consider implementing dynamic thresholds based on plot point type or importance (e.g., 'required' plot points might have a stricter or more lenient profile depending on desired game flow; plot points with very specific, easily verifiable conditions might have a higher default confidence expectation).
    *   Add more detailed logging of plot point evaluation decisions
    *   Implement a mechanism to review "near-miss" completions (high but not quite threshold-meeting confidence scores)

## 3. Benefits of this Enhanced Strategy

*   **Improved Narrative Integration:** Better alignment between plot points and the game narrative.
*   **More Accurate Completion Detection:** Reduced false negatives in plot point completion.
*   **Semantic Understanding:** Moving beyond simple word matching to understand the meaning of player actions.
*   **Flexible Confidence Thresholds:** Appropriate thresholds for different types of plot points.
*   **Richer State Context:** More detailed state information for more accurate evaluation.
*   **Better Debugging:** Enhanced logging to understand why plot points aren't being marked as completed.

## 4. Key Implementation Areas

### 4.1 Campaign Generation Enhancements

*   **`prompt_builder.py` (`build_campaign_prompt`):**
    *   Add more explicit examples of good atomic plot points
    *   Emphasize the importance of integrating plot points into the narrative
    *   Add instructions to ensure plot points are reflected in location descriptions

*   **`ai_service.py` (`generate_campaign`):**
    *   Add validation to ensure plot points are atomic and clearly defined
    *   Consider post-processing to break down complex plot points
    *   Analyze frequently problematic plot point patterns from AI generation and use this to refine `build_campaign_prompt`.

### 4.2 Stage 1: Narrative & State Update Enhancements

*   **`prompt_builder.py` (`build_response_prompt`):**
    *   Update to encourage more detailed state updates
    *   Add specific instructions for tracking NPC locations, relationships, and status
    *   Emphasize the importance of maintaining narrative consistency with defined plot points

*   **`ai_service.py` (`get_response`):**
    *   Enhance validation of state updates to ensure critical information is present
    *   Implement fallback mechanisms when state data is incomplete

### 4.3 Stage 2: Plausibility Check Enhancements

*   **`socket_service.py` (`handle_player_action`):**
    *   Implement a more sophisticated matching algorithm (e.g., exploring TF-IDF, keyword expansion with synonyms, or lightweight semantic similarity approaches)
    *   Add location-based relevance checks
    *   Include NPC-based relevance checks
    *   Lower the threshold for what's considered "plausible"
    *   Add special handling for critical game moments

### 4.4 Stage 3: Focused AI Completion Analysis Enhancements

*   **`prompt_builder.py` (`build_plot_completion_check_prompt`):**
    *   Provide clearer criteria for completion
    *   Add examples of what constitutes completion for different types of plot points
    *   Emphasize the importance of considering the full game state

*   **`ai_service.py` (`check_atomic_plot_completion`):**
    *   Consider using a more capable AI model for this analytical task
    *   Enhance error handling and validation

### 4.5 Stage 4: System Aggregation & Update Enhancements

*   **`socket_service.py` (`handle_player_action`):**
    *   Adjust the confidence threshold
    *   Consider implementing dynamic thresholds (e.g., 'required' plot points might have a stricter or more lenient profile depending on desired game flow; plot points with very specific, easily verifiable conditions might have a higher default confidence expectation)
    *   Add more detailed logging of plot point evaluation decisions
    *   Implement a mechanism to review "near-miss" completions

### 4.6 Debugging & Monitoring

*   **Logging Enhancements:**
    *   Add detailed logging of plot point evaluation decisions
    *   Log "near-miss" completions for review
    *   Track which plot points are frequently checked but never completed

*   **Developer Tools:**
    *   Consider adding a debug mode to see why plot points weren't marked as completed
    *   Implement a way to manually mark plot points as completed for testing
    *   Analyze frequently problematic plot point patterns from AI generation and use this to refine `build_campaign_prompt` (Covered in 4.1, but re-iterating importance for monitoring).

## 5. Implementation Plan

**Note:** All prompt-related changes will involve iterative testing and refinement based on AI performance.

### Phase 1: Quick Wins (Prompt Improvements & Threshold Adjustments)

1. **Update `build_plot_completion_check_prompt`:**
   - Provide clearer criteria for completion
   - Add examples of what constitutes completion for different types of plot points
   - Emphasize the importance of considering the full game state

2. **Update `build_response_prompt`:**
   - Encourage more detailed state updates
   - Add specific instructions for tracking NPC locations, relationships, and status

3. **Adjust Confidence Threshold:**
   - Lower the `PLOT_COMPLETION_CONFIDENCE_THRESHOLD` in `socket_service.py`
   - Test with different values to find the optimal balance

### Phase 2: Plausibility Check & State Management Enhancements

1. **Enhance Plausibility Check:**
   - Implement a more sophisticated matching algorithm
   - Add location-based and NPC-based relevance checks
   - Add special handling for critical game moments

2. **Improve State Management:**
   - Enhance validation of state updates
   - Implement fallback mechanisms for incomplete state data

### Phase 3: Campaign Generation & Advanced Semantic Matching

1. **Update `build_campaign_prompt`:**
   - Add more explicit examples of good atomic plot points
   - Emphasize the importance of integrating plot points into the narrative

2. **Enhance `generate_campaign`:**
   - Add validation to ensure plot points are atomic and clearly defined
   - Consider post-processing to break down complex plot points

3. **Implement Advanced Semantic Matching:**
   - Consider using embeddings or more sophisticated NLP techniques if simpler approaches aren't sufficient

### Phase 4: Debugging & Monitoring Enhancements

1. **Add Detailed Logging:**
   - Log plot point evaluation decisions
   - Track "near-miss" completions
   - Monitor frequently checked but never completed plot points

2. **Implement Developer Tools:**
   - Add a debug mode for plot point completion
   - Create a way to manually mark plot points as completed for testing

## 6. Testing Strategy

1. **Unit Tests:**
   - Test each component of the enhanced system in isolation
   - Verify that the plausibility check correctly identifies relevant plot points
   - Ensure the confidence threshold logic works as expected

2. **Integration Tests:**
   - Test the full multi-stage process with various scenarios
   - Verify that plot points are correctly marked as completed

3. **Regression Tests:**
   - Ensure that the enhancements don't break existing functionality
   - Verify that previously working plot points still work

4. **User Testing:**
   - Have users play through scenarios with known plot points
   - Gather feedback on whether plot points are being correctly integrated and completed
