"""Gradient M - Flask backend with Azure OpenAI + Azure Search
================================================================
This script powers the public chatbot that is embedded into `index.html` via
an iframe (see canvas doc *Gradientm Chatbot Integration Update*).

"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from flask import (
    Flask,
    request,
    render_template_string,
    send_from_directory,
    redirect,
    url_for,
)
from openai import AzureOpenAI

# ---------------------------------------------------------------------------
#  Configuration & Azure clients
# ---------------------------------------------------------------------------

load_dotenv()  # Load .env file (if present)

# --- Mandatory environment variables --------------------------------------
AZURE_OPENAI_ENDPOINT: str = os.getenv("ENDPOINT_URL")
AZURE_OPENAI_DEPLOYMENT: str = os.getenv("DEPLOYMENT_NAME")
AZURE_OPENAI_API_KEY: str | None = os.getenv("AZURE_OPENAI_API_KEY")

AZURE_SEARCH_ENDPOINT: str = os.getenv(
    "SEARCH_ENDPOINT"
)
AZURE_SEARCH_KEY: str | None = os.getenv("SEARCH_KEY")
AZURE_SEARCH_INDEX: str = os.getenv("SEARCH_INDEX_NAME")

if not AZURE_OPENAI_API_KEY:
    raise EnvironmentError("AZURE_OPENAI_API_KEY is required but not set.")

if not AZURE_SEARCH_KEY:
    raise EnvironmentError("SEARCH_KEY is required but not set.")

# --- Flask app -------------------------------------------------------------
app = Flask(__name__, static_folder=".", static_url_path="")
app.secret_key = os.getenv("FLASK_SECRET", "change-this-secret")

# --- Azure OpenAI client (key‑based auth) ----------------------------------
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2025-01-01-preview",
)

# ---------------------------------------------------------------------------
#  Helper utilities
# ---------------------------------------------------------------------------

def current_time() -> str:
    """Current local time formatted nicely (e.g. '10:05 AM')."""
    return datetime.now().strftime("%I:%M %p")


def clean_response(text: str) -> str:
    """Remove citation tokens like `[doc1]` and tidy whitespace/punctuation."""
    text = re.sub(r"\[doc\d+\]", "", text)
    text = re.sub(r"\s+\.", ".", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
#  Conversation state (kept in memory – fine for small deployments)
# ---------------------------------------------------------------------------

conversation_history: List[Dict[str, Any]] = [
    {
        "role": "assistant",
        "content": "Hello! How can I assist you today?",
        "timestamp": current_time(),
    }
]


# ---------------------------------------------------------------------------
#  Chatbot logic – call Azure OpenAI w/ Azure Search grounding
# ---------------------------------------------------------------------------

def get_chatbot_response(user_message: str) -> str:
    """Append user message, query Azure OpenAI, store and return assistant reply."""

    conversation_history.append(
        {"role": "user", "content": user_message, "timestamp": current_time()}
    )

    # Strip timestamps for model call
    messages_for_api = [
        {"role": m["role"], "content": m["content"]} for m in conversation_history
    ]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=messages_for_api,
        max_tokens=800,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        extra_body={
            "data_sources": [
                {
                    "type": "azure_search",
                    "parameters": {
                        "endpoint": AZURE_SEARCH_ENDPOINT,
                        "index_name": AZURE_SEARCH_INDEX,
                        "semantic_configuration": "default",
                        "query_type": "simple",
                        "fields_mapping": {},
                        "in_scope": True,
                        "filter": None,
                        "strictness": 3,
                        "top_n_documents": 5,
                        "authentication": {
                            "type": "api_key",
                            "key": AZURE_SEARCH_KEY,
                        },
                    },
                }
            ]
        },
    )

    assistant_reply: str = clean_response(response.choices[0].message.content)

    conversation_history.append(
        {
            "role": "assistant",
            "content": assistant_reply,
            "timestamp": current_time(),
        }
    )

    return assistant_reply


# ---------------------------------------------------------------------------
#  Chat UI template (served inside iframe)
# ---------------------------------------------------------------------------

CHATBOT_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Gradient M Chatbot</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap\" rel=\"stylesheet\">
  <style>
    html,body{margin:0;padding:0;height:100%;font-family:'Inter',sans-serif}
    body{display:flex;align-items:center;justify-content:center;background:#f2f2f2}
    .chat-container{width:100vw;height:100vh;display:flex;flex-direction:column;background:#fff;overflow:hidden}
    .chat-header{background:#fff;border-bottom:1px solid #e0e0e0;padding:16px;text-align:center;font-weight:600;font-size:1.2rem;position:relative}
    .chat-header a{position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:.9rem;color:#3f51b5;text-decoration:underline}
    .loading-indicator{display:none;width:100%;height:4px;background:linear-gradient(90deg,#4A90E2,#76c7c0,#4A90E2);background-size:200% 100%;animation:load 1.5s linear infinite}
    @keyframes load{0%{background-position:0 0}100%{background-position:200% 0}}
    .chat-messages{flex:1;padding:16px;overflow-y:auto;display:flex;flex-direction:column;gap:12px}
    .chat-messages::-webkit-scrollbar{width:6px}
    .chat-messages::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}
    .message{max-width:80%;display:flex;flex-direction:column}
    .assistant{align-self:flex-start}.user{align-self:flex-end;text-align:right}
    .bubble{padding:12px 16px;border-radius:8px;background:#f1f1f1;animation:fade .3s forwards}
    .user .bubble{background:#e7f0fd}
    @keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
    .timestamp{font-size:.75rem;color:#999;margin-top:4px}
    .chat-input{display:flex;border-top:1px solid #e0e0e0;padding:16px;gap:8px;background:#fff}
    .chat-input input{flex:1;padding:12px 16px;border:1px solid #e0e0e0;border-radius:4px}
    .chat-input button{background:#3f51b5;border:none;border-radius:4px;padding:12px 16px;color:#fff;cursor:pointer}
    @media(max-width:480px){.chat-header{font-size:1rem;padding:12px}.chat-input{padding:12px}.chat-input input{padding:10px 12px}.chat-input button{padding:10px 14px}}
  </style>
</head>
<body>
  <div class=\"chat-container\">
    <div class=\"chat-header\">Gradient M Chatbot <a href=\"/reset\">Clear</a></div>
    <div id=\"loader\" class=\"loading-indicator\"></div>
    <div class=\"chat-messages\">
      {% for msg in conversation %}
        <div class=\"message {{ msg.role }}\">
          <div class=\"bubble\">{{ msg.content }}</div>
          <div class=\"timestamp\">{{ msg.timestamp }}</div>
        </div>
      {% endfor %}
    </div>
    <form class=\"chat-input\" action=\"/chat\" method=\"post\" onsubmit=\"document.getElementById('loader').style.display='block';\">
      <input type=\"text\" name=\"question\" placeholder=\"Type your question…\" required autofocus>
      <button type=\"submit\">Send</button>
    </form>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
#  Flask routes
# ---------------------------------------------------------------------------

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        user_q = request.form.get("question", "").strip()
        if user_q:
            get_chatbot_response(user_q)
        return redirect(url_for("chat"))
    return render_template_string(CHATBOT_TEMPLATE, conversation=conversation_history)


@app.route("/")
def home():
    """Serve the public website root - index.html is located in the same directory."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/reset")
def reset():
    """Clear conversation history and redirect back to /chat."""
    global conversation_history
    conversation_history = [
        {
            "role": "assistant",
            "content": "Hello! How can I assist you today?",
            "timestamp": current_time(),
        }
    ]
    return redirect(url_for("chat"))


# ---------------------------------------------------------------------------
#  Security headers – allow same‑origin iframing of /chat
# ---------------------------------------------------------------------------

@app.after_request
def allow_iframe(resp):
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    return resp


# ---------------------------------------------------------------------------
#  Entry‑point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
