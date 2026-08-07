"""
llm.py — sends messages to an AI language model via the OpenRouter API
and manages Expert Routing & Orchestrator for Homework 1.
"""

import os
import re
import requests
from jinja2 import Template

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

# ------------------------------------------------------------------
# MASTER TEMPLATE & FILL TEMPLATE (Step 1 Requirement)
# ------------------------------------------------------------------

MASTER_TEMPLATE = Template("""\
You are a {{ role }}, an expert in {{ domain }}.

{{ specific_instructions }}
{% if background_context %}
Context:
{{ background_context }}
{% endif %}
{% if few_shot_examples %}
Examples:
{{ few_shot_examples }}
{% endif %}
Request: {{ request }}
""", trim_blocks=True, lstrip_blocks=True)


def fill_template(role, domain, specific_instructions, request,
                  background_context="", few_shot_examples=""):
    """Render MASTER_TEMPLATE into one expert's full system prompt."""
    return MASTER_TEMPLATE.render(
        role=role,
        domain=domain,
        specific_instructions=specific_instructions,
        background_context=background_context,
        few_shot_examples=few_shot_examples,
        request=request,
    ).strip()


def send_message(user_message, system_prompt="You are a helpful assistant."):
    """Send a message to OpenRouter API."""
    api_key = os.getenv('OPENROUTER_API_KEY')

    if not api_key or api_key == 'paste-your-key-here':
        return "⚠️ No API key found. Add your OpenRouter key to the .env file and restart the app."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8080"
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json={"model": DEFAULT_MODEL, "messages": messages},
            timeout=30
        )
        result = response.json()

        if 'error' in result:
            return f"⚠️ OpenRouter error: {result['error'].get('message', 'Unknown error')}"

        if 'choices' not in result:
            return f"⚠️ Unexpected response: {result}"

        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Exception occurred: {str(e)}"


# ------------------------------------------------------------------
# MAIN ROUTER & EXPERT EXECUTION (Step 4 Requirement)
# ------------------------------------------------------------------

def handle_ai_chat_request(db, role, message):
    """
    Route a chat message to the named expert dynamically using the llm_roles table.
    """
    if role is None:
        return send_message(message)

    config = db.getLLMRoles()[role]
    background_context = config['background_context'] or ""
    if role == "Content Expert":
        background_context += "\n" + db.getResumeText()

    system_prompt = fill_template(
        role=config['role'],
        domain=config['domain'],
        specific_instructions=config['specific_instructions'],
        background_context=background_context,
        few_shot_examples=config['few_shot_examples'] or "",
        request=message,
    )
    
    output = send_message(message, system_prompt).strip()
    print(f"\n[{role}] generated:\n{output}\n")

    if role == "Database Read Expert":
        return execute_read_query(db, output)
    if role == "Database Write Expert":
        return execute_write_action(db, output)
    if role == "Orchestrator":
        return run_orchestrator_plan(db, message, output)
    
    return output  # Content Expert


def execute_read_query(db, sql):
    """Run the Database Read Expert's generated SQL."""
    cleaned_sql = re.sub(r'```sql|```', '', sql).strip()
    if not cleaned_sql.upper().startswith("SELECT"):
        return "Sorry, I couldn't safely answer that question."
    try:
        return str(db.query(cleaned_sql))
    except Exception as error:
        print(f"Read Expert query failed: {error}")
        return "Sorry, that question couldn't be answered."


def execute_write_action(db, generated_code):
    """Run the Database Write Expert's generated Python."""
    cleaned_code = re.sub(r'```python|```', '', generated_code).strip()
    local_vars = {}
    try:
        exec(cleaned_code, {"db": db, "NULL": None}, local_vars)
    except Exception as error:
        print(f"Write Expert code failed: {error}")
        return "Operation was unsuccessful."
    return local_vars.get("outcome", "Operation was unsuccessful.")


def run_orchestrator_plan(db, original_request, plan_text):
    """
    Parse the Orchestrator's plan, execute calls in sequence,
    and generate a single clean response.
    """
    cleaned_plan = re.sub(r'```python|```', '', plan_text).strip()
    try:
        call_strings = eval(cleaned_plan)
    except Exception:
        print(f"Orchestrator returned an unparseable plan: {plan_text}")
        return "Sorry, I couldn't plan a response to that."

    results = []
    for call_string in call_strings:
        print(f"[Orchestrator] executing: {call_string}")
        match = re.search(r'role="([^"]*)",\s*message="([^"]*)"', call_string)
        if match:
            role, message = match.group(1), match.group(2)
            response = handle_ai_chat_request(db, role, message)
            results.append((role, message, response))

    steps_summary = "\n".join(f"{r}: {resp}" for r, m, resp in results)
    synthesis_prompt = (
        f'The user asked: "{original_request}"\n\n'
        f"Here is what each expert found or did:\n{steps_summary}\n\n"
        "Write ONE short, clear reply. A Database Write Expert step's result "
        "is already the exact message to show the user (e.g. 'New Python "
        "added to the skills table.') -- if one is present, reuse it "
        "verbatim rather than rephrasing it. Otherwise, summarize the "
        "other results in plain language. Never mention SQL, Python, code, "
        "or these internal steps."
    )
    return send_message(original_request, synthesis_prompt)