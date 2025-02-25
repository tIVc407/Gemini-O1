"""
Web interface for the Gemini-O1 application.

This module provides a Flask-based web interface for interacting with the
Gemini network, including API endpoints and static file serving.
"""

import os
import logging
import json
import asyncio
import uuid
import time
from threading import Thread
from queue import Queue
from typing import Dict, Any, List

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..models.network import GeminiNetwork
from ..utils.logging_config import logging_config
from ..utils.health_monitor import health_monitor
from ..utils.rate_limiter import rate_limiter

# Configure logging
logger = logging_config.get_logger(__name__)

class WebInterface:
    """
    Web interface for the Gemini-O1 application.
    """
    
    def __init__(self, host='0.0.0.0', port=5000):
        """
        Initialize the web interface.
        
        Args:
            host: The host to bind to
            port: The port to bind to
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__, static_folder='../../static')
        CORS(self.app)
        
        # Initialize rate limiter
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=["30 per minute", "1 per second"]
        )
        
        # Communication queue for bridging sync and async
        self.queue = Queue()
        self.results = {}
        
        # Set up event loop for async operations
        self.loop = asyncio.new_event_loop()
        self.worker_thread = Thread(target=self._run_async_loop, daemon=True)
        self.worker_thread.start()
        
        # Register routes
        self._register_routes()
        
    def _register_routes(self):
        """Register Flask routes."""
        
        @self.app.route('/')
        def index():
            return send_from_directory(self.app.static_folder, 'index.html')
            
        @self.app.route('/<path:path>')
        def static_files(path):
            return send_from_directory(self.app.static_folder, path)
            
        @self.app.route('/api/instances', methods=['GET'])
        @self.limiter.limit("10 per minute")
        def get_instances():
            result_id = self._queue_task('list_instances')
            return jsonify(self._wait_for_result(result_id))
            
        @self.app.route('/api/send_message', methods=['POST'])
        @self.limiter.limit("15 per minute")
        def send_message():
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({'error': 'No message provided'}), 400
                
            result_id = self._queue_task('handle_user_input', data['message'])
            return jsonify({'response': self._wait_for_result(result_id)})
            
        @self.app.route('/api/instance/<instance_id>', methods=['GET'])
        def get_instance_details(instance_id):
            result_id = self._queue_task('get_instance_details', instance_id)
            result = self._wait_for_result(result_id)
            
            if not result:
                return jsonify({'error': 'Instance not found'}), 404
                
            return jsonify(result)
            
        @self.app.route('/api/network/stats', methods=['GET'])
        def get_network_stats():
            result_id = self._queue_task('get_network_stats')
            return jsonify(self._wait_for_result(result_id))
            
        @self.app.route('/api/clear', methods=['POST'])
        def clear_network():
            result_id = self._queue_task('clear_network')
            return jsonify({'success': self._wait_for_result(result_id)})
            
        @self.app.route('/uploads/<path:filename>')
        def uploaded_file(filename):
            return send_from_directory('../../uploads', filename)
            
        # Health monitoring endpoints
        @self.app.route('/api/health', methods=['GET'])
        def get_health():
            return jsonify(health_monitor.get_health_status())
            
        @self.app.route('/api/health/detailed', methods=['GET'])
        def get_detailed_health():
            return Response(
                health_monitor.get_health_json(),
                mimetype='application/json'
            )
            
        @self.app.route('/api/metrics', methods=['GET'])
        def get_metrics():
            # Combine different metrics sources
            metrics = {
                'api_calls': rate_limiter.get_call_metrics(),
                'system_resources': health_monitor._get_system_metrics(),
                'network_stats': self._queue_task('get_network_stats'),
            }
            return jsonify(metrics)
            
        @self.app.route('/api/health/check/<check_name>', methods=['GET'])
        def run_health_check(check_name):
            if check_name not in health_monitor.checks:
                return jsonify({'error': f'Health check {check_name} not found'}), 404
                
            result_id = self._queue_task('run_health_check', check_name)
            return jsonify(self._wait_for_result(result_id))
            
        @self.app.errorhandler(429)
        def ratelimit_handler(e):
            return jsonify({'error': f'Rate limit exceeded: {e.description}'}), 429
            
    def _queue_task(self, task_name, *args):
        """
        Queue an async task to be executed.
        
        Args:
            task_name: The name of the task to execute
            *args: Arguments to pass to the task
            
        Returns:
            A unique ID for the task result
        """
        result_id = str(uuid.uuid4())
        self.queue.put((result_id, task_name, args))
        return result_id
        
    def _wait_for_result(self, result_id, timeout=30):
        """
        Wait for a task result.
        
        Args:
            result_id: The ID of the task result
            timeout: Maximum time to wait in seconds
            
        Returns:
            The task result
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if result_id in self.results:
                result = self.results[result_id]
                del self.results[result_id]
                return result
            time.sleep(0.1)
        return {'error': 'Operation timed out'}
        
    def _run_async_loop(self):
        """Run the async event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._process_queue())
        
    async def _process_queue(self):
        """Process tasks from the queue."""
        # Create the network instance
        self.network = GeminiNetwork()
        await self.network._initialize_mother_node()
        
        # Start health monitoring
        health_monitor.start()
        
        while True:
            try:
                result_id, task_name, args = self.queue.get()
                
                if task_name == 'handle_user_input':
                    result = await self.network.handle_user_input(*args)
                elif task_name == 'list_instances':
                    result = await self.network.list_instances()
                elif task_name == 'get_instance_details':
                    instance_id = args[0]
                    if instance_id in self.network.instances:
                        result = self.network.instances[instance_id].get_status()
                    else:
                        result = None
                elif task_name == 'get_network_stats':
                    result = {
                        'instance_count': len(self.network.instances),
                        'total_messages': sum(len(inst.history) for inst in self.network.instances.values()),
                        'mother_node_status': 'active' if self.network.mother_node else 'inactive',
                        'uptime': time.time() - self.network.mother_node.created_at if self.network.mother_node else 0
                    }
                elif task_name == 'clear_network':
                    await self.network.cleanup_old_instances(max_age_hours=0)
                    result = True
                elif task_name == 'run_health_check':
                    check_name = args[0]
                    if check_name in health_monitor.checks:
                        result = await health_monitor.checks[check_name].run()
                    else:
                        result = {'error': f'Health check {check_name} not found'}
                else:
                    result = {'error': f'Unknown task: {task_name}'}
                    
                self.results[result_id] = result
                
            except Exception as e:
                logger.error(f"Error processing task {task_name}: {e}")
                self.results[result_id] = {'error': str(e)}
                
    def start(self):
        """Start the web interface."""
        self.app.run(host=self.host, port=self.port)


def run_web_interface():
    """Run the web interface."""
    import time
    
    logging_config.setup_logging(
        level=logging.INFO,
        log_file='app.log',
        enable_console=True,
        enable_request_tracking=True,
        enable_structured_logging=True
    )
    
    logger.info("Starting Gemini-O1 Web Interface")
    
    # Configure rate limiter
    rate_limiter.configure_endpoint("gemini_api", 15, 1/4, 5)  # 15 calls per minute
    rate_limiter.configure_endpoint("embeddings_api", 60, 1, 3)  # 60 calls per minute
    
    web = WebInterface()
    web.start()


if __name__ == '__main__':
    run_web_interface()