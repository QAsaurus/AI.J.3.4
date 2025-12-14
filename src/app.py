import os
from dotenv import load_dotenv
import requests
from flask import Flask, render_template, request

# Load environment variables from .env file in the project root.
# The .env file is expected to contain: MENTORPIECE_API_KEY=<your_key>
# load_dotenv searches for .env in the current directory and up the tree.
# This will be called automatically when the app module is imported.
load_dotenv()

# Endpoint and basic configuration for MentorPiece API
MENTORPIECE_ENDPOINT = "https://api.mentorpiece.org/v1/process-ai-request"

# Create Flask app. The templates directory is expected at src/templates
app = Flask(__name__, template_folder="templates")


def call_llm(model_name, messages, mode='mock'):
    """
    Call the MentorPiece LLM endpoint.

    Args:
        model_name (str): The model identifier to use for the request.
        messages (list[str]): A list of message strings that will be concatenated
                              into a single prompt for the API.

    Returns:
        str: The text response returned by the API, or an error message.

    Notes for QA beginners:
        - We join `messages` into one `prompt` because the MentorPiece
          endpoint expects a single `prompt` string in the request body.
        - We send an Authorization header `Bearer <KEY>` using the
          `MENTORPIECE_API_KEY` environment variable.
        - We handle network and HTTP errors and return readable messages
          so the web UI can display helpful feedback.
    """

    # Modes supported:
    # - 'mock'       : return canned responses without calling external API
    # - 'no_auth'    : call the API endpoint without Authorization header
    # - 'auth'       : call the API endpoint with Authorization: Bearer <KEY>
    # Default mode is 'mock' for safe local testing and QA.
    mode = (mode or 'mock').lower()

    # If mock mode is enabled, return canned responses useful for QA and tests.
    if mode == 'mock':
        # Provide deterministic, simple responses depending on the model.
        if model_name.lower().startswith('qwen'):
            return 'Mocked Translation: The sun is shining.'
        if model_name.lower().startswith('claude'):
            return 'Mocked Grade: 9/10. Fluent and accurate.'
        return 'Mocked response for model: ' + model_name

    # For non-mock modes, read API key at call time so tests can control env.
    api_key = os.getenv("MENTORPIECE_API_KEY")
    if mode == 'auth' and not api_key:
        return "Error: MENTORPIECE_API_KEY is not set in environment"

    # Build the prompt by joining messages with blank lines for readability
    prompt = "\n\n".join(messages)

    payload = {
        "model_name": model_name,
        "prompt": prompt,
    }

    # Build headers depending on mode
    headers = {"Content-Type": "application/json"}
    if mode == 'auth':
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        # Use a reasonable timeout to avoid hanging requests during QA
        resp = requests.post(MENTORPIECE_ENDPOINT, json=payload, headers=headers, timeout=15)

        # Raise an exception for 4xx/5xx responses so we can handle them in except
        resp.raise_for_status()

        # The MentorPiece API returns JSON of the form: {"response": "..."}
        data = resp.json()

        # Safely get the `response` field
        return data.get("response", "")

    except requests.exceptions.RequestException as e:
        # Network error, timeout, or HTTP error
        return f"Network/HTTP error when calling LLM: {str(e)}"
    except ValueError:
        # JSON decoding error
        return "Invalid JSON response from MentorPiece API"


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main route for the application.

    GET: Render the form to accept text and language.
    POST: Perform translation using the translation model, then ask the judge model
          to evaluate the translation quality.
    """

    original_text = ""
    translated_text = ""
    evaluation = ""

    if request.method == 'POST':
        # Get form values
        original_text = request.form.get('source_text', '').strip()
        target_lang_ru = request.form.get('target_lang', 'Английский')
        # Mode of operation: 'mock', 'no_auth', 'auth'
        mode = request.form.get('mode', 'mock')

        # Map Russian language names to English for API prompts
        lang_map = {
            'Английский': 'English',
            'Французский': 'French',
            'Немецкий': 'German',
            'Португальский': 'Portuguese (Portugal)',
        }
        target_lang = lang_map.get(target_lang_ru, 'English')

        # Defensive: if user submitted empty text, show helpful message
        if not original_text:
            evaluation = "Please provide text to translate."
            return render_template('index.html', original=original_text, translated=translated_text, evaluation=evaluation)

        # Step 1: Translate using the specified translation model
        translation_prompt = (
            f"Translate the following text into {target_lang}. "
            "Preserve meaning, tone, and formatting as much as possible. "
            "Only return the translated text and do not include extra commentary.\n\n"
            f"Original text:\n{original_text}"
        )

        # call_llm expects a list of messages; we provide a single prompt element
        translated_text = call_llm("Qwen/Qwen3-VL-30B-A3B-Instruct", [translation_prompt], mode=mode)

        # If translation failed due to network/API key issues, translated_text will contain an error
        if translated_text.startswith("Error:") or translated_text.startswith("Network/"):
            # Show error in evaluation area to be visible to QA
            evaluation = translated_text
            translated_text = ""
            return render_template('index.html', original=original_text, translated=translated_text, evaluation=evaluation)

        # Step 2: Ask judge model to evaluate the translation quality
        judge_prompt = (
            "Оцени качество перевода от 1 до 10 и аргументируй. "
            "Дай краткую разметку: оценка и затем аргументы.\n\n"
            f"Исходный текст:\n{original_text}\n\nПеревод:\n{translated_text}"
        )

        evaluation = call_llm("claude-sonnet-4-5-20250929", [judge_prompt], mode=mode)

    # Render the template with whatever values we have (empty strings by default)
    return render_template('index.html', original=original_text, translated=translated_text, evaluation=evaluation)


if __name__ == '__main__':
    # Run the Flask dev server. In production, use a WSGI server like Gunicorn.
    app.run(host='0.0.0.0', port=5000, debug=True)
