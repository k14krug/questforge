import os
import json
from flask import current_app

DEBUG_PAYLOAD_DIR = "ai_debug_payloads"

def log_ai_debug_payload(purpose: str, payload: dict, label: str, index: int) -> None:
    """
    Logs the AI API call payload to a human-readable JSON file for debugging purposes.

    Args:
        purpose (str): Static, human-readable description of the API call's intent.
        payload (dict): The exact dictionary payload sent to the AI API.
        label (str): Short identifier for the call type (e.g., 'plotpoint', 'narrative', 'campaign').
        index (int): Index to distinguish multiple calls of the same type in one turn.

    Behavior:
        - Only writes the file if the Flask app logger level is DEBUG.
        - Creates the ai_debug_payloads directory if it does not exist.
        - Writes a file named ai_payload_{label}_{index}.json, overwriting if it exists.
        - File content starts with a purpose statement, followed by pretty-printed JSON payload.
    """
    try:
        app = current_app._get_current_object()
        if not app.logger.isEnabledFor(10):  # 10 == logging.DEBUG
            print("DEBUG logging is not enabled. Skipping payload logging.")
            return

        print("DEBUG logging is enabled. Proceeding with payload logging.")
        if not os.path.exists(DEBUG_PAYLOAD_DIR):
            os.makedirs(DEBUG_PAYLOAD_DIR, exist_ok=True)

        filename = f"ai_payload_{label}_{index}.json"
        filepath = os.path.join(DEBUG_PAYLOAD_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Purpose: {purpose}\n\n")
            f.write("--- AI Prompt ---\n")
            if "messages" in payload and payload["messages"]:
                for msg in payload["messages"]:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    content = content.replace("\\n", "\n")
                    f.write(f"[{role}]:\n{content}\n\n")
            f.write("--- AI API JSON Payload ---\n")
            json.dump(payload, f, indent=4, sort_keys=True, ensure_ascii=False)

        app.logger.debug(f"AI debug payload written to {filepath}")

    except Exception as e:
        # Log error but do not raise to avoid interrupting main flow
        try:
            app.logger.warning(f"Failed to write AI debug payload file: {e}")
        except Exception:
            # If logger is not available, silently ignore
            pass
