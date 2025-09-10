#!/usr/bin/env python3
"""
Only-Test 识别策略管理器
==========================

负责智能选择和管理元素识别策略
根据播放状态、界面复杂度等因素自动选择最佳策略
"""

import logging
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class RecognitionStrategy(Enum):
    """元素识别策略枚举"""
    XML_ONLY = "xml_only"           # 仅使用XML模式（快速，适用于静态界面）
    VISUAL_ONLY = "visual_only"     # 仅使用视觉模式（准确，适用于播放状态）
    HYBRID = "hybrid"               # 混合模式（先XML后视觉，平衡性能和准确性）
    AUTO = "auto"                   # 自动选择模式（根据上下文智能选择）
    
    @classmethod
    def from_string(cls, value: str) -> 'RecognitionStrategy':
        """从字符串安全地创建枚举实例，支持多种格式"""
        if isinstance(value, cls):
            return value
            
        # 尝试直接匹配枚举值
        try:
            return cls(value.lower())
        except ValueError:
            pass
            
        # 尝试匹配枚举名称
        value_upper = value.upper()
        for strategy in cls:
            if strategy.name == value_upper:
                return strategy
                
        # 如果都失败，抛出更友好的错误信息
        valid_values = [s.value for s in cls] + [s.name for s in cls]
        raise ValueError(f"Invalid strategy '{value}'. Valid values: {valid_values}")


@dataclass
class StrategyDecision:
    """策略决策结果"""
    strategy: RecognitionStrategy
    reason: str
    confidence: float  # 0.0-1.0
    factors: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategy": self.strategy.value,
            "reason": self.reason,
            "confidence": self.confidence,
            "factors": self.factors,
            "timestamp": datetime.now().isoformat()
        }


