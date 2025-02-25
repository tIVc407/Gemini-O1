# Gemini-O1

## An Enhanced Multi-Agent Network Using Gemini API

Gemini-O1 is a powerful multi-agent system that leverages Google's Gemini API to create a network of specialized AI instances that can collaborate on complex tasks.

## Key Features

- **Multi-agent Architecture**: Create specialized AI instances to tackle complex problems
- **Scrum Master Node**: A mother node coordinates tasks and synthesizes responses
- **Asynchronous Processing**: Efficient handling of multiple parallel AI instances
- **Command-based Communication**: Structured command language for agent interaction
- **Multiple Interfaces**: CLI and Web interfaces with visualization tools
- **Real-time Monitoring**: Track instance status, history, and network statistics

## Getting Started

### Prerequisites

- Python 3.9+
- Google Gemini API key

### Installation

1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root with your API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

### Usage

#### Command Line Interface

```bash
# Interactive mode
python beep.py interactive

# Single query mode
python beep.py query "Write a short story about robots"

# List instances
python beep.py list
```

#### Web Interface

```bash
# Start the web server
python web_interface.py

# Access the interface at http://localhost:5000
```

## Project Structure

- **beep.py**: Core implementation with GeminiNetwork and GeminiInstance classes
- **config_file.py**: Configuration settings for models, API, and rate limits
- **utils_file.py**: Utility functions and rate limiting implementation
- **web_interface.py**: Flask web server with REST API endpoints
- **static/**: Web interface files (HTML, CSS, JavaScript)
- **examples/**: Example client implementations and visualizations

## Web Interface Features

- **Chat Interface**: Interact with the AI network through a modern chat UI
- **Workflow Visualization**: See the network of instances and their connections
- **Instance Management**: View detailed information about each instance
- **Network Statistics**: Monitor performance metrics and usage statistics

## API Endpoints

- **GET /api/instances**: List all active instances with details
- **POST /api/send_message**: Send a message to the network
- **GET /api/instance/<instance_id>**: Get detailed info about a specific instance
- **GET /api/network/stats**: Get comprehensive network statistics
- **POST /api/clear**: Clear all instances and history

## Examples

### Test Client

Run the test client to see the CLI in action:

```bash
python examples/test_client.py run-tests
```

### Network Visualization

Open `examples/network_visualization.html` in a browser to see an interactive network visualization.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Google Gemini API
- Flask and D3.js for the web interface
- All contributors