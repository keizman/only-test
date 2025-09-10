#!/usr/bin/env python3
"""
OmniParser/XML 结果归一化
将不同来源的元素数据统一为：
{
  uuid, text, resource_id, content_desc, clickable,
  bounds, package, class_name, source
}
其中 bounds 为像素 [l,t,r,b]，同时支持从 bbox_norm 或 coordinates 推导。
"""

import hashlib
from typing import Dict, Any, List, Optional


def _hash_uuid(payload: str) -> str:
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()[:8]


def _to_bounds_px_from_bbox_norm(bbox: List[float], w: int, h: int) -> List[int]:
    if not bbox or len(bbox) != 4:
        return []
    return [int(bbox[0]*w), int(bbox[1]*h), int(bbox[2]*w), int(bbox[3]*h)]


def _to_bounds_px_from_coordinates(coords: Dict[str, Any]) -> List[int]:
    try:
        x, y = int(coords.get('x', 0)), int(coords.get('y', 0))
        width, height = int(coords.get('width', 0)), int(coords.get('height', 0))
        return [x, y, x+width, y+height]
    except Exception:
        return []


def normalize_visual_elements(result: Dict[str, Any], screen_w: int, screen_h: int) -> List[Dict[str, Any]]:
    elements = []
    for e in result.get('elements', []):
        uuid = e.get('uuid')
        content = e.get('content') or e.get('text') or ''
        interactivity = e.get('interactivity')
        if interactivity is None:
            interactivity = bool(e.get('interactive', False))
        class_name = e.get('type', 'visual_element')

        # bounds 优先从 bbox，其次 coordinates
        bounds = []
        if isinstance(e.get('bbox'), list):
            bounds = _to_bounds_px_from_bbox_norm(e['bbox'], screen_w, screen_h)
        elif isinstance(e.get('coordinates'), dict):
            bounds = _to_bounds_px_from_coordinates(e['coordinates'])

        if not uuid:
            payload = f"{class_name}|{content}|{bounds}"
            uuid = _hash_uuid(payload)

        elements.append({
            'uuid': uuid,
            'text': content,
            'resource_id': '',
            'content_desc': content,
            'clickable': interactivity,
            'bounds': bounds,
            'package': e.get('package', ''),
            'class_name': class_name,
            'source': 'omniparser'
        })
    return elements

