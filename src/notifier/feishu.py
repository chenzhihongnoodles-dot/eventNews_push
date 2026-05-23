# coding=utf-8
"""飞书推送模块"""

import json
from typing import Dict, List

import requests

from src.notifier.base import BaseNotifier
from src.utils.logger import logger


class FeishuNotifier(BaseNotifier):
    """飞书推送器"""

    def __init__(self, config: Dict):
        super().__init__(config)

    def send(self, content: str, title: str = "") -> bool:
        """发送消息到飞书"""
        if not self.is_available():
            logger.warning("飞书推送不可用")
            return False

        try:
            payload = {
                "msg_type": "markdown",
                "content": {
                    "title": title or "TrendRadar 推送",
                    "text": content
                }
            }
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
                return True
            else:
                logger.error(f"飞书发送失败: {result.get('msg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"飞书发送异常: {e}")
            return False

    def format_content(self, items: List[Dict]) -> str:
        """格式化内容为飞书Markdown格式"""
        lines = []
        
        for item in items:
            lines.append(f"## 📌 {item.get('title', '')}")
            lines.append("")
            
            event_summary = item.get("event_summary", "")
            if event_summary:
                lines.append(f"- **活动简要**：{event_summary}")
            
            creative_text = item.get("creative_text", "")
            if creative_text:
                lines.append(f"- **创意与亮点**：{creative_text}")
            
            reusable_elements = item.get("reusable_elements", "")
            if reusable_elements:
                lines.append(f"- **可复用元素**：{reusable_elements}")
            
            url = item.get("url", "")
            if url:
                lines.append(f"- **原文链接**：[点击查看]({url})")
            
            lines.append("")

        return "\n".join(lines)