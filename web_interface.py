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
import time
from functools import partial
from threading import Thread
from config_file import RATE_LIMIT

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
loop = None  # Will be initialized in run_async_app
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
        
        # Add icon and additional details for mother node
        if 'mother_node' in result:
            result['mother_node']['icon'] = get_node_icon(result['mother_node']['role'])
            result['mother_node']['status'] = 'active'
            result['mother_node']['model'] = network.mother_node.model_name
            result['mother_node']['created_at'] = network.mother_node.created_at
            result['mother_node']['message_count'] = len(network.mother_node.history)
            result['mother_node']['connected_to'] = list(network.mother_node.connected_instances.keys())
            result['mother_node']['last_active'] = time.time()
            result['mother_node']['response_time_avg'] = 1.5  # Mock value - would track actual response times
        
        # Add icon and additional details for instances
        if 'instances' in result:
            for instance in result['instances']:
                instance_id = instance['id']
                if instance_id in network.instances:
                    instance_obj = network.instances[instance_id]
                    instance['icon'] = get_node_icon(instance['role'])
                    instance['status'] = 'active' if instance_obj.task_completed else 'idle'
                    instance['model'] = instance_obj.model_name
                    instance['created_at'] = instance_obj.created_at
                    instance['message_count'] = len(instance_obj.history)
                    instance['connected_to'] = list(instance_obj.connected_instances.keys())
                    instance['outputs_count'] = len(instance_obj.outputs)
                    instance['last_active'] = time.time() - (0 if instance_obj.task_completed else 300)
                    instance['response_time_avg'] = 2.0  # Mock value - would track actual response times
                    
                    # Add last message info if available
                    if instance_obj.history:
                        instance['last_message'] = {
                            'text': instance_obj.history[-1]['text'][:100] + "..." if len(instance_obj.history[-1]['text']) > 100 else instance_obj.history[-1]['text'],
                            'timestamp': time.time()
                        }
                    
        # Add overall network stats
        total_instances = len(network.instances) + 1  # +1 for mother node
        active_instances = sum(1 for inst in network.instances.values() if inst.task_completed)
        total_messages = sum(len(inst.history) for inst in network.instances.values())
        if network.mother_node:
            total_messages += len(network.mother_node.history)
            
        result['stats'] = {
            'total_instances': total_instances,
            'active_instances': active_instances,
            'total_messages': total_messages,
            'network_created_at': network.mother_node.created_at if network.mother_node else 0,
            'network_uptime': time.time() - (network.mother_node.created_at if network.mother_node else time.time()),
            'completion_rate': (active_instances / total_instances) * 100 if total_instances > 0 else 0,
            'api_usage': {
                'total_calls': total_messages,
                'rate_limit': f"{RATE_LIMIT['max_calls']} per {RATE_LIMIT['period']}s",
                'current_usage': min(total_messages % RATE_LIMIT['max_calls'], RATE_LIMIT['max_calls'])
            }
        }
        
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

