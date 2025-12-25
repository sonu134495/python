# two_person_chat.py
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

users = {}  # track username by session ID

html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Two-Person Chat</title>
<style>
body { font-family: Arial; background:#f0f2f5; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;}
.chat-container { width:400px; max-width:90%; background:#fff; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.1); display:flex; flex-direction:column; overflow:hidden;}
.chat-header { background:#007bff; color:#fff; padding:15px; text-align:center; font-size:1.2em;}
.chat-messages { flex:1; padding:15px; overflow-y:auto;}
.message { margin-bottom:10px; padding:8px 12px; border-radius:10px; max-width:80%; word-wrap:break-word;}
.message.user { background:#007bff; color:#fff; align-self:flex-end;}
.message.other { background:#e5e5ea; color:#000; align-self:flex-start;}
.message.system { background:#ccc; color:#000; text-align:center; border-radius:5px; max-width:100%;}
.chat-input { display:flex; border-top:1px solid #ddd;}
.chat-input input { flex:1; border:none; padding:15px; font-size:1em;}
.chat-input button { background:#007bff; color:#fff; border:none; padding:15px 20px; cursor:pointer;}
.chat-input input:focus { outline:none;}
.chat-input button:hover { background:#0056b3;}
#username-prompt { position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; }
#username-prompt input { padding:10px; font-size:1em; }
#username-prompt button { padding:10px 15px; margin-left:10px; }
</style>
</head>
<body>
<div id="username-prompt">
  <input type="text" id="username-input" placeholder="Enter your name" />
  <button onclick="setUsername()">Join</button>
</div>

<div class="chat-container" style="display:none;">
  <div class="chat-header">Two-Person Chat</div>
  <div class="chat-messages" id="messages"></div>
  <div class="chat-input">
    <input type="text" id="input" placeholder="Type a message..." />
    <button onclick="sendMessage()">Send</button>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
let username = "";
const socket = io();
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');

function appendMessage(text, type){
  const msg = document.createElement('div');
  msg.classList.add('message', type);
  msg.textContent = text;
  messagesEl.appendChild(msg);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function sendMessage(){
  const text = inputEl.value.trim();
  if(!text) return;
  appendMessage("Me: " + text, 'user');
  socket.emit('chat_message', {user: username, msg: text});
  inputEl.value = '';
}

inputEl.addEventListener('keypress', e=>{
  if(e.key==='Enter') sendMessage();
});

function setUsername(){
  const input=document.getElementById('username-input');
  if(input.value.trim()==="") return;
  username=input.value.trim();
  document.getElementById('username-prompt').style.display='none';
  document.querySelector('.chat-container').style.display='flex';
  socket.emit('join', username);
}

// Listen for messages from server
socket.on('chat_message', data=>{
  if(data.user !== username){
    appendMessage(data.user + ": " + data.msg, 'other');
  }
});

socket.on('system', data=>{
  appendMessage(data, 'system');
});
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(html)

@socketio.on('join')
def handle_join(name):
    if len(users) < 2:
        users[request.sid] = name
        emit('system', f"{name} joined the chat.", broadcast=True)
    else:
        emit('system', "Chat is full. Only two users allowed.", room=request.sid)

@socketio.on('chat_message')
def handle_chat_message(data):
    emit('chat_message', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        name = users.pop(request.sid)
        emit('system', f"{name} left the chat.", broadcast=True)

if __name__=="__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
