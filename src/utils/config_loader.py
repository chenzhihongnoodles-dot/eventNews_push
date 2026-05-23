# coding=utf-8
"""配置加载模块 - 支持YAML配置和环境变量覆盖"""

import os
import yaml
from typing import Dict, Any, Optional

class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            # 应用环境变量覆盖
            self._apply_env_overrides()
        except FileNotFoundError:
            print(f"警告: 配置文件 {self.config_path} 未找到")
        except Exception as e:
            print(f"配置加载失败: {e}")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖配置"""
        # LLM API Key
        if os.environ.get("DEEPSEEK_API_KEY"):
            self.config["llm"]["api_key"] = os.environ["DEEPSEEK_API_KEY"]
        
        # 企业微信Webhook
        if os.environ.get("WEWORK_WEBHOOK_URL"):
            self.config["webhooks"]["wework_url"] = os.environ["WEWORK_WEBHOOK_URL"]
        
        # Bing API Key
        if os.environ.get("BING_API_KEY"):
            self.config["enrichment"]["search_engines"]["bing_api_key"] = os.environ["BING_API_KEY"]
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔路径"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_llm_config(self) -> Dict:
        """获取LLM配置"""
        return self.config.get("llm", {})
    
    def get_webhook_config(self) -> Dict:
        """获取Webhook配置"""
        # webhooks 可能在根级别或 notification 下面
        return self.config.get("webhooks", {}) or self.config.get("notification", {}).get("webhooks", {})
    
    def get_enrichment_config(self) -> Dict:
        """获取信息扩充配置"""
        return self.config.get("enrichment", {})
    
    def get_push_config(self) -> Dict:
        """获取推送配置"""
        return self.config.get("push", {})
    
    def get_crawler_config(self) -> Dict:
        """获取爬虫配置"""
        return self.config.get("crawler", {})

# 全局配置实例
CONFIG = None

def init_config(config_path: str = "config/config.yaml") -> ConfigLoader:
    """初始化全局配置"""
    global CONFIG
    CONFIG = ConfigLoader(config_path)
    return CONFIG

def get_config() -> ConfigLoader:
    """获取全局配置实例"""
    if CONFIG is None:
        init_config()
    return CONFIG