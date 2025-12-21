# src/main.py
from flask import Flask, request, abort
from src.core.config import VERIFY_TOKEN_META
from src.webhook_handler import process_incoming_message
from src.core.logger import logger

app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token == VERIFY_TOKEN_META and challenge:
            return challenge
        else:
            abort(403)
    elif request.method == 'POST':
        data = request.json
        logger.info(f"Received webhook: {data}")
        process_incoming_message(data)
        return 'OK', 200

@app.route('/', methods=['GET'])
def home():
    return "ProQuery HR Bot is running!", 200

if __name__ == '__main__':
    app.run(debug=True)