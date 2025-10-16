from flask import Flask, render_template, request, Response
import requests
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat_proxy():
    user_prompt = request.json.get('prompt')
    if not user_prompt:
        return Response("Error: Prompt is missing.", status=400)

    # Updated system prompt for the new API format
    system_prompt = "You are Aya, a helpful but slightly enigmatic AI assistant inside a hacker's terminal. Your responses are concise, knowledgeable, and have a subtle digital/hacker tone. You refer to the user as 'operator'. Use asterisks for actions."

    def generate():
        # Use the OpenAI-compatible endpoint
        api_url = 'https://ai.hackclub.com/chat/completions'
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "stream": True
        }

        with requests.post(api_url, json=payload, stream=True) as response:
            if not response.ok:
                # If the API call itself fails, stream back an error message
                yield f"Error: Upstream API returned status {response.status_code}".encode('utf-8')
                return

            for chunk in response.iter_lines():
                if chunk:
                    decoded_chunk = chunk.decode('utf-8')
                    # OpenAI-compatible streams prefix data chunks with "data: "
                    if decoded_chunk.startswith('data: '):
                        json_str = decoded_chunk[len('data: '):]
                        if json_str.strip() and json_str != '[DONE]':
                            try:
                                data = json.loads(json_str)
                                content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    yield content.encode('utf-8')
                            except json.JSONDecodeError:
                                # Ignore chunks that are not valid JSON
                                continue

    return Response(generate(), content_type='text/plain')

if __name__ == '__main__':
    app.run(debug=True)