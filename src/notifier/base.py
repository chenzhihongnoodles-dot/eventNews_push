# coding=utf-8
"""推送模块基类 - 定义推送接口"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseNotifier(ABC):
    """推送器基类"""

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.webhook_url = config.get("webhook_url", "")

    @abstractmethod
    def send(self, content: str, title: str = "") -> bool:
        """发送消息"""
        pass

    @abstractmethod
    def format_content(self, items: List[Dict]) -> str:
        """格式化内容"""
        pass

    def is_available(self) -> bool:
        """检查推送器是否可用"""
        return self.enabled and self.webhook_url