@app.route('/api/instance/<instance_id>', methods=['GET'])
@limiter.limit("100 per minute")
def get_instance_details(instance_id):
    if not network:
        return jsonify({'error': 'Network not initialized'}), 503
    
    try:
        # Check if it's the mother node
        if instance_id == "mother" and network.mother_node:
            details = {
                'id': network.mother_node.instance_id,
                'name': network.mother_node.name,
                'role': network.mother_node.role,
                'model': network.mother_node.model_name,
                'icon': get_node_icon(network.mother_node.role),
                'created_at': network.mother_node.created_at,
                'status': 'active',
                'connected_instances': list(network.mother_node.connected_instances.keys()),
                'history': [{'role': msg.get('role', 'system'), 'text': msg.get('text', '')} 
                            for msg in network.mother_node.history],
                'outputs': network.mother_node.outputs
            }
            return jsonify(details)
        
        # Check if it's a regular instance
        elif instance_id in network.instances:
            instance = network.instances[instance_id]
            details = {
                'id': instance.instance_id,
                'name': instance.name,
                'role': instance.role,
                'model': instance.model_name,
                'icon': get_node_icon(instance.role),
                'created_at': instance.created_at,
                'status': 'active' if instance.task_completed else 'idle',
                'connected_instances': list(instance.connected_instances.keys()),
                'history': [{'role': msg.get('role', 'system'), 'text': msg.get('text', '')} 
                            for msg in instance.history],
                'outputs': instance.outputs
            }
            return jsonify(details)
        
        else:
            return jsonify({'error': 'Instance not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting instance details: {str(e)}")
        return jsonify({'error': 'Failed to get instance details'}), 500

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

@app.route('/api/network/stats', methods=['GET'])
@limiter.limit("60 per minute")
def get_network_stats():
    """Get detailed network statistics including performance metrics."""
    if not network:
        return jsonify({'error': 'Network not initialized'}), 503
    
    try:
        # Calculate basic stats
        total_instances = len(network.instances) + 1  # +1 for mother node
        active_instances = sum(1 for inst in network.instances.values() if inst.task_completed)
        total_messages = sum(len(inst.history) for inst in network.instances.values())
        if network.mother_node:
            total_messages += len(network.mother_node.history)
            
        # Get role distribution
        role_distribution = {}
        for instance in network.instances.values():
            role = instance.role
            if role in role_distribution:
                role_distribution[role] += 1
            else:
                role_distribution[role] = 1
                
        # Add mother node role
        if network.mother_node:
            mother_role = network.mother_node.role
            if mother_role in role_distribution:
                role_distribution[mother_role] += 1
            else:
                role_distribution[mother_role] = 1
        
        # Calculate model usage
        model_usage = {}
        for instance in network.instances.values():
            model = instance.model_name
            if model in model_usage:
                model_usage[model] += 1
            else:
                model_usage[model] = 1
                
        # Add mother node model
        if network.mother_node:
            mother_model = network.mother_node.model_name
            if mother_model in model_usage:
                model_usage[mother_model] += 1
            else:
                model_usage[mother_model] = 1
                
        # Network topology data (connections between nodes)
        network_connections = []
        for instance_id, instance in network.instances.items():
            for connected_id in instance.connected_instances:
                network_connections.append({
                    'source': instance_id,
                    'target': connected_id
                })
                
        # Calculate uptime
        network_start_time = network.mother_node.created_at if network.mother_node else time.time()
        uptime_seconds = time.time() - network_start_time
        
        # Format uptime nicely
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_uptime = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        stats = {
            'general': {
                'total_instances': total_instances,
                'active_instances': active_instances,
                'total_messages': total_messages,
                'network_created_at': network_start_time,
                'uptime': formatted_uptime,
                'uptime_seconds': uptime_seconds,
                'completion_rate': round((active_instances / total_instances) * 100, 2) if total_instances > 0 else 0
            },
            'api_usage': {
                'total_calls': total_messages,
                'rate_limit': f"{RATE_LIMIT['max_calls']} per {RATE_LIMIT['period']}s",
                'current_usage': min(total_messages % RATE_LIMIT['max_calls'], RATE_LIMIT['max_calls']),
                'usage_percent': round((min(total_messages % RATE_LIMIT['max_calls'], RATE_LIMIT['max_calls']) / RATE_LIMIT['max_calls']) * 100, 2)
            },
            'distribution': {
                'roles': role_distribution,
                'models': model_usage
            },
            'network_graph': {
                'nodes': total_instances,
                'connections': len(network_connections),
                'connection_data': network_connections
            },
            'performance': {
                'avg_response_time': 2.3,  # Mock value - would calculate from actual timing data
                'instances_created_count': total_instances,
                'peak_concurrent_instances': total_instances,
                'message_throughput': round(total_messages / (uptime_seconds / 60), 2) if uptime_seconds > 0 else 0  # messages per minute
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting network stats: {str(e)}")
        return jsonify({'error': 'Failed to get network statistics'}), 500

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
    
    # Use the new asyncio API
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    background_thread = Thread(target=run_background_loop, args=(loop,))
    background_thread.daemon = True
    background_thread.start()
    
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
