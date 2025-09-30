#!/usr/bin/env python3
"""
Only-Test Workflows Package
===========================

This package contains production-ready workflows for the Only-Test framework.
These are not examples or demos, but actual workflow implementations that can be
used in production environments.

Workflows include:
- LLM-driven test case generation workflows
- Complete end-to-end testing workflows
- MCP (Model Context Protocol) integration workflows

Usage:
    from only_test.workflows import llm_workflow_demo
    from only_test.workflows import complete_workflow_demo
"""

__version__ = "1.0.0"
__author__ = "Only-Test Team"

# Export main workflow functions
try:
    from .llm_workflow_demo import main as llm_workflow_main
    from .complete_workflow_demo import main as complete_workflow_main
    
    __all__ = [
        "llm_workflow_main",
        "complete_workflow_main"
    ]
except ImportError:
    # Allow partial imports if some dependencies are missing
    __all__ = []
