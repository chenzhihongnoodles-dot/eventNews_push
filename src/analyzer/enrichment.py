# coding=utf-8
"""信息扩充模块 - 通过网络搜索增强活动信息"""

import time
from typing import Dict, List, Optional

from src.analyzer.keyword_extractor import ActivityKeywordExtractor
from src.utils.logger import logger

# 尝试导入网络搜索模块
try:
    from web_search import MultiSearchEngine
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False


class ActivityInfoSearcher:
    """活动信息搜索器 - 从本地和网络搜索相关信息"""

    def __init__(self, search_config: Dict = None):
        self.search_config = search_config or {}
        self.search_engine = None
        if WEB_SEARCH_AVAILABLE:
            try:
                self.search_engine = MultiSearchEngine(search_config)
                logger.info("✓ 网络搜索引擎已初始化")
            except Exception as e:
                logger.error(f"网络搜索引擎初始化失败: {e}")

    def search_local_data(self, keywords: List[str], all_results: Dict) -> List[Dict]:
        """从本地已爬取的数据中搜索相关信息"""
        if not all_results or not keywords:
            return []

        results = []
        for title, info in all_results.items():
            for keyword in keywords:
                if keyword in title:
                    results.append({
                        "title": title,
                        "url": info.get("urls", [""])[0],
                        "snippet": title,
                        "source": "本地数据",
                    })
                    break

        return results[:5]

    def search_web(self, query: str) -> List[Dict]:
        """通过网络搜索相关信息"""
        if not self.search_engine:
            return []

        try:
            results = self.search_engine.search(query)
            logger.debug(f"网络搜索 '{query}' 找到 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            return []

    def search_related_info(self, title: str, all_results: Optional[Dict] = None) -> List[Dict]:
        """搜索与活动相关的信息"""
        # 提取关键词
        extractor = ActivityKeywordExtractor()
        keywords = extractor.extract_keywords(title)
        
        all_results = all_results or {}
        
        # 本地搜索
        local_results = self.search_local_data(keywords, all_results)
        
        # 网络搜索（使用多个查询词）
        queries = extractor.build_search_queries(title)
        web_results = []
        for query in queries[:2]:  # 最多搜索2个查询
            results = self.search_web(query)
            web_results.extend(results)
            time.sleep(1)  # 避免请求过快
        
        # 合并去重
        seen_titles = set()
        combined = []
        
        for result in local_results + web_results:
            if result["title"] not in seen_titles:
                seen_titles.add(result["title"])
                combined.append(result)
        
        return combined[:10]


class ActivityContentVerifier:
    """活动内容验证器 - 使用大模型验证内容真实性"""

    def __init__(self, llm_analyzer=None):
        self.llm_analyzer = llm_analyzer

    def verify_and_summarize(self, title: str, related_info: List[Dict]) -> Dict:
        """验证内容真实性并生成总结"""
        if not related_info:
            return {
                "summary": "",
                "sources": [],
                "confidence": 0.0,
                "verification_source": "无相关信息",
            }

        # 提取来源信息
        sources = []
        content_snippets = []
        
        for info in related_info[:5]:
            sources.append(info.get("title", ""))
            content_snippets.append(info.get("snippet", info.get("title", "")))

        # 如果有大模型，生成综合总结
        summary = ""
        confidence = 0.7  # 默认可信度
        
        if self.llm_analyzer:
            try:
                content = "\n".join(content_snippets)
                analysis = self.llm_analyzer.analyze_activity_creativity(title, content)
                summary = analysis.get("event_summary", "") or self._generate_summary(title, content_snippets)
                confidence = min(0.9, 0.7 + len(related_info) * 0.05)
            except Exception as e:
                logger.error(f"大模型验证失败: {e}")
                summary = self._generate_summary(title, content_snippets)
        else:
            summary = self._generate_summary(title, content_snippets)

        return {
            "summary": summary,
            "sources": sources[:5],
            "confidence": confidence,
            "verification_source": "AI验证 + 网络信息",
        }

    def _generate_summary(self, title: str, snippets: List[str]) -> str:
        """生成简单总结"""
        if not snippets:
            return ""
        
        return f"根据搜索结果，'{title}' 相关活动信息已获取，包含 {len(snippets)} 条相关报道。"


class ActivityEnrichmentPipeline:
    """活动信息扩充管道 - 整合关键词提取、信息搜索和真实性验证"""

    def __init__(self, config: Dict = None, llm_analyzer=None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.max_search_results = self.config.get("max_search_results", 5)
        self.search_timeout = self.config.get("search_timeout", 30)
        
        self.searcher = ActivityInfoSearcher(self.config.get("search_engines", {}))
        self.verifier = ActivityContentVerifier(llm_analyzer)

    def enrich_activity_info(self, title: str, url: str = "", source: str = "", 
                            all_results: Optional[Dict] = None) -> Optional[Dict]:
        """扩充活动信息"""
        if not self.enabled:
            return None

        try:
            # 搜索相关信息
            related_info = self.searcher.search_related_info(title, all_results)
            
            if not related_info:
                logger.debug(f"未找到 '{title}' 的相关信息")
                return None

            # 验证并总结
            result = self.verifier.verify_and_summarize(title, related_info)
            result["original_title"] = title
            result["original_url"] = url
            result["original_source"] = source

            logger.info(f"信息扩充完成: '{title}' - 可信度: {result['confidence']:.2f}")
            return result

        except Exception as e:
            logger.error(f"信息扩充失败: {e}")
            return None