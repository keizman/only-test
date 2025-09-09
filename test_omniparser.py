#!/usr/bin/env python3
"""
测试 omniparser 输出结果
验证使用指定图片的结构输出
"""

import asyncio
import json
import os
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加 phone-use 路径到 Python 路径
sys.path.insert(0, '/mnt/c/Download/git/uni/phone-use')

from phone_mcp.tools.omniparser_interface import OmniparserClient

async def test_omniparser_with_image():
    """测试 omniparser 分析指定图片"""
    
    # 指定的测试图片路径
    image_path = "/mnt/c/Download/git/uni/zdep_OmniParser-v2-finetune/imgs/yc_vod_playing_fullscreen.png"
    
    # 验证图片文件存在
    if not os.path.exists(image_path):
        logger.error(f"图片文件不存在: {image_path}")
        return
    
    # 创建 omniparser 客户端
    logger.info("创建 Omniparser 客户端...")
    client = OmniparserClient(server_url="http://100.122.57.128:9333")
    
    # 健康检查
    logger.info("检查 Omniparser 服务器状态...")
    is_healthy = await client.health_check()
    if not is_healthy:
        logger.warning("Omniparser 服务器可能不可用，继续尝试...")
    
    try:
        # 测试图片分析
        logger.info(f"分析图片: {image_path}")
        
        # 测试 1: 使用 PaddleOCR
        logger.info("=== 测试 1: 使用 PaddleOCR (文本+图标) ===")
        result_with_ocr = await client.parse_screen_file(image_path, use_paddleocr=True)
        
        print("🔍 使用 PaddleOCR 的结果:")
        print(json.dumps(result_with_ocr, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
        
        # 测试 2: 仅使用 YOLO
        logger.info("=== 测试 2: 仅使用 YOLO (图标) ===")
        result_yolo_only = await client.parse_screen_file(image_path, use_paddleocr=False)
        
        print("🎯 仅使用 YOLO 的结果:")
        print(json.dumps(result_yolo_only, indent=2, ensure_ascii=False))
        
        # 分析结果结构
        print("\n" + "="*50)
        print("📊 结果结构分析:")
        print("="*50)
        
        if 'elements' in result_with_ocr:
            elements = result_with_ocr['elements']
            print(f"📍 检测到 {len(elements)} 个元素")
            
            for i, element in enumerate(elements[:3]):  # 显示前3个元素作为示例
                print(f"\n🎯 元素 {i+1}:")
                print(f"  UUID: {element.get('uuid', 'N/A')}")
                print(f"  类型: {element.get('type', 'N/A')}")
                print(f"  内容: {element.get('content', 'N/A')}")
                print(f"  位置: {element.get('bbox', 'N/A')}")
                print(f"  可交互: {element.get('interactivity', 'N/A')}")
        
        print(f"\n✅ omniparser 测试完成!")
        print(f"📄 结果已保存，可以看到返回的 JSON 结构包含:")
        print(f"  - elements: UI 元素列表")
        print(f"  - 每个元素包含: uuid, type, content, bbox, interactivity")
        print(f"  - bbox 为归一化坐标 [x1, y1, x2, y2]")
        
    except Exception as e:
        logger.error(f"Omniparser 测试失败: {e}")
        print(f"❌ 错误: {e}")
        
        # 提供备用方案建议
        print("\n💡 可能的解决方案:")
        print("1. 检查 Omniparser 服务器是否运行在 http://100.122.57.128:9333")
        print("2. 检查网络连接")
        print("3. 尝试其他服务器地址 (如 http://172.27.1.113:9333)")

if __name__ == "__main__":
    asyncio.run(test_omniparser_with_image())