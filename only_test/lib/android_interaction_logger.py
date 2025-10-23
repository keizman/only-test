"""
Android 交互日志记录器

记录所有与 Android 设备的底层交互：
- Poco 命令
- Airtest 命令  
- ADB 命令

用于调试和分析执行流程。
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class AndroidInteractionLogger:
    """Android 交互日志记录器（线程安全）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._log_entries: List[Dict[str, Any]] = []
            self._log_file: Optional[Path] = None
            self._enabled = False
            self._write_lock = threading.Lock()
            # 广告检测日志
            self._ad_detection_entries: List[Dict[str, Any]] = []
            self._ad_detection_file: Optional[Path] = None
            self._ad_detection_round = 0
    
    def initialize(self, log_file: Path, ad_detection_file: Optional[Path] = None):
        """初始化日志文件路径"""
        with self._write_lock:
            self._log_file = log_file
            self._enabled = True
            self._log_entries = []
            # 创建空日志文件
            try:
                with open(self._log_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                logger.info(f"[ANDROID-LOG] Initialized: {log_file}, enabled={self._enabled}")
            except Exception as e:
                logger.error(f"Failed to initialize android interaction log: {e}")
                self._enabled = False
            
            # 初始化广告检测日志
            if ad_detection_file:
                self._ad_detection_file = ad_detection_file
                self._ad_detection_entries = []
                self._ad_detection_round = 0
                try:
                    with open(self._ad_detection_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                except Exception as e:
                    logger.error(f"Failed to initialize ad detection log: {e}")
    
    def log_interaction(
        self, 
        interaction_type: str,  # "poco" | "airtest" | "adb"
        command: str,
        parameters: Dict[str, Any],
        result: Any = None,
        error: str = None,
        device_id: str = None
    ):
        """记录一次 Android 交互"""
        if not self._enabled:
            logger.warning(f"[ANDROID-LOG] Logger not enabled! Call initialize_android_logger() first. Skipping {interaction_type}:{command}")
            return
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "command": command,
            "parameters": parameters,
            "device_id": device_id or "unknown"
        }
        
        if result is not None:
            entry["result"] = str(result)
        
        if error:
            entry["error"] = str(error)
            entry["success"] = False
        else:
            entry["success"] = True
        
        # 打印到命令行
        cmd_display = f"{interaction_type.upper()}: {command}({self._format_params(parameters)})"
        if error:
            logger.warning(f"[ANDROID] {cmd_display} -> ERROR: {error}")
        else:
            logger.info(f"[ANDROID] {cmd_display}")
        
        # 写入日志文件
        with self._write_lock:
            self._log_entries.append(entry)
            self._write_to_file()
    
    def _format_params(self, params: Dict[str, Any]) -> str:
        """格式化参数用于命令行显示"""
        if not params:
            return ""
        items = []
        for k, v in params.items():
            items.append(f"{k}={v}")
        return ", ".join(items)
    
    def _write_to_file(self):
        """写入日志文件（已持有锁）"""
        if not self._log_file:
            return
        
        try:
            with open(self._log_file, 'w', encoding='utf-8') as f:
                json.dump(self._log_entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to write android interaction log: {e}")
    
    def flush(self):
        """强制刷新日志到磁盘"""
        with self._write_lock:
            self._write_to_file()
    
    def disable(self):
        """禁用日志记录"""
        self._enabled = False
    
    def log_ad_detection(
        self,
        phase: str,  # "detection" | "closing" | "verification"
        confidence: float,
        ad_elements_count: int,
        close_elements_count: int,
        action_taken: str = None,  # "clicked" | "skipped" | "none"
        success: bool = True,
        details: str = None
    ):
        """记录广告检测流程"""
        if not self._ad_detection_file:
            return
        
        with self._write_lock:
            # 如果是新的检测轮次（phase=detection），增加轮次计数
            if phase == "detection":
                self._ad_detection_round += 1
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "detection_round": self._ad_detection_round,
                "phase": phase,
                "confidence": confidence,
                "detected": {
                    "ad_elements": ad_elements_count,
                    "close_elements": close_elements_count
                },
                "success": success
            }
            
            if action_taken:
                entry["action"] = action_taken
            
            if details:
                entry["details"] = details
            
            # 命令行打印
            action_str = f" -> {action_taken}" if action_taken else ""
            logger.info(f"[AD-DETECT] Round {self._ad_detection_round} | {phase} | conf={confidence:.2f} | ads={ad_elements_count} | closes={close_elements_count}{action_str}")
            
            self._ad_detection_entries.append(entry)
            
            # 写入文件
            try:
                with open(self._ad_detection_file, 'w', encoding='utf-8') as f:
                    json.dump(self._ad_detection_entries, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Failed to write ad detection log: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._write_lock:
            total = len(self._log_entries)
            by_type = {}
            errors = 0
            
            for entry in self._log_entries:
                t = entry.get('type', 'unknown')
                by_type[t] = by_type.get(t, 0) + 1
                if not entry.get('success', True):
                    errors += 1
            
            return {
                "total_interactions": total,
                "by_type": by_type,
                "errors": errors,
                "ad_detections": len(self._ad_detection_entries)
            }


# 全局单例
_logger = AndroidInteractionLogger()


def initialize_android_logger(log_file: Path, ad_detection_file: Optional[Path] = None):
    """初始化 Android 交互日志"""
    _logger.initialize(log_file, ad_detection_file)


def log_poco_interaction(command: str, **kwargs):
    """记录 Poco 交互"""
    _logger.log_interaction("poco", command, kwargs)


def log_airtest_interaction(command: str, **kwargs):
    """记录 Airtest 交互"""
    _logger.log_interaction("airtest", command, kwargs)


def log_adb_interaction(command: str, **kwargs):
    """记录 ADB 交互"""
    _logger.log_interaction("adb", command, kwargs)


def get_android_logger_stats() -> Dict[str, Any]:
    """获取 Android 交互日志统计"""
    return _logger.get_stats()


def log_ad_detection_event(phase: str, confidence: float, ad_count: int, close_count: int, **kwargs):
    """记录广告检测事件"""
    _logger.log_ad_detection(phase, confidence, ad_count, close_count, **kwargs)


def flush_android_logger():
    """刷新 Android 交互日志"""
    _logger.flush()

