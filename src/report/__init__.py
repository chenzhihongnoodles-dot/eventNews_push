# coding=utf-8
"""报告生成模块"""

from .html_report import HTMLReportGenerator
from .api_generator import APIGenerator

__all__ = [
    "HTMLReportGenerator",
    "APIGenerator",
]
