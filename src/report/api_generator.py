# coding=utf-8
"""API数据生成模块 - 生成JSON格式的API数据"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from src.crawler.data_processor import format_date_folder, get_output_path
from src.utils.logger import logger


class APIGenerator:
    """API数据生成器"""

    def generate(self, report_data: Dict) -> Dict:
        """生成API数据结构"""
        result = {
            "status": "success",
            "generated_at": datetime.now().isoformat(),
            "data": {
                "total_count": 0,
                "platforms": [],
                "news_items": [],
            }
        }

        total_count = 0
        
        for stat in report_data.get("stats", []):
            platform_id = stat.get("id", "")
            platform_name = stat.get("name", "")
            
            if platform_id not in result["data"]["platforms"]:
                result["data"]["platforms"].append({
                    "id": platform_id,
                    "name": platform_name,
                })
            
            for title_data in stat.get("titles", []):
                item = {
                    "title": title_data.get("title", ""),
                    "url": title_data.get("url", ""),
                    "mobile_url": title_data.get("mobile_url", ""),
                    "source": platform_name,
                    "source_id": platform_id,
                    "ranks": title_data.get("ranks", []),
                    "highlight": title_data.get("highlight", ""),
                }
                result["data"]["news_items"].append(item)
                total_count += 1
        
        result["data"]["total_count"] = total_count
        return result

    def save(self, report_data: Dict) -> str:
        """保存API数据到文件"""
        api_data = self.generate(report_data)
        file_path = "api/trends.json"
        
        # 确保目录存在
        Path("api").mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(api_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"API数据已保存到: {file_path}")
        return file_path