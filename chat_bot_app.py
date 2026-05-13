from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)
user_state = {}


def handle_scripted_flow(user_message: str) -> str | None:
    user_message_lower = (user_message or "").lower()

    main_options = {
        "our services": "services",
        "services": "services",
        "need support": "specific_requirement",
        "i have a specific requirement": "specific_requirement",
        "career opportunities": "career",
        "career": "career",
        "contact us": "contact",
    }

    if user_message_lower in main_options:
        user_state["step"] = main_options[user_message_lower]

    step = user_state.get("step", None)

    # Step 2 – Services
    if step == "services":
        services_list = ["IT Consulting", "Cloud Services", "Digital Workplace", "Talent Acquisition", "Data & AI"]
        if user_message in services_list:
            user_state["step"] = "contact_details"
            return (
                f"Thanks for selecting '<b>{user_message}</b>'.<br><br>"
                "Please share your contact details so our team can reach out to you:<br>"
                "- Name<br>- Phone Number<br>- Email ID<br>- Company Name<br>- Requirements / Message"
            )
        else:
            buttons_html = " ".join([
                f"<button class='chat-btn' onclick=\"sendOption('{s}')\">{s}</button>"
                for s in services_list
            ])
            return f"Select the service you’re looking for:<br><br>{buttons_html}"

    # Step 3 – Specific requirement / support
    if step == "specific_requirement":
        user_state["step"] = "contact_details"
        return (
            "Thanks for sharing your requirement. Now, please provide your contact details:<br>"
            "- Name<br>- Phone Number<br>- Email ID<br>- Company Name<br>- Requirements / Message"
        )

    # Step 4 – Contact Us
    if step == "contact":
        user_state["step"] = "contact_details"
        return (
            "Please share your contact details:<br>"
            "- Name<br>- Phone Number<br>- Email ID<br>- Company Name<br>- Requirements / Message"
        )

    # Step 5 – Career
    if step == "career":
        user_state["step"] = "done"
        return (
            "Check our <a href='https://www.gradientm.com/careers' target='_blank'>Career page</a> for current openings."
        )

    # Final Step – After contact details
    if step == "contact_details":
        user_state["step"] = "done"
        return "Thanks! Our team will contact you shortly."

    return None


@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <title>GradientM Chatbot</title>
  <style>
    body { font-family: Arial, sans-serif; margin:0; padding:0; }
    /* Floating chat icon */
    #chat-icon {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #F3A233;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        font-size: 30px;
        color: white;
    }
    /* Chat container */
    #chat-container {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 400px;
        height: 500px;
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        display: none;
        flex-direction: column;
        overflow: hidden;
        z-index: 999;
    }
    #chat-header { background: #F3A233; color: white; padding: 12px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; }
    #chat { flex: 1; padding: 15px; overflow-y: auto; }
    .user { color: #1d4ed8; margin: 8px 0; font-weight: bold; }
    .bot { color: #065f46; margin: 8px 0; }
    .chat-btn {
        background-color:#F3A233;
        color:white;
        padding:12px;
        margin:8px 0;
        border:none;
        border-radius:10px;
        cursor:pointer;
        width:100%;
        text-align:center;
        font-size:15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    .chat-btn:hover { opacity:0.9; }
    #input-area { display: flex; border-top: 1px solid #ddd; }
    #message { flex: 1; border: none; padding: 12px; font-size: 14px; }
    #send-btn { background: #F3A233; color: white; border: none; padding: 0 20px; cursor: pointer; }
    #clear-btn { background: transparent; border: none; color: white; cursor: pointer; font-size: 13px; }
  </style>
  <script>
    function toggleChat() {
        const chat = document.getElementById("chat-container");
        chat.style.display = (chat.style.display === "flex") ? "none" : "flex";
    }
    async function sendMessage() {
      const input = document.getElementById("message");
      const msg = input.value;
      if (!msg) return;
      document.getElementById("chat").innerHTML += "<div class='user'>You: " + msg + "</div>";
      input.value = "";
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      document.getElementById("chat").innerHTML += "<div class='bot'>Bot: " + data.reply + "</div>";
      document.getElementById("chat").scrollTop = document.getElementById("chat").scrollHeight;
    }
    async function sendOption(option) {
      document.getElementById("chat").innerHTML += "<div class='user'>You: " + option + "</div>";
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: option })
      });
      const data = await res.json();
      document.getElementById("chat").innerHTML += "<div class='bot'>Bot: " + data.reply + "</div>";
      document.getElementById("chat").scrollTop = document.getElementById("chat").scrollHeight;
    }
    function showInitialMessage() {
      document.getElementById("chat").innerHTML = "<div class='bot'>👋 Welcome to <b>GradientM</b>! How can I help you today?<br><br>"
        + "<button class='chat-btn' onclick=\\\"sendOption('Our Services')\\\">Our Services</button>"
        + "<button class='chat-btn' onclick=\\\"sendOption('I have a Specific Requirement')\\\">I have a Specific Requirement</button>"
        + "<button class='chat-btn' onclick=\\\"sendOption('Career Opportunities')\\\">Career Opportunities</button>"
        + "<button class='chat-btn' onclick=\\\"sendOption('Contact Us')\\\">Contact Us</button></div>";
    }
    function clearChat() {
      fetch("/reset", { method: "POST" });  // reset backend state
      showInitialMessage();
    }
    window.onload = () => { showInitialMessage(); };
  </script>
</head>
<body>
  <div id="chat-icon" onclick="toggleChat()">💬</div>
  <div id="chat-container" style="display: none; flex-direction: column;">
    <div id="chat-header">
      <span>GradientM</span>
      <button id="clear-btn" onclick="clearChat()">🗑 Clear</button>
    </div>
    <div id="chat"></div>
    <div id="input-area">
      <input type="text" id="message" placeholder="Type a message...">
      <button id="send-btn" onclick="sendMessage()">Send</button>
    </div>
  </div>
</body>
</html>
""")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    reply = handle_scripted_flow(user_message)
    if not reply:
        reply = "Sorry, I couldn't process that right now."
    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    user_state.clear()
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
