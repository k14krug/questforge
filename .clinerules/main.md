description: Enforce Gemini 2.5 Pro token budget
globs: ["*"]         # Applies to all tasks/files
alwaysApply: true    # Always active

rule:
  # If prompt size exceeds 180,000 tokens, warn and stop action
  if prompt_tokens > 180000 then
    reply: |
      ⚠️ Prompt context too large ({{prompt_tokens}} tokens).
      Gemini 2.5 Pro limit is 200,000 tokens.  
      Please update the memory bank or manually offload context before proceeding.
    stop
