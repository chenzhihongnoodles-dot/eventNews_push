# coding=utf-8
"""活动信息扩充模块 - 搜索同活动相关信息，验证真实性并总结"""

import re
import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# 导入分词工具
try:
    import jieba
    import jieba.posseg as pseg
    jieba.initialize()
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("警告: jieba 分词库未安装，将使用简单模式")

# 导入网络搜索模块
try:
    from web_search import MultiSearchEngine, BingSearchAPI, DuckDuckGoSearch, BaiduSearch, BAIDU_SEARCH_AVAILABLE
    WEB_SEARCH_AVAILABLE = True
    if BAIDU_SEARCH_AVAILABLE:
        print("✓ 百度搜索库已就绪")
except ImportError as e:
    WEB_SEARCH_AVAILABLE = False
    print(f"警告: web_search 模块未找到，将使用本地搜索 ({e})")


class ActivityKeywordExtractor:
    """从新闻标题中提取活动关键词（支持分词和大模型）"""
    
    # 停用词列表
    STOP_WORDS = {"的", "了", "在", "是", "有", "和", "也", "都", "而", "及", "与",
                  "着", "或", "一个", "没有", "我们", "你们", "他们", "它们",
                  "这", "那", "这些", "那些", "什么", "怎么", "如何", "为什么",
                  "因为", "所以", "但是", "虽然", "如果", "可以", "应该", "必须",
                  "会", "能", "要", "不", "很", "非常", "特别", "太", "更", "最",
                  "今日", "明天", "今天", "现在", "目前", "已经", "正在", "即将",
                  "将", "被", "由", "为", "对", "对于", "关于", "通过", "根据",
                  "按照", "经过", "由于", "鉴于", "基于", "通过", "利用", "使用",
                  "进行", "开展", "实施", "推进", "加强", "提高", "改善", "完善",
                  "举办", "举行", "召开", "开展", "发起", "组织", "参与", "出席",
                  "发布", "宣布", "公布", "启动", "启动", "结束", "开始", "完成"}
    
    # 活动类型词库
    EVENT_TYPES = {
        "发布会", "峰会", "论坛", "年会", "庆典", "展览", "展会",
        "快闪", "路演", "沙龙", "品鉴会", "体验日", "开放日",
        "粉丝见面会", "品牌日", "周年庆", "答谢会", "招商会",
        "推介会", "启动仪式", "揭牌仪式", "签约仪式", "颁奖典礼",
        "音乐节", "演唱会", "见面会", "直播", "大会", "会议",
        "研讨", "培训", "分享会", "嘉年华", "马拉松", "比赛",
        "赛事", "挑战", "评选", "投票", "首发", "上市", "亮相",
    }
    
    # 组织机构词尾
    ORG_SUFFIXES = {"公司", "集团", "协会", "委员会", "基金会", "政府", 
                    "大学", "学院", "机构", "部门", "中心", "联盟",
                    "组织", "媒体", "报社", "杂志社", "电视台", "广播",
                    "理事会", "董事会", "议会", "议院", "政党", "研究院", "研究所"}
    
    @staticmethod
    def extract_keywords(title: str, source: str = "") -> List[str]:
        """
        从新闻标题中提取关键词（使用分词+规则组合）
        返回: 关键词列表（按重要性排序）
        """
        keywords = []
        
        # 1. 使用分词工具提取关键词
        if JIEBA_AVAILABLE:
            seg_result = pseg.cut(title)
            for word, flag in seg_result:
                # 提取名词、专有名词、动词等
                if flag.startswith('n') or flag.startswith('v') or flag == 'eng':
                    if word not in ActivityKeywordExtractor.STOP_WORDS and len(word) > 1:
                        keywords.append(word)
        else:
            # 简单分词模式
            keywords.extend(ActivityKeywordExtractor._simple_tokenize(title))
        
        # 2. 提取活动类型关键词
        for event_type in ActivityKeywordExtractor.EVENT_TYPES:
            if event_type in title:
                keywords.append(event_type)
        
        # 3. 提取组织机构（基于词尾）
        keywords.extend(ActivityKeywordExtractor._extract_orgs_by_suffix(title))
        
        # 4. 提取引号中的内容
        keywords.extend(ActivityKeywordExtractor._extract_quoted_content(title))
        
        # 5. 提取长词（活动名称）
        keywords.extend(ActivityKeywordExtractor._extract_long_phrases(title))
        
        # 去重并过滤
        keywords = list(set(keywords))
        keywords = [k for k in keywords if k and len(k) > 1 and k not in ActivityKeywordExtractor.STOP_WORDS]
        
        # 按长度排序（长关键词优先，更具特异性）
        keywords.sort(key=lambda x: -len(x))
        
        return keywords[:10]  # 最多返回10个关键词
    
    @staticmethod
    def _simple_tokenize(title: str) -> List[str]:
        """简单分词（fallback）"""
        # 移除标点符号
        cleaned = re.sub(r'[，,。.！!？?、/\\|·]', ' ', title)
        tokens = cleaned.split()
        return [t for t in tokens if len(t) > 1]
    
    @staticmethod
    def _extract_orgs_by_suffix(title: str) -> List[str]:
        """基于词尾提取组织机构"""
        orgs = []
        for suffix in ActivityKeywordExtractor.ORG_SUFFIXES:
            pattern = r'([\u4e00-\u9fa5]{2,})' + suffix
            matches = re.findall(pattern, title)
            for match in matches:
                orgs.append(match + suffix)
        return orgs
    
    @staticmethod
    def _extract_quoted_content(title: str) -> List[str]:
        """提取引号中的内容"""
        patterns = [r'"([^"]+)"', r"'([^']+)'", r"「([^」]+)」", r"《([^》]+)》"]
        results = []
        for pattern in patterns:
            matches = re.findall(pattern, title)
            results.extend(matches)
        return results
    
    @staticmethod
    def _extract_long_phrases(title: str) -> List[str]:
        """提取长词短语（活动名称）"""
        phrases = []
        # 匹配活动名称模式
        patterns = [
            r'([\u4e00-\u9fa5]{3,}发布会)',
            r'([\u4e00-\u9fa5]{3,}峰会)',
            r'([\u4e00-\u9fa5]{3,}论坛)',
            r'([\u4e00-\u9fa5]{3,}音乐节)',
            r'([\u4e00-\u9fa5]{3,}演唱会)',
            r'([\u4e00-\u9fa5]{3,}大会)',
            r'([\u4e00-\u9fa5]{3,}庆典)',
            r'([\u4e00-\u9fa5]{3,}仪式)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, title)
            phrases.extend(matches)
        return phrases
    
    @staticmethod
    def build_search_queries(keywords: List[str], max_queries: int = 5) -> List[str]:
        """
        构建搜索查询组合（基于分词关键词）
        返回: 搜索查询列表
        """
        queries = []
        
        # 1. 使用完整标题作为查询（最精确）
        # 2. 长关键词优先组合
        if len(keywords) >= 2:
            # 长关键词组合
            long_keywords = [k for k in keywords if len(k) >= 3]
            for i in range(min(len(long_keywords), 3)):
                for j in range(i + 1, min(len(long_keywords), 4)):
                    query = f"{long_keywords[i]} {long_keywords[j]}"
                    if query not in queries:
                        queries.append(query)
        
        # 3. 添加单个长关键词
        for keyword in [k for k in keywords if len(k) >= 3]:
            if keyword not in queries and len(queries) < max_queries:
                queries.append(keyword)
        
        # 4. 添加短关键词组合
        if len(queries) < max_queries:
            for keyword in keywords[:max_queries - len(queries)]:
                if keyword not in queries:
                    queries.append(keyword)
        
        return queries[:max_queries]


class ActivityInfoSearcher:
    """搜索同活动相关信息（支持本地搜索和网络搜索）"""
    
    def __init__(self, config: Dict, search_config: Dict = None):
        self.config = config
        self.request_timeout = config.get("SEARCH_TIMEOUT", 30)
        self.max_search_results = config.get("MAX_SEARCH_RESULTS", 5)
        self.local_data_cache = {}
        
        # 初始化网络搜索引擎
        self.search_engine = None
        if WEB_SEARCH_AVAILABLE:
            try:
                # 即使search_config为空，也会默认使用百度搜索
                self.search_engine = MultiSearchEngine(search_config or {})
                print("✓ 网络搜索引擎已初始化")
            except Exception as e:
                print(f"网络搜索引擎初始化失败: {e}")
    
    def set_local_data(self, all_results: Dict, id_to_name: Dict):
        """设置本地数据缓存，用于搜索"""
        self.local_data_cache = {
            "all_results": all_results,
            "id_to_name": id_to_name,
        }
    
    def search_related_info(self, title: str, keywords: List[str], search_queries: List[str]) -> List[Dict]:
        """
        搜索活动相关信息
        返回: 搜索结果列表
        """
        all_results = []
        
        # 1. 首先从本地数据中搜索（已爬取的新闻）
        local_results = self._search_from_local_data(title, keywords)
        all_results.extend(local_results)
        print(f"  本地搜索找到 {len(local_results)} 条结果")
        
        # 2. 网络搜索（使用多个查询）
        web_results_count = 0
        if self.search_engine:
            for query in search_queries[:3]:
                web_results = self._search_from_web(query)
                web_results_count += len(web_results)
                all_results.extend(web_results)
                if web_results:
                    print(f"  网络搜索 '{query}' 找到 {len(web_results)} 条结果")
        else:
            print("  ⚠ 网络搜索引擎未配置，使用DuckDuckGo搜索")
            # 使用DuckDuckGo作为后备
            duckduckgo = DuckDuckGoSearch()
            for query in search_queries[:2]:
                web_results = self._search_from_web_duckduckgo(query)
                web_results_count += len(web_results)
                all_results.extend(web_results)
        
        print(f"  共找到 {len(all_results)} 条相关结果（本地{len(local_results)} + 网络{web_results_count}）")
        
        # 去重
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # 过滤与原标题相关的结果
        filtered_results = self._filter_related_results(title, keywords, unique_results)
        
        return filtered_results[:self.max_search_results]
    
    def _search_from_local_data(self, original_title: str, keywords: List[str]) -> List[Dict]:
        """从本地数据中搜索相关信息"""
        results = []
        
        if not self.local_data_cache:
            return results
        
        all_results = self.local_data_cache.get("all_results", {})
        id_to_name = self.local_data_cache.get("id_to_name", {})
        
        original_keywords_lower = set(k.lower() for k in keywords)
        
        # 遍历所有平台的新闻
        for platform_id, platform_data in all_results.items():
            if not isinstance(platform_data, dict):
                continue
            
            news_list = platform_data.get("data", [])
            if not isinstance(news_list, list):
                continue
            
            for news in news_list:
                if not isinstance(news, dict):
                    continue
                
                news_title = news.get("title", "")
                if not news_title or news_title == original_title:
                    continue
                
                # 计算关键词匹配度（放宽条件：至少匹配1个关键词）
                news_title_lower = news_title.lower()
                matches = 0
                for keyword in original_keywords_lower:
                    if keyword in news_title_lower:
                        matches += 1
                
                if matches >= 1:
                    result = {
                        "title": news_title,
                        "url": news.get("url", news.get("mobileUrl", "")),
                        "source": id_to_name.get(platform_id, platform_id),
                        "content": news_title,
                        "relevance_score": matches,
                    }
                    results.append(result)
        
        # 按相关性排序
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return results[:5]
    
    def _search_from_web(self, query: str) -> List[Dict]:
        """使用已配置的网络搜索引擎搜索"""
        if not self.search_engine:
            return self._search_from_web_duckduckgo(query)
        
        try:
            return self.search_engine.search(query)
        except Exception as e:
            print(f"网络搜索失败: {e}")
            return []
    
    def _search_from_web_duckduckgo(self, query: str) -> List[Dict]:
        """使用 DuckDuckGo 搜索"""
        try:
            engine = DuckDuckGoSearch()
            results = engine.search(query)
            return results
        except Exception as e:
            print(f"DuckDuckGo搜索失败: {e}")
            return []
    
    def _filter_related_results(self, original_title: str, keywords: List[str], results: List[Dict]) -> List[Dict]:
        """过滤相关结果（更宽松的匹配条件）"""
        filtered = []
        original_keywords = set(keywords)
        
        for result in results:
            title = result.get("title", "")
            content = result.get("content", "") or result.get("snippet", "")
            full_text = f"{title} {content}"
            
            # 计算关键词重叠度（放宽到至少1个匹配）
            matches = sum(1 for kw in original_keywords if kw in full_text)
            
            if matches >= 1:
                result["relevance_score"] = matches
                filtered.append(result)
        
        # 按相关性排序
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return filtered
    
    def extract_content_from_url(self, url: str) -> Optional[str]:
        """从URL提取内容"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            response.raise_for_status()
            
            # 简单提取文本内容
            content = response.text
            content = re.sub(r"<[^>]+>", "", content)
            content = re.sub(r"\s+", " ", content).strip()
            
            return content[:3000]
        except Exception as e:
            print(f"从URL提取内容失败: {e}")
            return None


class ActivityContentVerifier:
    """使用大模型验证内容真实性并总结"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = config.get("LLM_CONFIG", {})
        self.enabled = self.llm_config.get("ENABLED", False)
        self.provider = self.llm_config.get("PROVIDER", "deepseek")
        self.api_key = self.llm_config.get("API_KEY", "")
        self.model = self.llm_config.get("MODEL", "deepseek-chat")
        self.max_tokens = self.llm_config.get("MAX_TOKENS", 1000)
        self.temperature = self.llm_config.get("TEMPERATURE", 0.7)
        self.timeout = self.llm_config.get("TIMEOUT", 30)
    
    def verify_and_summarize(self, original_news: Dict, related_info: List[Dict]) -> Dict:
        """
        验证内容真实性并总结
        original_news: 原始新闻 {'title': ..., 'url': ..., 'source': ...}
        related_info: 相关信息列表
        返回: 验证和总结结果
        """
        result = {
            "verified": False,
            "summary": original_news.get("title", ""),
            "sources": [original_news.get("source", "未知")],
            "confirmed_info": [],
            "confidence": 0.5 if related_info else 0.3,
            "verification_source": "未验证",
        }
        
        if not self.enabled or not self.api_key:
            if related_info:
                result["summary"] = self._simple_summarize(original_news, related_info)
                result["sources"] = list(set(result["sources"] + [r.get("source", "") for r in related_info]))
                result["confidence"] = 0.6
                result["verification_source"] = "多源信息整合"
            return result
        
        # 构建提示词（包含搜索结果）
        prompt = self._build_verification_prompt(original_news, related_info)
        
        # 调用大模型
        try:
            response = self._call_llm(prompt)
            verified_result = self._parse_verification_response(response)
            
            result.update(verified_result)
            result["verification_source"] = "AI验证+网络信息"
            
        except Exception as e:
            print(f"真实性验证失败: {e}")
            if related_info:
                result["summary"] = self._simple_summarize(original_news, related_info)
                result["sources"] = list(set(result["sources"] + [r.get("source", "") for r in related_info]))
                result["confidence"] = 0.6
                result["verification_source"] = "多源信息整合"
        
        return result
    
    def _simple_summarize(self, original_news: Dict, related_info: List[Dict]) -> str:
        """简单总结（不使用大模型）"""
        title = original_news.get("title", "")
        summaries = [title]
        
        for info in related_info[:3]:
            info_title = info.get("title", "")
            if info_title and info_title != title:
                summaries.append(info_title)
        
        return "；".join(summaries)
    
    def _build_verification_prompt(self, original_news: Dict, related_info: List[Dict]) -> str:
        """构建真实性验证提示词"""
        title = original_news.get("title", "")
        source = original_news.get("source", "")
        
        related_text = "\n".join([f"- {info.get('title', '')}" for info in related_info[:5]])
        
        prompt = f"""
你是一位新闻真实性验证专家。请根据以下信息验证新闻的真实性并进行总结：

原始新闻标题：{title}
原始来源：{source}

相关信息：
{related_text}

请按照以下格式输出：
总结：（综合所有信息，用简洁的语言总结这个活动）
可信度：（0-1之间的数字，表示内容真实的概率）
确认信息：（列出已确认的关键信息）

注意：
1. 如果有多个来源报道同一事件，可信度更高
2. 如果信息相互矛盾，请指出
3. 如果没有足够信息，请说明
"""
        return prompt.strip()
    
    def _call_llm(self, prompt: str) -> str:
        """调用大模型（使用DeepSeek API）"""
        import requests
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
        response.raise_for_status()
        
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def _parse_verification_response(self, response: str) -> Dict:
        """解析大模型验证响应"""
        result = {
            "verified": True,
            "summary": "",
            "confidence": 0.7,
            "confirmed_info": [],
        }
        
        # 解析总结
        summary_match = re.search(r"总结：(.+?)(可信度|$)", response)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()
        
        # 解析可信度
        confidence_match = re.search(r"可信度：([\d.]+)", response)
        if confidence_match:
            try:
                result["confidence"] = float(confidence_match.group(1))
            except ValueError:
                pass
        
        # 解析确认信息
        confirmed_match = re.search(r"确认信息：(.+)", response)
        if confirmed_match:
            confirmed_text = confirmed_match.group(1)
            result["confirmed_info"] = [c.strip() for c in confirmed_text.split("；") if c.strip()]
        
        return result


class ActivityEnrichmentPipeline:
    """活动信息扩充流程管道"""
    
    def __init__(self, config: Dict, llm_config: Dict = None, search_config: Dict = None):
        self.config = config
        self.keyword_extractor = ActivityKeywordExtractor()
        self.info_searcher = ActivityInfoSearcher(config, search_config)
        self.content_verifier = ActivityContentVerifier({"LLM_CONFIG": llm_config or {}})
        
        self.enabled = config.get("ENABLED", True)
        self.min_confidence = config.get("MIN_CONFIDENCE_FOR_PUSH", 0.3)
    
    def set_local_data(self, all_results: Dict, id_to_name: Dict):
        """设置本地数据用于搜索"""
        self.info_searcher.set_local_data(all_results, id_to_name)
    
    def enrich_activity_info(self, title: str, url: str = "", source: str = "") -> Optional[Dict]:
        """
        扩充活动信息（完整流程）
        返回: 扩充后的信息，如果失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            # 1. 提取关键词
            keywords = self.keyword_extractor.extract_keywords(title)
            print(f"提取到关键词: {keywords}")
            
            if not keywords:
                keywords = [title[:10]]  # 使用标题作为备选
            
            # 2. 构建搜索查询
            search_queries = self.keyword_extractor.build_search_queries(keywords)
            print(f"搜索查询: {search_queries}")
            
            # 3. 搜索相关信息
            related_info = self.info_searcher.search_related_info(title, keywords, search_queries)
            print(f"找到 {len(related_info)} 条相关信息")
            
            # 4. 验证真实性并总结
            original_news = {"title": title, "url": url, "source": source}
            result = self.content_verifier.verify_and_summarize(original_news, related_info)
            
            # 5. 添加来源信息
            if related_info:
                result["sources"] = list(set(result.get("sources", []) + [r.get("source", "") for r in related_info]))
            
            print(f"活动信息扩充完成，可信度: {result.get('confidence', 0)}")
            
            return result
            
        except Exception as e:
            print(f"活动信息扩充失败: {e}")
            return None
