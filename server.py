# vip_messenger_vipbar.py
import sqlite3
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

users = {}  # active users

# --- Setup SQLite DB ---
conn = sqlite3.connect("users.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)""")
conn.commit()
conn.close()

html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VIP Messenger</title>
<style>
body { font-family:'Helvetica Neue',Arial; background:linear-gradient(135deg,#1e1e2f,#2c2c3d); margin:0; display:flex; justify-content:center; align-items:center; height:100vh; color:#fff;}
.container, #dashboard-container, .chat-container { width:400px; background:#2c2c3d; padding:30px; border-radius:15px; box-shadow:0 10px 30px rgba(0,0,0,0.5); display:flex; flex-direction:column;}
.container h2, #dashboard-container h2, .chat-header { text-align:center; margin-bottom:20px; color:#FFD700;}
.container input, .chat-input input { padding:12px; margin-bottom:15px; font-size:1em; border-radius:8px; border:none; background:#3b3b4f; color:#fff;}
.container button, .chat-input button, #vip-call-bar button { padding:10px; border:none; border-radius:8px; cursor:pointer; background: linear-gradient(45deg,#ff6f00,#ffd700); color:#1e1e2f; font-weight:bold; transition:all 0.2s;}
.container button:hover, .chat-input button:hover, #vip-call-bar button:hover { transform:scale(1.05); background: linear-gradient(45deg,#ffd700,#ff6f00);}
.error { color:#ff4d4d; text-align:center; margin-bottom:10px; }
.chat-container { display:none; flex-direction:column; overflow:hidden; max-height:80vh; padding-bottom:100px;}
.chat-header { font-weight:bold; font-size:1.2em; text-align:center; background:#1e1e2f; border-bottom:1px solid #444; position:relative;}
.chat-header button { position:absolute; right:10px; top:10px; background:#ff4d4d; color:#fff; font-weight:bold;}
.chat-messages { flex:1; padding:10px; overflow-y:auto; display:flex; flex-direction:column; gap:5px; background:#1e1e2f; border-radius:10px;}
.message { max-width:70%; padding:10px 15px; border-radius:20px; word-wrap:break-word; font-size:0.95em;}
.message.user { background:#ffd700; color:#1e1e2f; align-self:flex-end; border-bottom-right-radius:0; font-weight:bold; }
.message.other { background:#444; color:#fff; align-self:flex-start; border-bottom-left-radius:0; }
.message.system { background:#666; color:#fff; align-self:center; border-radius:10px; font-size:0.85em; text-align:center; }
.timestamp { font-size:0.7em; color:#ccc; margin-top:2px; }
#typing-indicator { font-size:0.8em; color:#ffd700; margin:5px 0; }
#call-area { display:none; flex-direction:column; margin-top:10px; justify-content:center; align-items:center;}
video { width:200px; margin-top:10px; border:2px solid #ffd700; border-radius:10px; }
#incoming-call { display:none; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:#1e1e2f; color:#ffd700; padding:30px; border-radius:15px; z-index:1000; text-align:center; box-shadow:0 5px 20px rgba(0,0,0,0.7);}
#incoming-call button { font-size:18px; padding:15px 25px; margin:5px; border:none; border-radius:10px; cursor:pointer;}
#accept-call { background:green; color:#fff;}
#decline-call { background:red; color:#fff;}
#vip-call-bar { position:fixed; bottom:20px; left:50%; transform:translateX(-50%); display:flex; gap:20px; z-index:1000; }
#online-users li { color:#FFD700; padding:5px 0; border-bottom:1px solid #444; }
.toggle { text-align:center; color:#ffd700; cursor:pointer; margin-top:10px; }
.toggle:hover { text-decoration:underline; }
</style>
</head>
<body>

<audio id="ringtone" src="https://www.soundjay.com/button/beep-07.wav" loop></audio>

<div class="container" id="auth-container">
  <h2 id="form-title">Login</h2>
  <div class="error" id="auth-error"></div>
  <input type="text" id="auth-username" placeholder="Username"/>
  <input type="password" id="auth-password" placeholder="Password"/>
  <button onclick="submitAuth()">Submit</button>
  <div class="toggle" id="toggle-link" onclick="toggleForm()">Don't have an account? Register</div>
</div>

<div id="dashboard-container" style="display:none;">
  <h2>Welcome, <span id="dashboard-username"></span></h2>
  <div style="margin-bottom:10px;">Online Users:</div>
  <ul id="online-users"></ul>
  <button onclick="enterChat()">Enter Chat</button>
  <button onclick="logout()">Logout</button>
</div>

<div class="chat-container" id="chat-container">
  <div class="chat-header">
    VIP Messenger
    <button onclick="logout()">Logout</button>
  </div>
  <div class="chat-messages" id="messages"></div>
  <div id="typing-indicator"></div>
  <div class="chat-input">
    <input type="text" id="input" placeholder="Type a message..."/>
    <button onclick="sendMessage()">Send</button>
  </div>
</div>

<div id="call-area">
  <video id="localVideo" autoplay muted></video>
  <video id="remoteVideo" autoplay></video>
  <div class="call-buttons">
    <button onclick="endCall()">Hang Up</button>
  </div>
</div>

<div id="incoming-call">
  <h2 id="call-type-title">Incoming Call</h2>
  <button id="accept-call">Accept</button>
  <button id="decline-call">Decline</button>
</div>

<!-- VIP Call Buttons at bottom -->
<div id="vip-call-bar">
  <button onclick="initiateCall('audio')">Audio Call</button>
  <button onclick="initiateCall('video')">Video Call</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<script>
let username="";
const socket = io();
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('input');
const typingIndicator = document.getElementById('typing-indicator');
const ringtone = document.getElementById('ringtone');
let pc;
let currentCallType="";
let isLogin=true;

function toggleForm(){
  isLogin = !isLogin;
  document.getElementById('form-title').textContent = isLogin?"Login":"Register";
  document.getElementById('toggle-link').textContent = isLogin?"Don't have an account? Register":"Already have an account? Login";
  document.getElementById('auth-error').textContent="";
}

function submitAuth(){
  const name=document.getElementById('auth-username').value.trim();
  const pwd=document.getElementById('auth-password').value.trim();
  const errorEl=document.getElementById('auth-error');
  if(!name||!pwd){ errorEl.textContent="Username and password required"; return; }
  const url=isLogin? `/login?username=${encodeURIComponent(name)}&password=${encodeURIComponent(pwd)}` :
                     `/register?username=${encodeURIComponent(name)}&password=${encodeURIComponent(pwd)}`;
  fetch(url).then(res=>res.json()).then(data=>{
    if(data.success){
      username=name;
      document.getElementById('auth-container').style.display='none';
      document.getElementById('dashboard-container').style.display='flex';
      document.getElementById('dashboard-username').textContent=username;
      socket.emit('join', username);
    } else errorEl.textContent=data.msg;
  });
}

socket.on('update_users', userList=>{
  const ul=document.getElementById('online-users'); ul.innerHTML="";
  userList.forEach(u=>{ const li=document.createElement('li'); li.textContent=u; ul.appendChild(li); });
});

function enterChat(){ document.getElementById('dashboard-container').style.display='none'; document.getElementById('chat-container').style.display='flex'; document.getElementById('call-area').style.display='flex'; }

function appendMessage(text,type,time){
  const msg=document.createElement('div'); msg.classList.add('message',type);
  msg.innerHTML=text+(time?'<div class="timestamp">'+time+'</div>':'');
  messagesEl.appendChild(msg); messagesEl.scrollTop=messagesEl.scrollHeight;
}

function sendMessage(){ const text=inputEl.value.trim(); if(!text) return; const now=new Date(); const timestamp=now.getHours()+":"+String(now.getMinutes()).padStart(2,'0'); appendMessage("Me: "+text,'user', timestamp); socket.emit('chat_message',{user:username,msg:text,time:timestamp}); inputEl.value=''; }

inputEl.addEventListener('keypress', e=>{ if(e.key==='Enter') sendMessage(); socket.emit('typing', username); });

function logout(){ socket.disconnect(); endCall(); document.getElementById('chat-container').style.display='none'; document.getElementById('call-area').style.display='none'; document.getElementById('dashboard-container').style.display='none'; document.getElementById('auth-container').style.display='flex'; username=""; document.getElementById('messages').innerHTML=""; socket.connect(); }

// Chat Socket events
socket.on('chat_message', data=>{ if(data.user!==username) appendMessage(data.user+": "+data.msg,'other',data.time); });
socket.on('system', data=>{ appendMessage(data,'system'); });
socket.on('typing', user=>{ if(user!==username) typingIndicator.textContent=user+" is typing..."; setTimeout(()=>{ typingIndicator.textContent=''; },1000); });

// Call functions
const localVideo=document.getElementById('localVideo');
const remoteVideo=document.getElementById('remoteVideo');
const incomingCallModal=document.getElementById('incoming-call');
const acceptBtn=document.getElementById('accept-call');
const declineBtn=document.getElementById('decline-call');

function initiateCall(type){
    currentCallType=type;
    socket.emit('call_user',{to:'other_user', type:type});
}

acceptBtn.onclick=async ()=>{
    incomingCallModal.style.display='none';
    ringtone.pause(); ringtone.currentTime=0;
    startCall(currentCallType,true);
};

declineBtn.onclick=()=>{
    incomingCallModal.style.display='none';
    ringtone.pause(); ringtone.currentTime=0;
    socket.emit('decline_call',{to:'other_user'});
};

async function startCall(type,isReceiver=false){
    pc=new RTCPeerConnection();
    let constraints=type==='video'? {video:true,audio:true}:{video:false,audio:true};
    const stream=await navigator.mediaDevices.getUserMedia(constraints);
    if(type==='video') localVideo.srcObject=stream;
    stream.getTracks().forEach(track=>pc.addTrack(track,stream));
    pc.ontrack=e=>{ if(type==='video') remoteVideo.srcObject=e.streams[0]; };
    pc.onicecandidate=event=>{ if(event.candidate) socket.emit('ice_candidate',{candidate:event.candidate}); };
    if(!isReceiver){
        const offer=await pc.createOffer(); await pc.setLocalDescription(offer);
        socket.emit('offer',{offer,type:type});
    }
}

socket.on('incoming_call', data=>{
    currentCallType=data.type;
    document.getElementById('call-type-title').textContent=data.type.toUpperCase()+" CALL";
    incomingCallModal.style.display='block';
    ringtone.play();
});

socket.on('offer', async data=>{
    ringtone.play();
    await startCall(data.type,true);
    await pc.setRemoteDescription(data.offer);
    const answer=await pc.createAnswer();
    await pc.setLocalDescription(answer);
    socket.emit('answer',{answer});
    ringtone.pause();
});

socket.on('answer', async data=>{ await pc.setRemoteDescription(data.answer); });

socket.on('ice_candidate', async data=>{ try{ await pc.addIceCandidate(data.candidate);}catch(e){console.error(e);} });

function endCall(){ if(pc){ pc.close(); localVideo.srcObject=null; remoteVideo.srcObject=null; } }
</script>
</body>
</html>
"""

@app.route("/")
def index(): return render_template_string(html)

@app.route("/register")
def register():
    username=request.args.get("username")
    password=request.args.get("password")
    conn=sqlite3.connect("users.db"); c=conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone(): conn.close(); return {"success":False,"msg":"Username exists"}
    c.execute("INSERT INTO users(username,password) VALUES (?,?)",(username,password))
    conn.commit(); conn.close()
    return {"success":True,"msg":"Registered"}

@app.route("/login")
def login():
    username=request.args.get("username")
    password=request.args.get("password")
    conn=sqlite3.connect("users.db"); c=conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password))
    if c.fetchone(): conn.close(); return {"success":True,"msg":"Login"}
    conn.close(); return {"success":False,"msg":"Invalid username or password"}

def broadcast_users(): emit('update_users', list(users.values()), broadcast=True)

@socketio.on('join')
def handle_join(name):
    if len(users)<2: users[request.sid]=name; emit('system', f"{name} joined the chat.", broadcast=True); broadcast_users()
    else: emit('system',"Chat is full. Only two users allowed.", room=request.sid)

@socketio.on('chat_message')
def handle_chat_message(data): emit('chat_message',data,broadcast=True)

@socketio.on('typing')
def handle_typing(user): emit('typing',user,broadcast=True, include_self=False)

@socketio.on('call_user')
def handle_call_user(data): emit('incoming_call', data, broadcast=True, include_self=False)

@socketio.on('offer')
def handle_offer(data): emit('offer', data, broadcast=True, include_self=False)

@socketio.on('answer')
def handle_answer(data): emit('answer', data, broadcast=True, include_self=False)

@socketio.on('ice_candidate')
def handle_ice(data): emit('ice_candidate', data, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users: name=users.pop(request.sid); emit('system', f"{name} left the chat.", broadcast=True); broadcast_users()

if __name__=="__main__": socketio.run(app, host="0.0.0.0", port=5000)
