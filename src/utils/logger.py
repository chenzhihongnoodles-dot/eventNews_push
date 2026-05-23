# coding=utf-8
"""日志模块 - 统一日志管理"""

import logging
import os
from datetime import datetime

class Logger:
    """日志管理器"""
    
    def __init__(self, name: str = "TrendRadar", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            self._configure_handlers()
    
    def _configure_handlers(self):
        """配置日志处理器"""
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件handler - 按日期分割
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """错误日志"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str):
        """严重错误日志"""
        self.logger.critical(message)

# 全局日志实例
logger = Logger()

def get_logger(name: str = "TrendRadar") -> Logger:
    """获取日志实例"""
    return Logger(name)