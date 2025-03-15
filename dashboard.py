import uuid
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key

# Global store for conversations (in memory)
conversations = {}

# Define conversation steps for each flow.
setup_steps = [
    {"key": "minting", "question": "Enter Minting Amount (SOL):"},
    {"key": "distribution", "question": "Enter Distribution Amount (SOL):"},
    {"key": "contract_address", "question": "Enter Contract Address:"},
    {"key": "sol_pool_wallet", "question": "Enter SOL_POOL_WALLET:"},
    {"key": "transaction_signature", "question": "Enter TRANSACTION_SIGNATURE:"},
]

reset_confirm_steps = [
    {"key": "confirm", "question": "Do you want to reset the script with new parameters? (yes/no)"}
]

reset_steps = [
    {"key": "minting", "question": "Enter NEW Minting Amount (SOL):"},
    {"key": "distribution", "question": "Enter NEW Distribution Amount (SOL):"},
    {"key": "contract_address", "question": "Enter NEW Contract Address:"},
    {"key": "sol_pool_wallet", "question": "Enter NEW SOL_POOL_WALLET:"},
    {"key": "transaction_signature", "question": "Enter NEW TRANSACTION_SIGNATURE:"},
]

# General endpoint to create a new conversation for setup or reset (if using a single flow)
@app.route('/new/<flow>')
def new_conversation(flow):
    if flow not in ['setup', 'reset']:
        return jsonify({"error": "Invalid flow"}), 400
    conv_id = str(uuid.uuid4())
    steps = setup_steps if flow == 'setup' else reset_steps
    conversations[conv_id] = {
        "flow": flow,
        "steps": steps,
        "index": 0,
        "responses": {},
        "finished": False
    }
    return jsonify({"conversation_id": conv_id})

# New endpoint for reset confirmation conversation.
@app.route('/new_reset_confirm')
def new_reset_confirm():
    conv_id = str(uuid.uuid4())
    conversations[conv_id] = {
        "flow": "reset_confirm",
        "steps": reset_confirm_steps,
        "index": 0,
        "responses": {},
        "finished": False
    }
    return jsonify({"conversation_id": conv_id})

# New endpoint for reset parameters conversation.
@app.route('/new_reset_parameters')
def new_reset_parameters():
    conv_id = str(uuid.uuid4())
    conversations[conv_id] = {
        "flow": "reset_parameters",
        "steps": reset_steps,
        "index": 0,
        "responses": {},
        "finished": False
    }
    return jsonify({"conversation_id": conv_id})

# Chat interface page that uses the conversation id (cid) provided in the URL.
@app.route('/chat')
def chat():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return "Invalid conversation id", 400
    flow = conversations[conv_id]["flow"]
    if flow == "setup":
        title = "Initial Setup"
    elif flow == "reset_confirm":
        title = "Reset Confirmation"
    elif flow == "reset_parameters":
        title = "Reset Parameters"
    else:
        title = "Reset Parameters"
    return render_template_string(CHAT_HTML, title=title, cid=conv_id)

# Return the current question for a given conversation.
@app.route('/start')
def start():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    conv = conversations[conv_id]
    if conv["index"] < len(conv["steps"]):
        question = conv["steps"][conv["index"]]["question"]
        return jsonify({"message": question})
    else:
        return jsonify({"message": "Conversation complete!"})

# Receive an answer and send the next question.
@app.route('/send', methods=['POST'])
def send():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    conv = conversations[conv_id]
    data = request.get_json()
    user_message = data.get("message", "")
    if conv["index"] < len(conv["steps"]):
        current_key = conv["steps"][conv["index"]]["key"]
        conv["responses"][current_key] = user_message
        conv["index"] += 1
        if conv["index"] < len(conv["steps"]):
            next_question = conv["steps"][conv["index"]]["question"]
            return jsonify({"message": next_question})
        else:
            # For setup and reset_parameters flows, compute additional parameter.
            if conv["flow"] in ["setup", "reset_parameters"]:
                try:
                    minting = float(conv["responses"].get("minting", 0))
                    distribution = float(conv["responses"].get("distribution", 0))
                    conv["responses"]["target_number"] = minting + distribution
                except Exception:
                    conv["responses"]["target_number"] = None
            conv["finished"] = True
            return jsonify({"message": "All parameters received!", "finished": True})
    else:
        return jsonify({"message": "Conversation already complete.", "finished": True})

# Endpoint for external clients (e.g., the main script) to check the conversation state.
@app.route('/conversation/<conv_id>')
def get_conversation(conv_id):
    if conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    conv = conversations[conv_id]
    return jsonify({"finished": conv["finished"], "responses": conv["responses"]})

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; }
        #chat { width: 500px; height: 400px; border: 1px solid #ccc; overflow-y: scroll; padding: 10px; }
        #input { width: 500px; padding: 10px; }
        .message { margin: 5px 0; }
        .bot { color: blue; }
        .user { color: green; }
    </style>
</head>
<body>
    <h2>{{ title }}</h2>
    <div id="chat"></div>
    <input type="text" id="input" placeholder="Type your answer and press Enter" autofocus>
    <script>
        const cid = "{{ cid }}";
        function addMessage(sender, text) {
            const chat = document.getElementById('chat');
            const msg = document.createElement('div');
            msg.className = 'message ' + sender;
            msg.textContent = sender.toUpperCase() + ': ' + text;
            chat.appendChild(msg);
            chat.scrollTop = chat.scrollHeight;
        }
        function sendMessage(message) {
            addMessage('user', message);
            fetch('/send?cid=' + cid, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: message})
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    addMessage('bot', data.message);
                }
                if (data.finished) {
                    document.getElementById('input').disabled = true;
                }
            });
        }
        document.getElementById('input').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const text = this.value.trim();
                if (text !== '') {
                    sendMessage(text);
                    this.value = '';
                }
            }
        });
        // Load the first question on page load.
        window.onload = function() {
            fetch('/start?cid=' + cid)
            .then(response => response.json())
            .then(data => {
                addMessage('bot', data.message);
            });
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
