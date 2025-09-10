#!/usr/bin/env python3
"""
Only-Test 播放状态检测器
==========================

负责检测Android设备的媒体播放状态
是动态策略切换的关键依据
"""

import asyncio
import subprocess
import logging
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """播放状态枚举"""
    IDLE = "idle"               # 空闲状态
    PLAYING = "playing"         # 正在播放
    PAUSED = "paused"           # 暂停状态
    BUFFERING = "buffering"     # 缓冲状态
    ERROR = "error"             # 错误状态
    UNKNOWN = "unknown"         # 未知状态


@dataclass
class MediaInfo:
    """媒体信息"""
    package_name: str
    state: PlaybackState
    session_active: bool
    audio_active: bool
    wake_lock_active: bool
    player_type: Optional[str] = None
    media_title: Optional[str] = None
    duration: Optional[int] = None
    position: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "package_name": self.package_name,
            "state": self.state.value,
            "session_active": self.session_active,
            "audio_active": self.audio_active,
            "wake_lock_active": self.wake_lock_active,
            "player_type": self.player_type,
            "media_title": self.media_title,
            "duration": self.duration,
            "position": self.position,
            "timestamp": datetime.now().isoformat()
        }


class PlaybackDetector:
    """
    播放状态检测器
    
    功能特性：
    1. 多维度检测：音频状态、媒体会话、唤醒锁等多重检测
    2. 应用感知：识别不同应用的播放状态
    3. 性能优化：缓存检测结果，避免频繁调用
    4. 准确性保证：多种检测方法互相验证
    """
    
    def __init__(self, cache_duration: int = 5):
        """
        初始化播放状态检测器
        
        Args:
            cache_duration: 缓存时长（秒）
        """
        self.device_id: Optional[str] = None
        self.cache_duration = cache_duration
        self._cached_state: Optional[MediaInfo] = None
        self._last_check_time: float = 0
        
        # 媒体应用包名列表（可扩展）
        self.media_packages = {
            "com.netflix.mediaclient", 
            "com.google.android.youtube",
            "com.amazon.avod.thirdpartyclient",
            "com.disney.disneyplus",
            "com.spotify.music",
            "com.tencent.qqlive",
            "com.youku.phone",
            "tv.danmaku.bili",
            "com.mobile.brasiltvmobile",  # TikTok
            # 添加更多媒体应用包名...
        }
        
        logger.info("播放状态检测器初始化完成")
    
    async def initialize(self, device_id: Optional[str] = None) -> bool:
        """
        初始化检测器
        
        Args:
            device_id: 设备ID
            
        Returns:
            bool: 初始化是否成功
        """
        self.device_id = device_id
        
        try:
            # 测试ADB连接
            await self._run_adb_command("shell echo 'test'")
            logger.info(f"播放状态检测器初始化成功 - 设备: {device_id or 'default'}")
            return True
        except Exception as e:
            logger.error(f"播放状态检测器初始化失败: {e}")
            return False
    
    async def is_media_playing(self, force_check: bool = False) -> bool:
        """
        检查是否正在播放媒体
        
        Args:
            force_check: 是否强制检查，忽略缓存
            
        Returns:
            bool: 是否正在播放
        """
        media_info = await self.get_media_info(force_check)
        return media_info.state == PlaybackState.PLAYING
    
    async def get_media_info(self, force_check: bool = False) -> MediaInfo:
        """
        获取详细的媒体播放信息
        
        Args:
            force_check: 是否强制检查，忽略缓存
            
        Returns:
            MediaInfo: 媒体信息
        """
        current_time = asyncio.get_event_loop().time()
        
        # 使用缓存
        if not force_check and self._cached_state:
            if current_time - self._last_check_time < self.cache_duration:
                return self._cached_state
        
        try:
            # 执行检测
            media_info = await self._detect_playback_state()
            
            # 更新缓存
            self._cached_state = media_info
            self._last_check_time = current_time
            
            return media_info
            
        except Exception as e:
            logger.error(f"获取媒体信息失败: {e}")
            return MediaInfo(
                package_name="",
                state=PlaybackState.ERROR,
                session_active=False,
                audio_active=False,
                wake_lock_active=False
            )
    
    async def get_active_media_apps(self) -> List[str]:
        """
        获取当前活跃的媒体应用列表
        
        Returns:
            List[str]: 活跃的媒体应用包名列表
        """
        try:
            # 获取正在运行的应用
            running_apps = await self._get_running_apps()
            
            # 过滤媒体应用
            active_media_apps = [
                app for app in running_apps 
                if app in self.media_packages
            ]
            
            return active_media_apps
            
        except Exception as e:
            logger.error(f"获取活跃媒体应用失败: {e}")
            return []
    
    async def is_audio_session_active(self) -> bool:
        """
        检查音频会话是否活跃
        
        Returns:
            bool: 音频会话是否活跃
        """
        try:
            # 使用dumpsys audio检查音频状态
            output = await self._run_adb_command("shell dumpsys audio")
            
            # 检查活跃的音频会话
            audio_patterns = [
                r"AudioFocus.*state=GAIN",
                r"MediaSession.*state=STATE_PLAYING",
                r"AudioPlaybackConfiguration.*STARTED"
            ]
            
            for pattern in audio_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"检查音频会话状态失败: {e}")
            return False
    
    async def detect_media_session_state(self) -> PlaybackState:
        """
        通过媒体会话检测播放状态
        
        Returns:
            PlaybackState: 播放状态
        """
        try:
            output = await self._run_adb_command("shell dumpsys media_session")
            
            # 解析媒体会话状态
            if "state=STATE_PLAYING" in output:
                return PlaybackState.PLAYING
            elif "state=STATE_PAUSED" in output:
                return PlaybackState.PAUSED
            elif "state=STATE_BUFFERING" in output:
                return PlaybackState.BUFFERING
            elif "state=STATE_ERROR" in output:
                return PlaybackState.ERROR
            else:
                return PlaybackState.IDLE
                
        except Exception as e:
            logger.warning(f"检测媒体会话状态失败: {e}")
            return PlaybackState.UNKNOWN
    
    async def is_wake_lock_active(self) -> bool:
        """
        检查是否有媒体相关的唤醒锁活跃
        
        Returns:
            bool: 是否有活跃的唤醒锁
        """
        try:
            output = await self._run_adb_command("shell dumpsys power")
            
            # 检查与媒体播放相关的唤醒锁
            wake_lock_patterns = [
                r"AudioMix.*PARTIAL_WAKE_LOCK",
                r"MediaPlayback.*PARTIAL_WAKE_LOCK",
                r"VideoView.*PARTIAL_WAKE_LOCK",
                r"ExoPlayer.*PARTIAL_WAKE_LOCK"
            ]
            
            for pattern in wake_lock_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"检查唤醒锁状态失败: {e}")
            return False
    
    def clear_cache(self) -> None:
        """清空检测缓存"""
        self._cached_state = None
        self._last_check_time = 0
        logger.debug("播放状态检测缓存已清空")
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        return {
            "cached_state": self._cached_state.to_dict() if self._cached_state else None,
            "last_check_time": self._last_check_time,
            "cache_duration": self.cache_duration,
            "device_id": self.device_id,
            "media_packages_count": len(self.media_packages)
        }
    
    # === 私有方法 ===
    
    async def _detect_playback_state(self) -> MediaInfo:
        """执行播放状态检测的核心逻辑"""
        
        # 1. 获取当前前台应用
        foreground_app = await self._get_foreground_app()
        
        # 2. 检查音频会话状态
        audio_active = await self.is_audio_session_active()
        
        # 3. 检查媒体会话状态
        session_state = await self.detect_media_session_state()
        
        # 4. 检查唤醒锁状态
        wake_lock_active = await self.is_wake_lock_active()
        
        # 5. 综合判断播放状态
        if session_state == PlaybackState.PLAYING:
            final_state = PlaybackState.PLAYING
        elif session_state in [PlaybackState.PAUSED, PlaybackState.BUFFERING]:
            final_state = session_state
        elif audio_active and wake_lock_active:
            final_state = PlaybackState.PLAYING
        elif session_state == PlaybackState.ERROR:
            final_state = PlaybackState.ERROR
        else:
            final_state = PlaybackState.IDLE
        
        return MediaInfo(
            package_name=foreground_app,
            state=final_state,
            session_active=session_state != PlaybackState.IDLE,
            audio_active=audio_active,
            wake_lock_active=wake_lock_active
        )
    
    async def _get_foreground_app(self) -> str:
        """获取当前前台应用包名"""
        try:
            # 使用dumpsys activity检查当前活动
            output = await self._run_adb_command("shell dumpsys activity activities | grep mResumedActivity")
            
            # 解析包名
            match = re.search(r"ActivityRecord\{.*?\s+(\S+)/", output)
            if match:
                return match.group(1)
            
            # 备用方法：使用dumpsys window
            output = await self._run_adb_command("shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'")
            
            match = re.search(r"(\w+\.\w+\.\w+)", output)
            if match:
                return match.group(1)
            
            return ""
            
        except Exception as e:
            logger.warning(f"获取前台应用失败: {e}")
            return ""
    
    async def _get_running_apps(self) -> List[str]:
        """获取正在运行的应用列表"""
        try:
            output = await self._run_adb_command("shell pm list packages")
            
            # 解析包名列表
            packages = []
            for line in output.split('\n'):
                if line.startswith('package:'):
                    package_name = line.replace('package:', '').strip()
                    packages.append(package_name)
            
            return packages
            
        except Exception as e:
            logger.error(f"获取运行应用列表失败: {e}")
            return []
    
    async def _run_adb_command(self, command: str) -> str:
        """执行ADB命令"""
        try:
            # 构建完整命令
            full_command = f"adb"
            if self.device_id:
                full_command += f" -s {self.device_id}"
            full_command += f" {command}"
            
            # 执行命令
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    full_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            )
            
            if result.returncode != 0:
                raise Exception(f"ADB命令执行失败: {result.stderr}")
            
            return result.stdout
            
        except Exception as e:
            logger.error(f"执行ADB命令失败 '{command}': {e}")
            raise