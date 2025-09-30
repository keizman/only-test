#!/usr/bin/env python3
"""
Application Management Module
=============================

This module provides utilities for managing Android applications during testing.

Components:
- app_launcher: Unified application launching with configuration support
- ad_closer: Automatic advertisement detection and closing

Usage:
    from only_test.lib.app_management import app_launcher, ad_closer
    from only_test.lib.app_management.app_launcher import launch_app
"""

try:
    from . import app_launcher
    from . import ad_closer
    
    __all__ = ["app_launcher", "ad_closer"]
except ImportError:
    __all__ = []
