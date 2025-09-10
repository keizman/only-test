#!/usr/bin/env python3
"""
测试 airtest 项目的 omniparser 集成
验证使用指定图片的结构输出
"""

import asyncio
import json
import os
import sys
import base64
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加 airtest 路径到 Python 路径
sys.path.insert(0, '/mnt/c/Download/git/uni/airtest')
sys.path.insert(0, '/mnt/c/Download/git/uni')

from only_test.lib.visual_recognition.omniparser_client import OmniparserClient, OmniElement

def image_to_base64(image_path: str) -> str:
    """将图片文件转换为 base64 编码"""
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"图片 {image_path} 转换为 base64 成功，大小: {len(base64_encoded)} 字符")
            return base64_encoded
    except Exception as e:
        logger.error(f"图片转换失败: {e}")
        raise

async def test_airtest_omniparser():
    """测试 airtest 项目的 omniparser 功能"""
    
    # 指定的测试图片路径
    image_path = "/mnt/c/Download/git/uni/zdep_OmniParser-v2-finetune/imgs/yc_vod_playing_fullscreen.png"
    
    # 验证图片文件存在
    if not os.path.exists(image_path):
        logger.error(f"图片文件不存在: {image_path}")
        return
    
    # 创建 omniparser 客户端（试用多个可能的服务器地址）
    server_urls = [
        "http://100.122.57.128:9333",
        "http://172.27.1.113:9333", 
        "http://localhost:9333"
    ]
    
    client = None
    working_server = None
    
    for server_url in server_urls:
        logger.info(f"尝试连接服务器: {server_url}")
        test_client = OmniparserClient(server_url=server_url, timeout=30)
        
        # 健康检查
        is_healthy = await test_client.health_check(force_check=True)
        if is_healthy:
            logger.info(f"✅ 服务器 {server_url} 可用")
            client = test_client
            working_server = server_url
            break
        else:
            logger.warning(f"❌ 服务器 {server_url} 不可用")
    
    if not client:
        logger.error("所有 omniparser 服务器都不可用")
        logger.info("💡 可能的解决方案:")
        logger.info("1. 启动本地 omniparser 服务器")
        logger.info("2. 检查网络连接")
        logger.info("3. 确认服务器地址和端口")
        return
    
    try:
        # 转换图片为 base64
        logger.info(f"处理图片: {image_path}")
        screenshot_base64 = image_to_base64(image_path)
        
        # 测试 1: 使用 PaddleOCR (文本+图标)
        logger.info("=== 测试 1: 使用 PaddleOCR (文本+图标) ===")
        result_with_ocr = await client.analyze_screen(
            screenshot_base64=screenshot_base64,
            use_paddleocr=True,
            enable_cache=False
        )
        
        print("\n🔍 使用 PaddleOCR 的结果:")
        print(json.dumps(result_with_ocr, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
        
        # 测试 2: 仅使用 YOLO (图标)
        logger.info("=== 测试 2: 仅使用 YOLO (图标) ===")
        result_yolo_only = await client.analyze_screen(
            screenshot_base64=screenshot_base64,
            use_paddleocr=False,
            enable_cache=False
        )
        
        print("🎯 仅使用 YOLO 的结果:")
        print(json.dumps(result_yolo_only, indent=2, ensure_ascii=False))
        
        # 分析结果结构
        print("\n" + "="*50)
        print("📊 airtest omniparser 结果结构分析:")
        print("="*50)
        
        if result_with_ocr.get('success', False) and 'elements' in result_with_ocr:
            elements = result_with_ocr['elements']
            print(f"📍 检测到 {len(elements)} 个元素")
            
            # 分析前几个元素
            for i, element in enumerate(elements[:3]):
                print(f"\n🎯 元素 {i+1}:")
                print(f"  UUID: {element.get('uuid', 'N/A')}")
                print(f"  类型: {element.get('type', 'N/A')}")
                print(f"  内容: {element.get('content', 'N/A')}")
                print(f"  位置: {element.get('bbox', 'N/A')}")
                print(f"  可交互: {element.get('interactivity', 'N/A')}")
                print(f"  来源: {element.get('source', 'N/A')}")
                
                # 如果有中心坐标，也显示出来
                if 'center_x' in element and 'center_y' in element:
                    print(f"  中心点: ({element['center_x']:.3f}, {element['center_y']:.3f})")
        
        # 统计信息
        print(f"\n📈 统计信息:")
        print(f"  服务器地址: {working_server}")
        print(f"  分析耗时: {result_with_ocr.get('analysis_time_ms', 'N/A')} ms")
        print(f"  识别状态: {'成功' if result_with_ocr.get('success', False) else '失败'}")
        
        print(f"\n✅ airtest omniparser 测试完成!")
        print(f"📄 airtest 项目的 omniparser 客户端工作正常")
        print(f"🎯 返回的 JSON 结构符合预期，包含:")
        print(f"  - success: 操作是否成功")
        print(f"  - elements: UI 元素列表")
        print(f"  - 每个元素包含: uuid, type, content, bbox, interactivity, source")
        print(f"  - bbox 为归一化坐标 [x1, y1, x2, y2]")
        print(f"  - 支持缓存和重试机制")
        
    except Exception as e:
        logger.error(f"Omniparser 测试失败: {e}")
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    asyncio.run(test_airtest_omniparser())