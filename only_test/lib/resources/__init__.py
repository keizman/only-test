#!/usr/bin/env python3
"""
Resources Management Module
===========================

This module provides utilities for managing test resources and reporting.

Components:
- assets_manager: Test asset and resource management
- reporting: Test execution reporting and result management

Usage:
    from only_test.lib.resources import assets_manager, reporting
    from only_test.lib.resources.assets_manager import AssetsManager
"""

try:
    from . import assets_manager
    from . import reporting
    
    __all__ = ["assets_manager", "reporting"]
except ImportError:
    __all__ = []
