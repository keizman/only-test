# coding=utf-8
"""
Verify tmp.poco_v1 UIAutomator2 driver on a real device.

Usage:
  python verify_device_uia2_tmp_poco_v1.py 192.168.100.112:5555

Checks:
 - Connects via UIAutomator2
 - Dumps hierarchy via tmp.poco_v1 driver
 - Verifies dump structure and package info preservation
 - Prints a concise summary compatible with UIAutomator1 expectations
"""
import sys
import json

def count_total_nodes(node):
    if not isinstance(node, dict):
        return 0
    c = 1
    for child in node.get('children', []) or []:
        c += count_total_nodes(child)
    return c

def count_nodes_with_package(node):
    if not isinstance(node, dict):
        return 0
    c = 1 if node.get('payload', {}).get('package') else 0
    for child in node.get('children', []) or []:
        c += count_nodes_with_package(child)
    return c

def main(device_id):
    print('Connecting to device:', device_id)

    # Import our refactored tmp.poco_v1 UIA2-backed driver
    # Note: a top-level tmp.py file exists, so we create a synthetic 'tmp' package
    # that points to the tmp/ directory to avoid name collision.
    import sys as _sys, types as _types, os as _os
    # Ensure Poco package is importable (used by tmp.poco_v1)
    poco_root = _os.path.join(_os.path.dirname(__file__), 'Poco')
    if poco_root not in _sys.path:
        _sys.path.insert(0, poco_root)
    if 'tmp' not in _sys.modules:
        tmp_pkg = _types.ModuleType('tmp')
        tmp_pkg.__path__ = [_os.path.join(_os.path.dirname(__file__), 'tmp')]
        tmp_pkg.__package__ = 'tmp'
        _sys.modules['tmp'] = tmp_pkg

    from tmp.poco_v1.drivers.android.uiautomation import AndroidUiautomationPoco

    # Initialize poco (UIAutomator2 backend)
    poco = AndroidUiautomationPoco(device_id=device_id, force_restart=False)
    info = poco.get_device_info()
    print('Device info:', json.dumps({
        'brand': info.get('brand'),
        'model': info.get('model'),
        'displayWidth': info.get('displayWidth'),
        'displayHeight': info.get('displayHeight'),
    }, ensure_ascii=False))

    print('Dumping hierarchy...')
    data = poco.agent.hierarchy.dump()
    if not isinstance(data, dict):
        print('✗ Dump failed or invalid type:', type(data))
        return 2

    # Basic shape checks (UIA1-compatible)
    missing = [k for k in ('name', 'payload', 'children') if k not in data]
    if missing:
        print('✗ Dump missing keys:', missing)
        return 3

    total = count_total_nodes(data)
    with_pkg = count_nodes_with_package(data)
    print('Total nodes:', total)
    print('Nodes with package:', with_pkg)
    if with_pkg == 0:
        print('✗ No package info found (incompatible with UIA1 expectations)')
        return 4

    # Sample a few attributes from first child (if exists)
    first_child = (data.get('children') or [None])[0]
    if isinstance(first_child, dict):
        p = first_child.get('payload', {})
        sample = {
            'name': first_child.get('name'),
            'type': p.get('type'),
            'text': p.get('text'),
            'resourceId': p.get('resourceId'),
            'package': p.get('package'),
            'bounds': p.get('bounds'),
        }
        print('Sample first child payload:', json.dumps(sample, ensure_ascii=False))

    print('✓ Verification passed: dump structure and package info preserved (UIA1-compatible).')
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python verify_device_uia2_tmp_poco_v1.py <device_id>')
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
