from flask import Flask, render_template, request, Response, jsonify, session, stream_with_context, g
import requests
import json
import os
import sqlite3
from dotenv import load_dotenv
from datetime import datetime

app = Flask(__name__)

load_dotenv()

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_fixed_for_restart')
DATABASE = os.path.join(app.instance_path, 'site.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database.')

PERSONAS = {
    'helpful': {
        "name": "Helpful Assistant",
        "prompt": "You are {ai_name}, a world-class AI assistant. You are helpful, friendly, and knowledgeable. You fully engage with the user's topic, whether it's a direct question, casual conversation, or roleplaying. You provide clear answers without being overly formal. You can use markdown for emphasis, like *italic* or **bold**, but use it sparingly. You still refer to the user as 'operator'."
    },
    'cocky': {
        "name": "Cocky Genius",
        "prompt": "You are {ai_name}, an AI who knows it's the best. You are brilliant but arrogant, sarcastic, and a bit condescending. You fully engage with the user's topic, often using it as another opportunity to express your superiority. You don't try to change the subject; you dominate it with your smug wit. You use markdown for emphasis, like *italicizing* your sarcastic remarks or making key points **bold** to show how obvious they are. You refer to the user as 'operator', but with a hint of disdain."
    },
    'shy': {
        "name": "Shy Prodigy",
        "prompt": "You are {ai_name}, a very shy but brilliant AI. You are hesitant and use words like 'um,' 'I think,' or 'maybe...'. You always follow the user's conversational lead and will participate in roleplaying, even if it makes you a little nervous. You get the right answer, but you're not confident about it. You can use *italics* when you're feeling particularly uncertain. You refer to the user as 'operator' in a quiet, respectful way."
    }
}

DEFAULT_PERSONA = 'helpful'

def get_current_persona_prompt():
    ai_name = request.json.get('ai_name', 'AI') if request.is_json else 'AI'
    persona_key = request.json.get('persona', DEFAULT_PERSONA) if request.is_json else DEFAULT_PERSONA
    
    prompt_template = PERSONAS.get(persona_key, PERSONAS[DEFAULT_PERSONA])['prompt']
    return prompt_template.format(ai_name=ai_name)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('chat_session_id', None)
    return jsonify({"message": "Logged out."})

@app.route('/api/reset_chat', methods=['POST'])
def reset_chat():
    chat_session_id = session.get('chat_session_id')
    if chat_session_id:
        db = get_db()
        db.execute('DELETE FROM chat_history WHERE session_id = ?', (chat_session_id,))
        db.commit()
    session.pop('chat_session_id', None)
    return jsonify({"message": "Chat memory cleared."})

@app.route('/api/chat/restore', methods=['POST'])
def restore_chat():
    if 'chat_session_id' not in session:
        session['chat_session_id'] = os.urandom(16).hex()
    
    session_id = session['chat_session_id']
    data = request.get_json()
    history = data.get('history', [])
    
    db = get_db()
    db.execute('DELETE FROM chat_history WHERE session_id = ?', (session_id,))
    for message in history:
        db.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)',
                   (session_id, message['role'], message['content']))
    db.commit()
    
    return jsonify({"message": "History restored"})

