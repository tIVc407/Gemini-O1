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
- **Advanced Rate Limiting**: Token bucket algorithm with exponential backoff for API calls
- **Health Monitoring**: System and API health checks with detailed status reporting
- **Structured Logging**: JSON-formatted logs with request ID tracking across instances
- **CI/CD Pipeline**: Automated testing, linting, and documentation generation

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
python main.py interactive

# Single query mode
python main.py query "Write a short story about robots"

# List instances
python main.py list
```

#### Web Interface

```bash
# Start the web server
python -m gemini_o1.ui.web_interface

# Access the interface at http://localhost:5000
```

## Project Structure

```
gemini_o1/
├── __init__.py         # Package initialization
├── models/             # Core data models
│   ├── __init__.py
│   ├── instance.py     # GeminiInstance class
│   └── network.py      # GeminiNetwork class
├── commands/           # Command parsing and handling
│   ├── __init__.py
│   ├── command_parser.py
│   └── command_handlers.py
├── communication/      # Communication between instances
│   ├── __init__.py
│   └── response.py
├── ui/                 # User interfaces
│   ├── __init__.py
│   ├── cli.py
│   └── web_interface.py
└── utils/              # Utility functions
    ├── __init__.py
    ├── config.py       # Configuration management
    ├── health_monitor.py # Health monitoring system
    ├── logging_config.py # Structured logging
    ├── prompts.py      # Prompt management
    ├── rate_limiter.py # Advanced rate limiting
    └── retry.py        # Retry decorator with backoff
```

## Web Interface Features

- **Chat Interface**: Interact with the AI network through a modern chat UI
- **Workflow Visualization**: See the network of instances and their connections
- **Instance Management**: View detailed information about each instance
- **Network Statistics**: Monitor performance metrics and usage statistics
- **Health Dashboard**: Monitor system health and API usage metrics

## API Endpoints

- **GET /api/instances**: List all active instances with details
- **POST /api/send_message**: Send a message to the network
- **GET /api/instance/<instance_id>**: Get detailed info about a specific instance
- **GET /api/network/stats**: Get comprehensive network statistics
- **POST /api/clear**: Clear all instances and history
- **GET /api/health**: Get basic health status of the system
- **GET /api/health/detailed**: Get detailed health information including metrics
- **GET /api/metrics**: Get performance metrics for API calls and system resources
- **GET /api/health/check/<check_name>**: Run a specific health check

## CI/CD Pipeline

The project includes GitHub Actions workflows for:

- **Continuous Integration**: Runs tests, linting, and code coverage on multiple Python versions
- **Documentation**: Automatically generates and publishes API documentation
- **Continuous Deployment**: Creates releases with versioned packages

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