# Error Handling Guidelines

This document establishes comprehensive guidelines for error handling within the QuestForge application, covering how various errors (e.g., AI API failures, invalid input, network issues) should be handled, logged, and communicated to users. The goal is to ensure a robust, user-friendly, and maintainable system.

## 1. General Principles

*   **Consistency:** All error responses (API, Socket.IO, UI) must follow a consistent structure and tone.
*   **User-Friendliness:** Error messages displayed to users should be clear, concise, actionable, and avoid technical jargon.
*   **Security:** Avoid exposing sensitive system information (e.g., full stack traces, internal server details, API keys) in public error messages.
*   **Logging:** Implement comprehensive logging for all errors to facilitate debugging, monitoring, and post-mortem analysis.
*   **Graceful Degradation:** The application should remain functional, even if partially, when non-critical components or external services experience issues.

## 2. Error Categories

Errors are broadly categorized by their origin and impact.

### 2.1 Client-Side Errors (HTTP 4xx Status Codes)

These errors typically result from invalid client requests or authentication issues.

*   **400 Bad Request:**
    *   **Cause:** Invalid input data (e.g., missing required fields, incorrect data types, malformed JSON), failed validation checks.
    *   **Backend Handling:** Return a JSON response with a clear error message and, if applicable, details about specific validation failures (e.g., which field is invalid).
    *   **Frontend Communication:** Display specific validation errors next to form fields or a general error message if the issue is broader.
*   **401 Unauthorized:**
    *   **Cause:** Missing or invalid authentication credentials (e.g., no token, expired token, invalid token).
    *   **Backend Handling:** Return a JSON response indicating authentication is required.
    *   **Frontend Communication:** Redirect user to login page or prompt for re-authentication.
*   **403 Forbidden:**
    *   **Cause:** Authenticated user does not have permission to perform the requested action or access the resource.
    *   **Backend Handling:** Return a JSON response indicating access is denied.
    *   **Frontend Communication:** Display a "permission denied" message.
*   **404 Not Found:**
    *   **Cause:** The requested resource (e.g., game ID, template ID) does not exist.
    *   **Backend Handling:** Return a JSON response indicating the resource was not found.
    *   **Frontend Communication:** Display a "resource not found" message or redirect to a relevant page (e.g., dashboard).
*   **409 Conflict:**
    *   **Cause:** Request conflicts with the current state of the resource (e.g., username already taken, game is full, attempting to join an already started game).
    *   **Backend Handling:** Return a JSON response explaining the conflict.
    *   **Frontend Communication:** Inform the user about the specific conflict (e.g., "Username already exists," "Game is full").

### 2.2 Server-Side Errors (HTTP 5xx Status Codes)

These errors indicate a problem on the server's end, preventing it from fulfilling a valid request.

*   **500 Internal Server Error:**
    *   **Cause:** Generic server-side error, unhandled exceptions, unexpected issues in application logic, database connection failures, or other internal system failures.
    *   **Backend Handling:** Log the full stack trace and relevant context. Return a generic, non-descriptive error message to the client (e.g., "An unexpected error occurred. Please try again later.").
    *   **Frontend Communication:** Display a generic "something went wrong" message. For critical failures, a dedicated error page might be shown.
*   **AI API Failures (e.g., 502 Bad Gateway, 503 Service Unavailable, 429 Too Many Requests from AI provider):**
    *   **Cause:** Issues with external AI service (e.g., downtime, rate limiting, invalid API key, malformed AI response).
    *   **Backend Handling:**
        *   **Retries:** Implement exponential backoff and retry mechanisms for transient AI API errors (e.g., 429, 503).
        *   **Fallback:** If retries fail, consider fallback strategies (e.g., using a lower-tier AI model if configured, or providing a default/placeholder response if acceptable).
        *   **Logging:** Log the specific AI API error code, message, and any relevant request/response details.
        *   **Cost Tracking:** Ensure AI call costs are not incorrectly accumulated for failed calls.
    *   **Frontend Communication:** Inform the user that AI services are temporarily unavailable or experiencing issues. For critical AI failures (e.g., during charter generation), prevent game start. For in-game narrative failures, display a message like "The Game Master is thinking..." or "The narrative is paused due to a cosmic disturbance."
*   **Database Errors:**
    *   **Cause:** Connection issues, query failures, data integrity violations not caught by application-level validation.
    *   **Backend Handling:** Catch database-specific exceptions. Log detailed error messages including query, parameters, and stack trace. Translate into generic 500 errors for the client.
    *   **Frontend Communication:** Treat as a generic server error.
*   **Network Issues (Backend to External Services):**
    *   **Cause:** Connectivity problems when the backend tries to reach external services (e.g., AI APIs, image hosting, other microservices).
    *   **Backend Handling:** Implement timeouts and retry logic. Log network errors.
    *   **Frontend Communication:** Similar to AI API failures, inform the user about temporary service unavailability.

## 3. Error Handling Workflow

### 3.1 Backend Workflow

1.  **Input Validation:**
    *   Perform strict validation on all incoming API requests and Socket.IO event payloads.
    *   Use appropriate libraries/framework features for validation (e.g., Flask-WTF, Pydantic).
    *   Return 400 Bad Request with specific error details for validation failures.
