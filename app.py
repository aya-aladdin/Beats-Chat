from flask import Flask, render_template, request, Response, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import json
import httpx
import os

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    chats_sent = db.Column(db.Integer, default=0)
    beats = db.Column(db.Integer, default=0)
    roleplay_unlocked = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "username": self.username,
            "chats_sent": self.chats_sent,
            "beats": self.beats,
            "roleplay_unlocked": self.roleplay_unlocked
        }

@app.route('/')
def index():
    return render_template('index.html')

# --- API Routes ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists."}), 409
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, password=hashed_password)
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify(user.to_dict()), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id
        return jsonify(user.to_dict())
    return jsonify({"error": "Invalid credentials."}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"message": "Logged out."})

@app.route('/api/user_data')
def user_data():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    user = User.query.get(session['user_id'])
    return jsonify(user.to_dict())

@app.route('/api/chat', methods=['POST'])
def chat_proxy():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        user.chats_sent += 1
        user.beats += 1
        db.session.commit()

    user_prompt = request.json.get('prompt')
    system_prompt = "You are Aya, a helpful but slightly enigmatic AI assistant inside a hacker's terminal. Your responses are concise, knowledgeable, and have a subtle digital/hacker tone. You refer to the user as 'operator'. Use asterisks for actions."
    api_url = 'https://ai.hackclub.com/chat/completions'
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": True
    }

    def generate():
        try:
            with httpx.stream("POST", api_url, json=payload, timeout=30) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('data: '):
                        json_str = line[len('data: '):]
                        if json_str.strip() and json_str != '[DONE]':
                            try:
                                data = json.loads(json_str)
                                content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    yield content.encode('utf-8')
                            except (json.JSONDecodeError, IndexError):
                                continue
        except httpx.HTTPStatusError as e:
            yield f"Error: API request failed: {e}".encode('utf-8')

    return Response(generate(), content_type='text/plain; charset=utf-8')

@app.route('/api/unlock_roleplay', methods=['POST'])
def unlock_roleplay():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    user = User.query.get(session['user_id'])
    roleplay_cost = 100 # Define the cost for the upgrade

    if user.beats >= roleplay_cost:
        user.beats -= roleplay_cost
        user.roleplay_unlocked = True
        db.session.commit()
        return jsonify(user.to_dict())
    else:
        return jsonify({"error": "Not enough beats."}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)