import logging
import sys
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import asyncio
from beep import GeminiNetwork
import os
import threading
import json
import markdown2
from functools import partial
from threading import Thread

logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('flask_limiter').setLevel(logging.WARNING)

# Set up logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use sys.stdout for better Unicode handling
    ]
)
logger = logging.getLogger(__name__)

# Force UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Initialize Flask app first
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize rate limiter after Flask app
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

network = None
loop = None
background_thread = None
is_initialized = False

# Node icon mapping
NODE_ICONS = {
    'scrum_master': '👨‍💼',
    'assistant': '🤖',
    'researcher': '🔍',
    'writer': '✍️',
    'analyst': '📊',
    'reviewer': '👀',
    'designer': '🎨',
    'developer': '💻',
    'tester': '🧪',
    'content-specialist': '📝',
    'plot-architect': '📚',
    'character-designer': '👤',
    'narrative-writer': '📖',
    'dialogue-writer': '💭',
    'world-builder': '🌍',
    'editor': '✂️',
    'proofreader': '📋',
    'vrchat-planner': '🎮',
    'discord-manager': '💬',
    'scheduler': '📅'
}

async def init_network():
    global network, is_initialized
    try:
        network = GeminiNetwork()
        await network._initialize_mother_node()
        is_initialized = True
        logger.info("Network initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize network: {str(e)}")
        raise

def run_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def start_background_loop():
    global loop, background_thread
    loop = asyncio.new_event_loop()
    background_thread = Thread(target=run_background_loop, args=(loop,))
    background_thread.daemon = True
    background_thread.start()

def cleanup():
    global loop, background_thread
    if loop:
        loop.call_soon_threadsafe(loop.stop)
    if background_thread:
        background_thread.join()

def get_node_icon(role):
    """Get icon for a node based on its role."""
    normalized_role = role.lower().replace(' ', '-')
    return NODE_ICONS.get(normalized_role, '🔵')

def format_instance_response(instance_id, response, role):
    """Format a single instance response with name, icon, and markdown-converted text."""
    icon = get_node_icon(role)
    markdown_response = markdown2.markdown(response, extras=['fenced-code-blocks', 'tables', 'break-on-newline'])
    return {
        'id': instance_id,
        'role': role,
        'icon': icon,
        'response': response,
        'markdown': markdown_response
    }

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/instances', methods=['GET'])
@limiter.limit("300 per minute")
def get_instances():
    if not network:
        return jsonify({'error': 'Network not initialized'}), 503
    try:
        future = asyncio.run_coroutine_threadsafe(network.list_instances(), loop)
        result = future.result(timeout=10)
        if 'mother_node' in result:
            result['mother_node']['icon'] = get_node_icon(result['mother_node']['role'])
        if 'instances' in result:
            for instance in result['instances']:
                instance['icon'] = get_node_icon(instance['role'])
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing instances: {str(e)}")
        return jsonify({'error': 'Failed to list instances'}), 500

@app.route('/api/send_message', methods=['POST'])
@limiter.limit("5 per minute")
def send_message():
    global network, is_initialized
    
    if not is_initialized or not network:
        logger.error("Attempted to send message before network initialization")
        return jsonify({'error': 'System is still initializing. Please try again in a moment.'}), 503

    try:
        data = request.get_json()
        if not data or not data.get('message', '').strip():
            return jsonify({'error': 'No data provided'}), 400

        user_message = data.get('message', '').strip()
        logger.info(f"Received message: {user_message}")
        
        # Get responses asynchronously
        future = asyncio.run_coroutine_threadsafe(
            network.handle_user_input(user_message),
            loop
        )
        
        responses = []
        
        # 1. Add mother node's planning response
        if network.mother_node and network.mother_node.history:
            responses.append({
                'role': 'scrum_master',
                'content': network.mother_node.history[-2]['text'] if len(network.mother_node.history) >= 2 else '',
                'icon': get_node_icon('scrum_master'),
                'type': 'planning'
            })
        
        # 2. Add all specialist node responses in order
        for instance_id, instance in network.instances.items():
            if instance and instance.history:
                last_response = instance.history[-1]['text']
                responses.append({
                    'role': instance.role,
                    'content': last_response,
                    'icon': get_node_icon(instance.role),
                    'type': 'specialist'
                })
        
        # 3. Get and add mother node's final synthesis
        final_response = future.result()
        if final_response:
            responses.append({
                'role': 'scrum_master',
                'content': final_response,
                'icon': get_node_icon('scrum_master'),
                'type': 'synthesis'
            })

        # Log full conversation flow
        for response in responses:
            logger.info(f"{response['role']} ({response['type']}): {response['content']}")

        return jsonify({'responses': responses})

    except Exception as e:
        logger.error("Error processing message: %r", e, exc_info=True)
        return jsonify({'error': f'Failed to process message: {str(e)}'}), 500

@app.route('/api/clear', methods=['POST'])
def clear_all():
    if not network:
        return jsonify({'error': 'Network not initialized'}), 503
    try:
        # Reset mother node
        if network.mother_node:
            network.mother_node.history = []
        
        # Clear all instances
        network.instances = {}
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing network: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/typing', methods=['POST'])
def typing():
    return jsonify({"status": "typing received"})

@app.route('/api/edit_message', methods=['POST'])
def edit_message():
    data = request.get_json()
    message_id = data.get('message_id')
    new_content = data.get('new_content')
    return jsonify({'status': 'success'})

@app.route('/api/delete_message', methods=['POST'])
def delete_message():
    data = request.get_json()
    message_id = data.get('message_id')
    return jsonify({'status': 'success'})

def initialize_network():
    global network
    future = asyncio.run_coroutine_threadsafe(
        init_network(),
        loop
    )
    try:
        future.result(timeout=30)
    except Exception as e:
        logger.error(f"Failed to initialize network: {e}")
        raise

def run_async_app():
    global loop, network
    
    start_background_loop()
    
    try:
        initialize_network()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        cleanup()
        raise
    
    return app

if __name__ == '__main__':
    app = run_async_app()
    try:
        app.run(debug=True, port=5000)
    finally:
        cleanup()