class StrategyManager:
    """
    识别策略管理器
    
    核心功能：
    1. 智能策略选择：根据多种因素自动选择最佳识别策略
    2. 性能监控：跟踪各策略的成功率和执行时间
    3. 自适应调整：根据历史表现动态调整策略选择偏好
    4. 决策透明化：提供策略选择的详细理由和信心度
    """
    
    def __init__(self):
        """初始化策略管理器"""
        self._omniparser_available = False
        self._strategy_performance: Dict[str, Dict[str, float]] = {}
        self._decision_history: list = []
        
        # 策略选择权重配置
        self._strategy_weights = {
            "is_playing": 0.4,      # 播放状态的权重
            "omni_available": 0.3,  # Omniparser可用性权重
            "performance": 0.2,     # 历史性能权重
            "complexity": 0.1       # 界面复杂度权重
        }
        
        logger.info("策略管理器初始化完成")
    
    def set_omniparser_available(self, available: bool) -> None:
        """设置Omniparser可用性状态"""
        self._omniparser_available = available
        logger.info(f"Omniparser可用性更新: {available}")
    
    def select_strategy(self, 
                       is_playing: bool = False,
                       omniparser_available: Optional[bool] = None,
                       interface_complexity: Optional[str] = None) -> RecognitionStrategy:
        """
        选择最佳识别策略
        
        Args:
            is_playing: 是否正在播放媒体
            omniparser_available: Omniparser是否可用（None则使用缓存状态）
            interface_complexity: 界面复杂度 ("simple", "medium", "complex")
            
        Returns:
            RecognitionStrategy: 选定的策略
        """
        # 更新Omniparser可用性
        if omniparser_available is not None:
            self._omniparser_available = omniparser_available
        
        # 进行策略决策
        decision = self._make_strategy_decision(is_playing, interface_complexity)
        
        # 记录决策历史
        self._record_decision(decision)
        
        logger.info(f"策略选择: {decision.strategy.value} (信心度: {decision.confidence:.2f}) - {decision.reason}")
        
        return decision.strategy
    
    def record_strategy_performance(self, 
                                  strategy: RecognitionStrategy,
                                  success: bool,
                                  execution_time: float) -> None:
        """
        记录策略执行性能
        
        Args:
            strategy: 使用的策略
            success: 是否成功
            execution_time: 执行时间（秒）
        """
        strategy_name = strategy.value
        
        if strategy_name not in self._strategy_performance:
            self._strategy_performance[strategy_name] = {
                "success_count": 0,
                "total_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "success_rate": 0.0
            }
        
        perf = self._strategy_performance[strategy_name]
        
        # 更新统计
        perf["total_count"] += 1
        perf["total_time"] += execution_time
        perf["avg_time"] = perf["total_time"] / perf["total_count"]
        
        if success:
            perf["success_count"] += 1
        
        perf["success_rate"] = perf["success_count"] / perf["total_count"]
        
        logger.debug(f"策略性能更新 {strategy_name}: 成功率 {perf['success_rate']:.2f}, 平均耗时 {perf['avg_time']:.2f}s")
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """
        获取策略使用统计
        
        Returns:
            Dict: 策略统计信息
        """
        return {
            "performance": self._strategy_performance.copy(),
            "recent_decisions": self._decision_history[-10:],  # 最近10个决策
            "omniparser_available": self._omniparser_available,
            "weights": self._strategy_weights.copy(),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_recommended_strategy(self, context: Dict[str, Any]) -> StrategyDecision:
        """
        基于上下文推荐策略（用于外部查询，不记录决策）
        
        Args:
            context: 上下文信息
            
        Returns:
            StrategyDecision: 推荐的策略决策
        """
        is_playing = context.get("is_playing", False)
        complexity = context.get("interface_complexity", None)
        
        return self._make_strategy_decision(is_playing, complexity)
    
    # === 私有方法 ===
    
    def _make_strategy_decision(self, 
                              is_playing: bool,
                              interface_complexity: Optional[str] = None) -> StrategyDecision:
        """执行策略决策逻辑"""
        
        factors = {
            "is_playing": is_playing,
            "omniparser_available": self._omniparser_available,
            "interface_complexity": interface_complexity,
            "has_performance_data": len(self._strategy_performance) > 0
        }
        
        # 决策逻辑
        
        # 1. 如果正在播放且Omniparser可用，优先视觉识别
        if is_playing and self._omniparser_available:
            return StrategyDecision(
                strategy=RecognitionStrategy.VISUAL_ONLY,
                reason="播放状态下XML无法访问控件，使用视觉识别",
                confidence=0.9,
                factors=factors
            )
        
        # 2. 如果正在播放但Omniparser不可用，尝试混合模式
        if is_playing and not self._omniparser_available:
            return StrategyDecision(
                strategy=RecognitionStrategy.XML_ONLY,
                reason="播放状态但视觉识别不可用，使用XML模式（可能失败）",
                confidence=0.3,
                factors=factors
            )
        
        # 3. 如果Omniparser不可用，只能使用XML
        if not self._omniparser_available:
            return StrategyDecision(
                strategy=RecognitionStrategy.XML_ONLY,
                reason="视觉识别不可用，使用XML模式",
                confidence=0.7,
                factors=factors
            )
        
        # 4. 如果界面复杂度较高，使用混合模式
        if interface_complexity == "complex":
            return StrategyDecision(
                strategy=RecognitionStrategy.HYBRID,
                reason="界面复杂，使用混合模式提高准确性",
                confidence=0.8,
                factors=factors
            )
        
        # 5. 基于历史性能选择策略
        if self._strategy_performance:
            best_strategy = self._select_best_performing_strategy()
            if best_strategy:
                return StrategyDecision(
                    strategy=best_strategy,
                    reason="基于历史性能选择最佳策略",
                    confidence=0.7,
                    factors=factors
                )
        
        # 6. 默认策略：混合模式（平衡性能和准确性）
        return StrategyDecision(
            strategy=RecognitionStrategy.HYBRID,
            reason="默认策略，平衡性能和准确性",
            confidence=0.6,
            factors=factors
        )
    
    def _select_best_performing_strategy(self) -> Optional[RecognitionStrategy]:
        """基于历史性能选择最佳策略"""
        best_strategy = None
        best_score = 0.0
        
        for strategy_name, perf in self._strategy_performance.items():
            # 综合评分：成功率 * 0.7 + (1 / 平均时间) * 0.3
            # 成功率越高越好，执行时间越短越好
            if perf["total_count"] >= 3:  # 至少有3次执行记录
                time_score = min(1.0, 1.0 / max(0.1, perf["avg_time"]))  # 时间评分
                score = perf["success_rate"] * 0.7 + time_score * 0.3
                
                if score > best_score:
                    best_score = score
                    try:
                        best_strategy = RecognitionStrategy.from_string(strategy_name)
                    except ValueError:
                        continue
        
        return best_strategy
    
    def _record_decision(self, decision: StrategyDecision) -> None:
        """记录策略决策"""
        self._decision_history.append(decision.to_dict())
        
        # 保持历史记录在合理范围内
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-50:]  # 保留最近50个决策
    
    def _calculate_interface_complexity(self, elements_count: int) -> str:
        """基于元素数量评估界面复杂度"""
        if elements_count <= 10:
            return "simple"
        elif elements_count <= 30:
            return "medium"
        else:
            return "complex"