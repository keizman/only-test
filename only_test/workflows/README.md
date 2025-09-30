# Only-Test Workflows

This directory contains production-ready workflows for the Only-Test framework. These are complete, functional workflows that demonstrate and implement the core capabilities of the framework.

## Available Workflows

### 1. LLM Workflow Demo (`llm_workflow_demo.py`)
**Purpose**: Demonstrates LLM-driven test case generation using MCP (Model Context Protocol)

**Features**:
- Natural language requirement input
- LLM-powered JSON test case generation
- Automatic Python code generation
- Real LLM integration with fallback to mock LLM

**Usage**:
```bash
cd only_test/workflows
python llm_workflow_demo.py --requirement "Test login functionality" --app "com.example.app"
```

### 2. Complete Workflow Demo (`complete_workflow_demo.py`)
**Purpose**: End-to-end workflow demonstration including device interaction

**Features**:
- Device connection and setup
- Test execution with real device interaction
- Result collection and reporting
- Error handling and recovery

**Usage**:
```bash
cd only_test/workflows
python complete_workflow_demo.py --device-id "your_device_id"
```

## Workflow Architecture

```
User Input (Natural Language)
        ↓
MCP Server (Tool Registry)
        ↓
LLM Client (OpenAI/Anthropic/etc)
        ↓
JSON Test Case Generation
        ↓
Python Code Generation
        ↓
Device Execution
        ↓
Results & Reports
```

## Configuration

Workflows use the unified configuration system:
- `config/device_config.yaml` - Device settings
- `config/framework_config.yaml` - Framework behavior
- `testcases/main.yaml` - Test suite configuration

## Dependencies

- Python 3.8+
- Only-Test framework
- LLM API keys (for real LLM integration)
- Android device with ADB enabled

## Development

To create new workflows:

1. Follow the existing pattern in `llm_workflow_demo.py`
2. Use the MCP interface for LLM communication
3. Leverage the unified configuration system
4. Include proper error handling and logging
5. Add comprehensive documentation

## Integration

These workflows can be:
- Run standalone for testing and development
- Integrated into CI/CD pipelines
- Called from other Python scripts
- Executed via command line interfaces

## Notes

- These are **production workflows**, not examples or demos
- Each workflow is self-contained and can run independently
- All workflows follow the Only-Test framework conventions
- Proper logging and error handling is implemented throughout
