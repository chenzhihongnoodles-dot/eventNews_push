# coding=utf-8
"""企业微信推送模块"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import requests

from src.analyzer.enrichment import ActivityEnrichmentPipeline
from src.analyzer.llm_analyzer import LLMContentAnalyzer
from src.crawler.data_processor import clean_title
from src.notifier.base import BaseNotifier
from src.utils.config_loader import get_config
from src.utils.logger import logger


class WeWorkNotifier(BaseNotifier):
    """企业微信推送器"""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.message_batch_size = config.get("message_batch_size", 4000)

    def send(self, content: str, title: str = "") -> bool:
        """发送消息到企业微信"""
        if not self.is_available():
            logger.warning("企业微信推送不可用")
            return False

        try:
            payload = {"msgtype": "markdown", "markdown": {"content": content}}
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("企业微信消息发送成功")
                return True
            else:
                logger.error(f"企业微信发送失败: {result.get('errmsg', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"企业微信发送异常: {e}")
            return False

    def format_content(self, items: List[Dict]) -> str:
        """格式化内容为企业微信Markdown格式"""
        lines = []
        
        for item in items:
            lines.append("")
            lines.append("")
            lines.append("📌 " + clean_title(item.get("title", "")))
            lines.append("")
            lines.append("")
            
            # 活动简要
            event_summary = item.get("event_summary", "")
            if event_summary:
                lines.append("**· 活动简要：**" + event_summary)
            else:
                lines.append("**· 活动简要：**" + clean_title(item.get("title", "")))
            lines.append("")
            
            # 创意与亮点
            creative_text = item.get("creative_text", "")
            if creative_text:
                lines.append("**· 创意与亮点：**" + creative_text)
                lines.append("")
            
            # 可复用元素
            reusable_elements = item.get("reusable_elements", "")
            if reusable_elements:
                lines.append("**· 可复用元素：**" + reusable_elements)
                lines.append("")
            
            # 原文链接
            url = item.get("url", "")
            if url and not url.startswith("javascript"):
                lines.append("· 原文链接: [点击查看]({url})".format(url=url))
            lines.append("")
            lines.append("")

        return "\n".join(lines)

    def send_deduped_events(self, deduped_events: List[Dict], all_results: Dict,
                           analyzer: LLMContentAnalyzer) -> bool:
        """发送已去重的事件列表（关键词过滤+事件去重已在main.py完成）"""
        config = get_config()

        enrichment_pipeline = None
        enrichment_config = config.get("enrichment", {})
        if enrichment_config.get("enabled", False):
            enrichment_pipeline = ActivityEnrichmentPipeline(
                config=enrichment_config,
                llm_analyzer=analyzer
            )

        content_lines = []
        filtered_count = 0  # 被过滤掉的数量
        
        for event in deduped_events:
            title = event.get("title", "")
            url = event.get("mobile_url") or event.get("url", "")
            source = event.get("source", "未知")
            related_titles = event.get("related_titles", [title])

            # 信息扩充：合并多来源标题作为搜索上下文
            enriched_content = ""
            if enrichment_pipeline:
                search_text = " ".join(related_titles[:3])
                enriched_info = enrichment_pipeline.enrich_activity_info(
                    search_text, url, source, all_results
                )
                if enriched_info:
                    enriched_content = enriched_info.get("summary", "") + " " + \
                        " ".join(enriched_info.get("sources", []))

            # 大模型创意分析
            analysis = analyzer.analyze_activity_creativity(title, enriched_content)
            
            # 过滤：只保留与活动策划创意相关的内容
            is_relevant = analysis.get('is_relevant', True)
            if not is_relevant:
                logger.info(f"过滤无关内容: {title[:30]}...")
                filtered_count += 1
                continue

            # 格式化输出
            lines = []
            lines.append("")
            lines.append("")
            lines.append("📌 **" + clean_title(title) + "**")
            lines.append("")
            lines.append("")

            event_summary = analysis.get('event_summary', '')
            if event_summary and event_summary != '不适用':
                lines.append("· **活动简要：**" + event_summary)
            else:
                lines.append("· **活动简要：**" + clean_title(title))
            lines.append("")

            core_creative = analysis.get('core_creative', '')
            innovation_highlights = analysis.get('innovation_highlights', '')
            if core_creative or innovation_highlights:
                creative_text = ""
                if core_creative and core_creative != '不适用':
                    creative_text += core_creative
                if innovation_highlights and innovation_highlights != '不适用':
                    if creative_text:
                        creative_text += (" " if creative_text else "") + innovation_highlights
                    else:
                        creative_text = innovation_highlights
                if creative_text and creative_text != '不适用':
                    lines.append("· **创意与亮点：**" + creative_text)
                    lines.append("")

            reusable_elements = analysis.get('reusable_elements', '')
            if reusable_elements and reusable_elements != '不适用':
                lines.append("· **可复用元素：**" + reusable_elements)
                lines.append("")

            lines.append("")
            lines.append("")

            content_lines.append("\n".join(lines))
        
        # 添加头部
        if content_lines:
            header = f"📊 **今日活动创意灵感**（共 {len(content_lines)} 条）"
            if filtered_count > 0:
                header += f"，已过滤 {filtered_count} 条无关内容"
            content_lines.insert(0, header + "\n\n")
        else:
            content_lines = ["📭 今日暂无匹配的活动策划相关新闻"]

        # 添加尾部
        now = datetime.now()
        content_lines.append(f"\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 合并为单条发送
        full_content = "\n".join(content_lines)
        logger.info(f"企业微信消息大小: {len(full_content.encode('utf-8'))} 字节")
        return self.send(full_content)

    def send_report(self, report_data: Dict, all_results: Optional[Dict] = None, 
                   id_to_name: Optional[Dict] = None) -> bool:
        """发送完整报告"""
        # 创建大模型分析器
        config = get_config()
        llm_config = config.get("llm", {})
        analyzer = LLMContentAnalyzer(llm_config)

        # 创建活动信息扩充管道
        enrichment_pipeline = None
        enrichment_config = config.get("enrichment", {})
        if enrichment_config.get("enabled", False):
            enrichment_pipeline = ActivityEnrichmentPipeline(
                config=enrichment_config,
                llm_analyzer=analyzer
            )

        # 加载频率词过滤
        frequency_words = []
        try:
            from src.crawler.data_processor import load_frequency_words
            word_groups, filter_words = load_frequency_words()
            # 提取所有关键词
            for group in word_groups:
                frequency_words.extend(group.get("required", []))
                frequency_words.extend(group.get("normal", []))
        except:
            pass

        # 构建创意分析内容
        content_lines = []
        total_news = 0

        for stat in report_data.get("stats", []):
            for title_data in stat.get("titles", []):
                title = title_data.get("title", "")
                url = title_data.get("mobile_url") or title_data.get("url", "")
                source = title_data.get("source", "未知")

                # 频率词过滤
                if frequency_words:
                    matched = False
                    for word in frequency_words:
                        if word in title:
                            matched = True
                            break
                    if not matched:
                        continue  # 跳过不匹配的新闻

                # 先进行信息扩充
                enriched_content = ""
                if enrichment_pipeline:
                    enriched_info = enrichment_pipeline.enrich_activity_info(
                        title, url, source, all_results
                    )
                    if enriched_info:
                        enriched_content = enriched_info.get("summary", "") + " " + \
                            " ".join(enriched_info.get("sources", []))

                # 使用大模型分析
                analysis = analyzer.analyze_activity_creativity(title, enriched_content)

                # 格式化输出
                lines = []
                lines.append("")
                lines.append("")
                lines.append("📌 " + clean_title(title))
                lines.append("")
                lines.append("")
                
                # 活动简要
                event_summary = analysis.get('event_summary', '')
                if event_summary:
                    lines.append("· **活动简要：**" + event_summary)
                else:
                    lines.append("· **活动简要：**" + clean_title(title))
                lines.append("")
                
                # 创意与亮点
                core_creative = analysis.get('core_creative', '')
                innovation_highlights = analysis.get('innovation_highlights', '')
                if core_creative or innovation_highlights:
                    creative_text = ""
                    if core_creative:
                        creative_text += core_creative
                    if innovation_highlights:
                        if creative_text:
                            creative_text += " " + innovation_highlights
                        else:
                            creative_text = innovation_highlights
                    lines.append("· **创意与亮点：**" + creative_text)
                    lines.append("")
                
                # 可复用元素
                reusable_elements = analysis.get('reusable_elements', '')
                if reusable_elements:
                    lines.append("· **可复用元素：**" + reusable_elements)
                    lines.append("")
                
                # 原文链接
                if url and not url.startswith("javascript"):
                    lines.append("· 原文链接: [点击查看]({url})".format(url=url))
                lines.append("")
                lines.append("")

                content_lines.append("\n".join(lines))
                total_news += 1

        # 添加头部
        if total_news > 0:
            content_lines.insert(0, f"📊 **今日活动创意灵感**（共 {total_news} 条）\n\n")
        else:
            content_lines = ["📭 今日暂无匹配的活动策划相关新闻"]

        # 添加尾部
        now = datetime.now()
        content_lines.append(f"\n> 更新时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 分批处理
        batches = self._split_into_batches(content_lines)

        logger.info(f"企业微信消息分为 {len(batches)} 批次发送")

        # 逐批发送
        success = True
        for i, batch_content in enumerate(batches, 1):
            if len(batches) > 1:
                batch_header = f"**[第 {i}/{len(batches)} 批次]**\n\n"
                batch_content = batch_header + batch_content
            
            if not self.send(batch_content):
                success = False

        return success

    def _split_into_batches(self, content_lines: List[str]) -> List[str]:
        """将内容分割为多个批次"""
        batches = []
        current_batch = ""

        for line in content_lines:
            test_content = current_batch + line
            if len(test_content.encode("utf-8")) >= self.message_batch_size and current_batch:
                batches.append(current_batch)
                current_batch = line
            else:
                current_batch = test_content
        
        if current_batch:
            batches.append(current_batch)

        return batches