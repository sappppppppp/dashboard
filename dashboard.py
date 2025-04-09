from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key

# Global in-memory store for conversations.
# We use a fixed conversation ID for our persistent chat.
conversations = {}

def get_main_conversation():
    conv_id = "main_chat"
    if conv_id not in conversations:
        conversations[conv_id] = {"messages": []}  # Each message is a dict: {"sender": "user"/"bot", "text": "..."}
    return conv_id

@app.route('/new/main')
def new_main_conversation():
    conv_id = get_main_conversation()  # Always "main_chat"
    return jsonify({"conversation_id": conv_id})

# Chat interface page that always uses the persistent conversation.
@app.route('/chat')
def chat():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return "Invalid conversation id", 400
    return render_template_string(CHAT_HTML, cid=conv_id)

# Return all messages in the conversation.
@app.route('/messages/<conv_id>')
def get_messages(conv_id):
    if conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    return jsonify({"messages": conversations[conv_id]["messages"]})

# Endpoint for the user to send a message.
@app.route('/send', methods=['POST'])
def send():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    data = request.get_json()
    text = data.get("message", "")
    conversations[conv_id]["messages"].append({"sender": "user", "text": text})
    return jsonify({"status": "Message received"})

# Endpoint for the bot (or main script) to send a reply.
@app.route('/reply', methods=['POST'])
def reply():
    conv_id = request.args.get("cid")
    if not conv_id or conv_id not in conversations:
        return jsonify({"error": "Invalid conversation id"}), 400
    data = request.get_json()
    text = data.get("message", "")
    conversations[conv_id]["messages"].append({"sender": "bot", "text": text})
    return jsonify({"status": "Bot reply added"})

CHAT_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Persistent Chat</title>
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
    <h2>Persistent Chat</h2>
    <div id="chat"></div>
    <input type="text" id="input" placeholder="Type your message and press Enter" autofocus>
    <script>
        const cid = "{{ cid }}";
        let prevMessagesLength = 0; // Track previous message count

        function renderMessages(messages) {
            const chatDiv = document.getElementById("chat");
            chatDiv.innerHTML = "";
            messages.forEach(msg => {
                const div = document.createElement("div");
                div.className = "message " + msg.sender;
                div.textContent = msg.sender.toUpperCase() + ": " + msg.text;
                chatDiv.appendChild(div);
            });
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }

        function fetchMessages() {
            fetch('/messages/' + cid)
                .then(response => response.json())
                .then(data => {
                    if (data.messages) {
                        renderMessages(data.messages);
                        // Log the new title value to the console.
                        const newTitle = "Persistent Chat HERE " + new Date().toLocaleString();
                        console.log("Updating title to:", newTitle);
                        document.title = newTitle;
                    }
                });
        }

        function sendMessage(text) {
            fetch('/send?cid=' + cid, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: text})
            }).then(() => {
                fetchMessages();
            });
        }

        document.getElementById("input").addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                const text = this.value.trim();
                if (text !== "") {
                    sendMessage(text);
                    this.value = "";
                }
            }
        });

        setInterval(fetchMessages, 2000);
        fetchMessages(); // Initial fetch
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
