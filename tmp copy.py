import uiautomator2 as u2

def is_media_player_fullscreen(device_address=None, class_name="android.widget.VideoView"):
    """
    检查媒体播放器是否占据全屏。
    - device_address: 设备地址（如 'emulator-5554'），默认为 None（自动连接）。
    - class_name: 媒体播放器的 className（可自定义，如 'com.google.android.exoplayer2.ui.PlayerView'）。
    返回: True（全屏）或 False。
    """
    try:
        # 连接设备
        d = u2.connect(device_address) if device_address else u2.connect()
        
        # 获取屏幕尺寸
        screen_width, screen_height = d.window_size()
        
        # 查找媒体播放器元素
        player = d(className=class_name)
        if not player.exists:
            print("媒体播放器元素未找到。")
            return False
        
        # 获取元素的 bounds
        bounds = player.info.get('bounds', {})
        if not bounds:
            print("无法获取元素 bounds。")
            return False
        
        # 检查 bounds 是否覆盖整个屏幕
        is_full = (bounds.get('left', -1) == 0 and
                   bounds.get('top', -1) == 0 and
                   bounds.get('right', -1) == screen_width and
                   bounds.get('bottom', -1) == screen_height)
        
        return is_full
    
    except Exception as e:
        print(f"检测失败: {e}")
        return False

# 使用示例
result = is_media_player_fullscreen()  # 或指定 device_address='your_device_id'
print("是否全屏:", result)
