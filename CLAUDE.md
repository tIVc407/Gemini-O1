# Gemini-O1 Development Guide

## Commands
- **Run Web Interface**: `python -m gemini_o1.ui.web_interface`
- **Run CLI**: `python main.py interactive`
- **Single Query**: `python main.py query "Your query here"`
- **Run Tests**: `pytest -v`
- **Run Single Test**: `pytest -xvs test_gemini_o1.py::TestGeminiNetwork::test_instance_creation`
- **Test with Coverage**: `pytest --cov=gemini_o1 --cov-report=term`
- **Lint Code**: `pylint gemini_o1/`
- **Build Documentation**: `cd docs && sphinx-build -b html . _build/html`
- **Run Simple Test**: `python test_simple.py`

## Code Style Guidelines
- **Imports**: Standard library first, third-party second, local modules last, all alphabetically sorted
- **Type Hints**: Use Python's typing module for all function signatures and class attributes
- **Naming**: PEP8 style - snake_case for functions/variables, CamelCase for classes
- **Documentation**: Docstrings for classes and important functions
- **Error Handling**: Use try/except with explicit error types, utilize retry_on_exception decorator for API calls
- **Async Pattern**: Use asyncio and async/await for all I/O operations
- **Formatting**: 4-space indentation, 100 character line limit
- **Classes**: Use dataclasses for data containers, instance methods for behavior
- **Logging**: Use the logging module with appropriate log levels (DEBUG, INFO, WARNING, ERROR)

## Development Roadmap

### Phase 1 (Completed)
- ✅ Implement structured logging with request IDs for tracking multi-instance operations
- ✅ Move API key management to environment variables with proper validation
- ✅ Add basic unit tests for web interface components
- ✅ Refactor codebase into modular package structure

### Phase 2 (Completed)
- ✅ Create CI/CD pipeline with automated testing
- ✅ Implement advanced rate limiting with exponential backoff strategies
- ✅ Add health monitoring and basic performance metrics
- ✅ Add documentation framework with Sphinx

### Phase 3 (Next Steps)
- Implement results caching system for repeated queries
- Add comprehensive error handling for network failures
- Improve instance coordination and message passing with better error recovery
- Implement distributed deployment support