2.  **Exception Handling:**
    *   Wrap critical operations (database interactions, external API calls, complex logic) in `try-except` blocks.
    *   Catch specific exceptions where possible (e.g., `requests.exceptions.ConnectionError`, `sqlalchemy.exc.IntegrityError`).
    *   For unhandled exceptions, a global error handler should catch them and return a generic 500 error to the client while logging the full details.
3.  **Logging:**
    *   Log all errors with sufficient detail (see Section 4).
    *   Use unique request IDs to trace requests across logs.
4.  **Standardized Responses:**
    *   All API error responses should be JSON objects with at least an `error` field and optionally a `details` field.
    *   Example: `{"error": "Invalid credentials", "details": "Password too short"}`
5.  **Retries and Fallbacks:**
    *   For transient errors (e.g., network timeouts, rate limits from external APIs), implement retry logic with exponential backoff.
    *   For non-critical failures, consider graceful degradation or fallback mechanisms (e.g., if image generation fails, use a placeholder image).

### 3.2 Frontend Workflow

1.  **API Error Processing:**
    *   Listen for HTTP error codes (4xx, 5xx) from API responses.
    *   Parse the standardized JSON error responses.
2.  **Socket.IO Error Processing:**
    *   Listen for the `error_message` Socket.IO event.
    *   Parse the `code`, `message`, and `details` fields.
3.  **User Feedback:**
    *   **In-App Notifications:** Use toast notifications or temporary banners for non-blocking errors (e.g., "Failed to save settings").
    *   **Form Validation:** Display inline error messages for invalid form inputs.
    *   **Blocking Modals:** For critical errors that prevent further interaction (e.g., "Game session disconnected").
    *   **Game Log:** For game-specific system errors (e.g., "SYSTEM: AI GM is unresponsive. Please try again.").
    *   **Dedicated Error Pages:** For unrecoverable application-wide errors (e.g., 500 errors, network issues preventing app load).
4.  **Graceful Degradation:**
    *   If an AI image fails to load, display a default image.
    *   If real-time updates are interrupted, display a "reconnecting..." message.
5.  **User Actions:**
    *   Provide clear calls to action where appropriate (e.g., "Retry," "Go to Dashboard," "Contact Support").

## 4. Logging Strategy

Effective logging is crucial for identifying, diagnosing, and resolving issues.

*   **Logging Levels:**
    *   `DEBUG`: Detailed information, typically only of interest when diagnosing problems.
    *   `INFO`: Confirmation that things are working as expected.
    *   `WARNING`: An indication that something unexpected happened, or indicative of some problem in the near future (e.g., 'disk space low'). The software is still working as expected.
    *   `ERROR`: Due to a more serious problem, the software has not been able to perform some function.
    *   `CRITICAL`: A serious error, indicating that the program itself may be unable to continue running.
*   **Log Content:** Each log entry should include:
    *   `timestamp` (ISO 8601 format)
    *   `level` (e.g., ERROR, INFO)
    *   `service/module` (e.g., `auth_service`, `ai_service`, `database_manager`)
    *   `message` (human-readable description of the event)
    *   `request_id` (UUID, for tracing a single request across multiple log entries)
    *   `user_id` (UUID, if applicable)
    *   `game_id` (UUID, if applicable)
    *   `error_type` (e.g., `ValueError`, `ConnectionError`, `AI_RATE_LIMIT_EXCEEDED`)
    *   `stack_trace` (for ERROR and CRITICAL levels)
    *   `details` (JSON object for additional context, e.g., input parameters that caused validation error, AI API response body)
*   **Log Location:**
    *   Initially, logs can be written to files (e.g., `logs/app.log`, `logs/error.log`).
    *   For production, integrate with a centralized logging system (e.g., ELK stack, Splunk, cloud logging services like AWS CloudWatch, Google Cloud Logging) for easier aggregation, searching, and analysis.
*   **Monitoring & Alerting:**
    *   Set up alerts for `ERROR` and `CRITICAL` level logs.
    *   Monitor key error metrics (e.g., error rate per endpoint, AI API error counts).

## 5. Communication to Users

Clear and timely communication about errors is essential for a good user experience.

*   **In-App Notifications:**
    *   Use non-intrusive notifications (e.g., toast messages) for minor, recoverable errors (e.g., "Failed to update profile. Please try again.").
    *   For more significant but non-blocking issues, use banners at the top of the screen.
*   **Game Log (Play Screen):**
    *   For errors directly impacting gameplay (e.g., AI API issues during a turn, dice roller malfunction), a `SYSTEM_MESSAGE` entry should be added to the `game_log`.
    *   Example: `{"type": "SYSTEM_MESSAGE", "timestamp": "...", "event": "AI_ERROR", "message": "The Game Master is experiencing a narrative block. Please wait a moment or try a different action."}`
*   **Dedicated Error Pages:**
    *   For unrecoverable application-wide errors (e.g., 500 errors that prevent the app from loading), display a simple, branded error page with a generic message and a link to the homepage or support.
*   **Support Channels:**
    *   Provide clear instructions on how users can report issues, including what information to provide (e.g., "If this persists, please contact support with the error timestamp and your username.").
