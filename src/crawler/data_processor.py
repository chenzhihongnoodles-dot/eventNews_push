# coding=utf-8
"""数据处理模块 - 处理和分析爬取的数据"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.utils.logger import logger


def clean_title(title: str) -> str:
    """清理标题，移除多余字符"""
    if not title:
        return ""
    
    # 移除首尾空白
    title = title.strip()
    
    # 移除常见的标题后缀
    suffixes = ["- 今日头条", "- 抖音", "- 微博", "- 腾讯新闻", "- 网易新闻", "| 新浪新闻"]
    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
    
    # 移除特殊字符
    title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\-\_\,\。\，\！\？\：\;\(\)\[\]\{\}《》【】]', '', title)
    
    # 移除多余空格
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title


def format_time_filename() -> str:
    """格式化时间为文件名格式"""
    from datetime import datetime
    return datetime.now().strftime("%H时%M分")


def format_date_folder() -> str:
    """格式化日期为文件夹名"""
    from datetime import datetime
    return datetime.now().strftime("%Y年%m月%d日")


def get_output_path(file_type: str, filename: str) -> str:
    """获取输出文件路径"""
    date_folder = format_date_folder()
    output_dir = Path("output") / date_folder / file_type
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir / filename)


def save_titles_to_file(results: Dict, id_to_name: Dict, failed_ids: List) -> str:
    """保存标题到文件"""
    file_path = get_output_path("txt", f"{format_time_filename()}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        for id_value, title_data in results.items():
            name = id_to_name.get(id_value)
            if name and name != id_value:
                f.write(f"{id_value} | {name}\n")
            else:
                f.write(f"{id_value}\n")

            sorted_titles = []
            for title, info in title_data.items():
                cleaned_title = clean_title(title)
                if isinstance(info, dict):
                    ranks = info.get("ranks", [])
                    url = info.get("url", "")
                    mobile_url = info.get("mobileUrl", "")
                else:
                    ranks = info if isinstance(info, list) else []
                    url = ""
                    mobile_url = ""

                rank = ranks[0] if ranks else 1
                sorted_titles.append((rank, cleaned_title, url, mobile_url))

            sorted_titles.sort(key=lambda x: x[0])

            for rank, cleaned_title, url, mobile_url in sorted_titles:
                line = f"{rank}. {cleaned_title}"

                if url:
                    line += f" [URL:{url}]"
                if mobile_url:
                    line += f" [MOBILE:{mobile_url}]"
                f.write(line + "\n")

            f.write("\n")

        if failed_ids:
            f.write("==== 以下ID请求失败 ====\n")
            for id_value in failed_ids:
                f.write(f"{id_value}\n")

    logger.info(f"标题已保存到: {file_path}")
    return file_path


def load_frequency_words(
        frequency_file: Optional[str] = None,
) -> Tuple[List[Dict], List[str]]:
    """加载频率词配置"""
    if frequency_file is None:
        frequency_file = os.environ.get(
            "FREQUENCY_WORDS_PATH", "config/frequency_words.txt"
        )

    frequency_path = Path(frequency_file)
    if not frequency_path.exists():
        raise FileNotFoundError(f"频率词文件 {frequency_file} 不存在")

    with open(frequency_path, "r", encoding="utf-8") as f:
        content = f.read()

    word_groups = [group.strip() for group in content.split("\n\n") if group.strip()]

    processed_groups = []
    filter_words = []

    for group in word_groups:
        words = [word.strip() for word in group.split("\n") if word.strip()]

        group_required_words = []
        group_normal_words = []
        group_filter_words = []

        for word in words:
            # 跳过注释行
            if word.startswith("#"):
                continue
            if word.startswith("!"):
                filter_words.append(word[1:])
                group_filter_words.append(word[1:])
            elif word.startswith("+"):
                group_required_words.append(word[1:])
            else:
                group_normal_words.append(word)

        if group_required_words or group_normal_words:
            if group_normal_words:
                group_key = " ".join(group_normal_words)
            else:
                group_key = " ".join(group_required_words)

            processed_groups.append(
                {
                    "required": group_required_words,
                    "normal": group_normal_words,
                    "group_key": group_key,
                }
            )

    return processed_groups, filter_words


def parse_file_titles(file_path: Path) -> Tuple[Dict, Dict]:
    """解析单个txt文件的标题数据"""
    titles_by_id = {}
    id_to_name = {}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        sections = content.split("\n\n")

        for section in sections:
            if not section.strip() or "==== 以下ID请求失败 ====" in section:
                continue

            lines = section.strip().split("\n")
            if len(lines) < 2:
                continue

            header_line = lines[0].strip()
            if " | " in header_line:
                parts = header_line.split(" | ", 1)
                source_id = parts[0].strip()
                name = parts[1].strip()
                id_to_name[source_id] = name
            else:
                source_id = header_line
                id_to_name[source_id] = source_id

            titles_by_id[source_id] = {}

            for line in lines[1:]:
                if line.strip():
                    try:
                        title_part = line.strip()
                        rank = None

                        if ". " in title_part and title_part.split(". ")[0].isdigit():
                            rank_str, title_part = title_part.split(". ", 1)
                            rank = int(rank_str)

                        mobile_url = ""
                        if " [MOBILE:" in title_part:
                            title_part, mobile_part = title_part.rsplit(" [MOBILE:", 1)
                            if mobile_part.endswith("]"):
                                mobile_url = mobile_part[:-1]

                        url = ""
                        if " [URL:" in title_part:
                            title_part, url_part = title_part.rsplit(" [URL:", 1)
                            if url_part.endswith("]"):
                                url = url_part[:-1]

                        title = clean_title(title_part.strip())
                        ranks = [rank] if rank is not None else [1]

                        titles_by_id[source_id][title] = {
                            "ranks": ranks,
                            "url": url,
                            "mobileUrl": mobile_url,
                        }

                    except Exception as e:
                        logger.error(f"解析标题行出错: {line}, 错误: {e}")

    return titles_by_id, id_to_name


def process_source_data(
        source_id: str,
        title_data: Dict,
        time_info: str,
        all_results: Dict,
        title_info: Dict,
):
    """处理单个来源的数据"""
    for title, info in title_data.items():
        if title not in all_results:
            all_results[title] = {
                "sources": [],
                "ranks": [],
                "urls": [],
                "mobileUrls": [],
            }

        all_results[title]["sources"].append(source_id)
        
        if isinstance(info, dict):
            all_results[title]["ranks"].extend(info.get("ranks", []))
            all_results[title]["urls"].append(info.get("url", ""))
            all_results[title]["mobileUrls"].append(info.get("mobileUrl", ""))
        else:
            all_results[title]["ranks"].append(info[0] if isinstance(info, list) else 1)
            all_results[title]["urls"].append("")
            all_results[title]["mobileUrls"].append("")

        if title not in title_info:
            title_info[title] = {
                "first_time": time_info,
                "last_time": time_info,
                "count": 0,
            }
        title_info[title]["last_time"] = time_info
        title_info[title]["count"] += 1


def read_all_today_titles(
        current_platform_ids: Optional[List[str]] = None,
) -> Tuple[Dict, Dict, Dict]:
    """读取当天所有标题文件"""
    date_folder = format_date_folder()
    txt_dir = Path("output") / date_folder / "txt"

    if not txt_dir.exists():
        return {}, {}, {}

    all_results = {}
    final_id_to_name = {}
    title_info = {}

    files = sorted([f for f in txt_dir.iterdir() if f.suffix == ".txt"])

    for file_path in files:
        titles_by_id, file_id_to_name = parse_file_titles(file_path)

        if current_platform_ids is not None:
            filtered_titles_by_id = {}
            filtered_id_to_name = {}

            for source_id, title_data in titles_by_id.items():
                if source_id in current_platform_ids:
                    filtered_titles_by_id[source_id] = title_data
                    if source_id in file_id_to_name:
                        filtered_id_to_name[source_id] = file_id_to_name[source_id]

            titles_by_id = filtered_titles_by_id
            file_id_to_name = filtered_id_to_name

        final_id_to_name.update(file_id_to_name)

        for source_id, title_data in titles_by_id.items():
            process_source_data(
                source_id, title_data, file_path.stem, all_results, title_info
            )

    return all_results, final_id_to_name, title_info