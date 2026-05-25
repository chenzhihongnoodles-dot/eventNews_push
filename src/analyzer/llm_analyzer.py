# coding=utf-8
"""大模型分析模块 - 使用AI分析活动策划创意"""

import json
import requests
from typing import Dict, List, Optional

from src.utils.logger import logger


class LLMContentAnalyzer:
    """使用大模型分析活动策划创意"""

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", False)
        self.provider = config.get("provider", "deepseek")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "deepseek-chat")
        self.max_tokens = config.get("max_tokens", 500)
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 30)

    def deduplicate_events(self, matched_items: List[Dict]) -> List[Dict]:
        """将相似标题归并为同一事件，去重后每个事件返回一条代表性条目
        matched_items: [{title, url, mobile_url, source, ranks}, ...]
        返回: 去重后的事件列表，相同事件的标题合并到 related_titles 字段
        """
        if len(matched_items) <= 1:
            for item in matched_items:
                item["related_titles"] = [item["title"]]
            return matched_items

        if not self.enabled or not self.api_key:
            return self._simple_deduplicate(matched_items)

        try:
            titles = [item["title"] for item in matched_items]
            prompt = self._build_dedup_prompt(titles)
            response = self._call_llm(prompt)
            groups = self._parse_dedup_response(response, len(titles))

            if not groups:
                return self._simple_deduplicate(matched_items)

            result = []
            for group_indices in groups:
                if not group_indices:
                    continue
                group_items = [matched_items[i] for i in group_indices if i < len(matched_items)]
                if not group_items:
                    continue
                main_item = group_items[0].copy()
                main_item["related_titles"] = [item["title"] for item in group_items]
                result.append(main_item)

            logger.info(f"事件去重: {len(matched_items)}条 -> {len(result)}个事件")
            return result

        except Exception as e:
            logger.error(f"事件去重失败: {e}")
            return self._simple_deduplicate(matched_items)

    def _build_dedup_prompt(self, titles: List[str]) -> str:
        title_list = "\n".join(f"{i}. {t}" for i, t in enumerate(titles))
        return f"""你是一个新闻事件去重专家。以下是从多个平台爬取的活动策划相关新闻标题。

请将报道同一事件的标题归为一组（如同一次发布会、同一场音乐节、同一个航天任务等算同一事件）。

标题列表：
{title_list}

请严格按照以下JSON格式输出分组结果，只输出JSON，不要其他内容：
{{"groups": [[0, 3, 7], [1, 5], [2], [4, 6]]}}

其中每个子数组是一组报道同一事件的标题索引。注意：
1. 所有标题都必须出现在某个分组中
2. 每个标题只能出现在一个分组中
3. 只有确实报道同一事件才归为一组
4. 仅返回JSON"""

    def _parse_dedup_response(self, response: str, total: int) -> List[List[int]]:
        try:
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[1]
                if response.endswith("```"):
                    response = response[:-3]
            data = json.loads(response)
            groups = data.get("groups", [])
            used_indices = set()
            valid_groups = []
            for group in groups:
                valid = [i for i in group if isinstance(i, int) and 0 <= i < total]
                if valid:
                    valid_groups.append(valid)
                    used_indices.update(valid)
            missing = set(range(total)) - used_indices
            for idx in missing:
                valid_groups.append([idx])
            return valid_groups
        except Exception:
            return []

    def _simple_deduplicate(self, matched_items: List[Dict]) -> List[Dict]:
        seen = set()
        result = []
        for item in matched_items:
            t = item["title"]
            if t not in seen:
                seen.add(t)
                item["related_titles"] = [t]
                result.append(item)
        return result

    def analyze_activity_creativity(self, title: str, content: str = "") -> Dict:
        """
        使用大模型分析活动策划的创意点
        返回: 分析结果字典
        """
        if not self.enabled or not self.api_key:
            return self._fallback_analysis(title, content)

        try:
            prompt = self._build_prompt(title, content)
            response = self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"大模型分析失败: {e}")
            return self._fallback_analysis(title, content)

    def _build_prompt(self, title: str, content: str) -> str:
        """构建分析提示词 - 针对活动策划公司的创意分析"""
        content_preview = content[:500] if content else ""

        prompt = f"""
你是一位资深的活动策划专家，专门为活动策划公司提供创意灵感和策划建议。

请分析以下活动相关新闻：

新闻标题：{title}
新闻内容预览：{content_preview}

请严格按照以下格式输出分析结果，每项内容单独一行：

是否相关：（回答"是"或"否"，判断这条新闻是否与活动策划创意相关，如发布会、展览、音乐节、体育赛事、庆典活动、展览展示等线下活动策划；不包括单纯的股市行情、政治新闻、娱乐八卦、体育比赛结果等非活动策划内容）
活动简要：（根据标题和内容，简要描述这个活动是什么、核心目的是什么，不要复述标题）
核心创意点：（这个活动最亮眼的创意是什么？）
可复用元素：（哪些策划手法可以复制到其他活动中？）
创新亮点：（相比传统活动，哪里做得更出色？）

注意：
1. 是否相关字段必须回答"是"或"否"
2. 如果回答"否"，其他字段可以为空或填"不适用"
3. 活动简要需要提供有价值的信息，不能只是重复标题
4. 使用中文回答，语言简洁专业
5. 每项内容控制在50字以内
"""
        return prompt.strip()

    def _call_llm(self, prompt: str) -> str:
        """调用大模型API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        if self.provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
        elif self.provider == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
        elif self.provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_tokens,
            }
            headers["x-api-key"] = self.api_key
            del headers["Authorization"]
        else:
            url = "https://api.openai.com/v1/chat/completions"

        response = requests.post(
            url, headers=headers, json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()

        if self.provider == "anthropic":
            return result["content"][0]["text"]
        else:
            return result["choices"][0]["message"]["content"]

    def _parse_response(self, response: str) -> Dict:
        """解析大模型响应"""
        result = {
            "is_relevant": False,           # 是否与活动策划创意相关
            "event_type": "未识别",
            "event_summary": "",           # 活动简要
            "core_creative": "",           # 核心创意点
            "reusable_elements": "",      # 可复用元素
            "innovation_highlights": "",  # 创新亮点
            "theme_positioning": "",      # 主题定位
            "interaction_design": "",     # 互动设计
            "communication_strategy": "", # 传播策略
            "suitable_industries": "",    # 适合行业
            "budget_suggestion": "",      # 预算建议
            "execution_difficulty": "",   # 执行难度
            "variant_schemes": "",        # 变体方案
            "analysis_source": "AI分析",
        }

        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            
            if "是否相关" in line:
                # 解析是否相关字段
                value = line.replace("是否相关：", "").replace("是否相关:", "").strip()
                result["is_relevant"] = value == "是"
            elif "活动简要" in line:
                result["event_summary"] = line.replace("活动简要：", "").replace("活动简要:", "").strip()
            elif "核心创意点" in line:
                result["core_creative"] = line.replace("核心创意点：", "").replace("核心创意点:", "").strip()
            elif "可复用元素" in line:
                result["reusable_elements"] = line.replace("可复用元素：", "").replace("可复用元素:", "").strip()
            elif "创新亮点" in line:
                result["innovation_highlights"] = line.replace("创新亮点：", "").replace("创新亮点:", "").strip()
            elif "主题定位" in line:
                result["theme_positioning"] = line.replace("主题定位：", "").replace("主题定位:", "").strip()
            elif "互动设计" in line:
                result["interaction_design"] = line.replace("互动设计：", "").replace("互动设计:", "").strip()
            elif "传播策略" in line:
                result["communication_strategy"] = line.replace("传播策略：", "").replace("传播策略:", "").strip()
            elif "适合行业" in line:
                result["suitable_industries"] = line.replace("适合行业：", "").replace("适合行业:", "").strip()
            elif "预算建议" in line:
                result["budget_suggestion"] = line.replace("预算建议：", "").replace("预算建议:", "").strip()
            elif "执行难度" in line:
                result["execution_difficulty"] = line.replace("执行难度：", "").replace("执行难度:", "").strip()
            elif "变体方案" in line:
                result["variant_schemes"] = line.replace("变体方案：", "").replace("变体方案:", "").strip()
            elif "活动类型" in line:
                result["event_type"] = line.replace("活动类型：", "").replace("活动类型:", "").strip()

        return result

    def _fallback_analysis(self, title: str, content: str) -> Dict:
        """降级分析（不使用大模型）"""
        return {
            "is_relevant": True,           # 降级模式默认保留
            "event_type": "未识别",
            "event_summary": title,
            "core_creative": "",
            "reusable_elements": "",
            "innovation_highlights": "",
            "theme_positioning": "",
            "interaction_design": "",
            "communication_strategy": "",
            "suitable_industries": "",
            "budget_suggestion": "",
            "execution_difficulty": "",
            "variant_schemes": "",
            "analysis_source": "降级模式",
        }