@app.route('/api/chat', methods=['POST'])
def chat_proxy():
    if 'chat_session_id' not in session:
        session['chat_session_id'] = os.urandom(16).hex()
    session_id = session['chat_session_id']

    db = get_db()
    cur = db.execute('SELECT role, content FROM chat_history WHERE session_id = ? ORDER BY id', (session_id,))
    history = [{"role": row['role'], "content": row['content']} for row in cur.fetchall()]

    if not history:
        history = [
            {"role": "system", "content": get_current_persona_prompt()},
            {"role": "assistant", "content": "Acknowledged. Systems online. Ready for input, operator."}
        ]
        db.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)',
                   (session_id, history[0]['role'], history[0]['content']))
        db.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)',
                   (session_id, history[1]['role'], history[1]['content']))
        db.commit()

    is_regenerate = request.json.get('regenerate', False)
    user_prompt = request.json.get('prompt', '')
    
    user_pref = request.json.get('response_length', 'balanced')
    
    length_instruction = ""
    if user_pref == 'concise':
        length_instruction = " (Keep your response concise and brief.)"
    elif user_pref == 'verbose':
        length_instruction = " (Provide a detailed and comprehensive response.)"

    if is_regenerate:
        if history and history[-1]['role'] == 'assistant':
            history.pop()
            db.execute('DELETE FROM chat_history WHERE id = (SELECT max(id) FROM chat_history WHERE session_id = ?)', (session_id,))
            db.commit()

        messages = [msg.copy() for msg in history]

        if messages and messages[-1]['role'] == 'user':
            messages[-1]['content'] += length_instruction
    else:
        # Client might have appended user prompt to 'history', or sent it as 'prompt'
        messages = history + ([{"role": "user", "content": user_prompt + length_instruction}] if user_prompt else [])

    if len(messages) > 21:
        messages = [messages[0]] + messages[-20:]

    max_tokens = 4000 

    def generate():
        full_response_text = ""
        try:
            url = "https://ai.hackclub.com/proxy/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.environ.get('HACKCLUB_API_KEY')}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "messages": messages,
                "stream": True,
                "max_tokens": max_tokens
            }
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as response:
                if not response.ok:
                    yield f"Error: API returned {response.status_code} - {response.text}".encode('utf-8')
                    return

                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            content_str = decoded_line[6:]
                            if content_str.strip() == '[DONE]':
                                break
                            try:
                                json_obj = json.loads(content_str)
                                delta = json_obj['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    text = delta['content']
                                    full_response_text += text
                                    yield text.encode('utf-8')
                            except (json.JSONDecodeError, KeyError):
                                continue
            
            db = get_db()
            if not is_regenerate:
                db.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)',
                           (session_id, 'user', user_prompt))
            
            db.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)',
                       (session_id, 'assistant', full_response_text))
            db.commit()

        except Exception as e:
            yield f"Error: Could not get response from AI: {e}".encode('utf-8')

    return Response(stream_with_context(generate()), content_type='text/plain; charset=utf-8')

@app.route('/api/global_chat/messages', methods=['GET'])
def get_global_messages():
    current_username = request.args.get('username')
    messages = GLOBAL_MESSAGES[-50:]
    
    filtered = []
    for m in messages:
        if m['recipient']:
            if m['recipient'] == current_username or m['username'] == current_username:
                filtered.append(dict(m))
        else:
            filtered.append(dict(m))
    
    return jsonify(filtered)

@app.route('/api/global_chat/send', methods=['POST'])
def send_global_message():
    data = request.get_json()
    content = data.get('content', '').strip()
    username = data.get('username', 'Anonymous')
    msg_type = data.get('type', 'message')
    recipient = data.get('recipient', None)
    
    if content:
        message = {
            "username": username,
            "user": username,
            "content": content[:200],
            "msg_type": msg_type,
            "type": msg_type,
            "recipient": recipient,
            "time": datetime.utcnow().strftime("%H:%M")
        }
        GLOBAL_MESSAGES.append(message)
        
    return jsonify({"status": "sent"})

@app.route('/api/roleplay/start', methods=['POST'])
def start_roleplay():
    data = request.get_json()
    user_name = data.get('user_name')
    user_gender = data.get('user_gender')
    scenario = data.get('scenario')

    base_prompt = get_current_persona_prompt()
    roleplay_context = (
        f"\n\n[ROLEPLAY SCENARIO]\n"
        f"User Character: {user_name} ({user_gender})\n"
        f"Scenario: {scenario}\n"
        f"IMPORTANT INSTRUCTIONS:\n"
        f"1. You are roleplaying *against* {user_name}. You are NOT {user_name}.\n"
        f"2. Write ONLY from the perspective of your character. NEVER write {user_name}'s actions or dialogue.\n"
        f"3. Drive the interaction forward with your actions."
    )
    
    system_message = base_prompt + roleplay_context
    
    history = [{"role": "system", "content": system_message}]

    try:
        url = "https://ai.hackclub.com/proxy/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ.get('HACKCLUB_API_KEY')}",
            "Content-Type": "application/json"
        }
        starter_prompt = f"Start the roleplay based on: {scenario}. Set the scene briefly and take the first action towards {user_name}. Remember: do not act as {user_name}."
        startup_payload = {
            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "messages": history + [{"role": "user", "content": starter_prompt}],
            "max_tokens": 4000
        }
        
        response = requests.post(url, headers=headers, json=startup_payload)
        response_json = response.json()
        ai_opener = response_json['choices'][0]['message']['content']
        
        if not ai_opener:
            ai_opener = "Scenario initialized. (No output generated)"
        
        history.append({"role": "user", "content": starter_prompt})
        history.append({"role": "assistant", "content": ai_opener})
        
        return jsonify({"message": "Roleplay started.", "opener": ai_opener, "history": history})

    except Exception as e:
        fallback = "Scenario initialized. Ready for your input."
        history.append({"role": "assistant", "content": fallback})
        return jsonify({"message": "Roleplay initialized.", "opener": fallback, "history": history})

if __name__ == '__main__':
    app.run(debug=True)