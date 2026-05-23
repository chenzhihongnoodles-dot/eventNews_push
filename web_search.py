# coding=utf-8
"""网络搜索模块 - 支持多种搜索引擎API"""

import re
import time
from typing import Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# 尝试导入百度搜索库
try:
    from baidusearch.baidusearch import search as baidu_search
    BAIDU_SEARCH_AVAILABLE = True
except ImportError:
    BAIDU_SEARCH_AVAILABLE = False


class WebSearchEngine:
    """网络搜索引擎基类"""
    
    def __init__(self, api_key: str = "", config: Dict = None):
        self.api_key = api_key
        self.config = config or {}
        self.timeout = self.config.get("timeout", 10)
        self.max_results = self.config.get("max_results", 5)
    
    def search(self, query: str) -> List[Dict]:
        """搜索接口，返回搜索结果列表"""
        raise NotImplementedError
    
    def _parse_result(self, item: Dict) -> Dict:
        """解析单个搜索结果"""
        return {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("snippet", item.get("description", "")),
            "source": self.__class__.__name__,
        }


class BingSearchAPI(WebSearchEngine):
    """必应搜索API"""
    
    def __init__(self, api_key: str = "", config: Dict = None):
        super().__init__(api_key, config)
        self.endpoint = "https://api.bing.microsoft.com/v7.0/search"
    
    def search(self, query: str) -> List[Dict]:
        """使用 Bing Search API 搜索"""
        if not self.api_key:
            print("警告: 未配置 Bing API Key")
            return []
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
        }
        
        params = {
            "q": query,
            "count": self.max_results,
            "mkt": "zh-CN",  # 中文市场
            "responseFilter": "WebPages",
        }
        
        try:
            response = requests.get(
                self.endpoint,
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("webPages", {}).get("value", []):
                results.append(self._parse_result(item))
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"Bing搜索失败: {e}")
            return []
        except Exception as e:
            print(f"Bing搜索错误: {e}")
            return []


class SerpAPISearch(WebSearchEngine):
    """SerpAPI (支持 Google, Bing, Yahoo 等)"""
    
    def __init__(self, api_key: str = "", config: Dict = None):
        super().__init__(api_key, config)
        self.endpoint = "https://serpapi.com/search"
        self.engine = self.config.get("engine", "google")  # google, bing, baidu, duckduckgo
    
    def search(self, query: str) -> List[Dict]:
        """使用 SerpAPI 搜索"""
        if not self.api_key:
            print("警告: 未配置 SerpAPI Key")
            return []
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": self.engine,
            "num": self.max_results,
        }
        
        try:
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 根据不同引擎解析结果
            if self.engine == "google":
                for item in data.get("organic_results", [])[:self.max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "Google",
                    })
            elif self.engine == "bing":
                for item in data.get("organic_results", [])[:self.max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "Bing",
                    })
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"SerpAPI搜索失败: {e}")
            return []
        except Exception as e:
            print(f"SerpAPI搜索错误: {e}")
            return []


class DuckDuckGoSearch(WebSearchEngine):
    """DuckDuckGo 搜索 (免费，无需API Key)"""
    
    def __init__(self, api_key: str = "", config: Dict = None):
        super().__init__(api_key, config)
        self.endpoint = "https://api.duckduckgo.com/"
    
    def search(self, query: str) -> List[Dict]:
        """使用 DuckDuckGo Instant Answer API"""
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        
        try:
            response = requests.get(
                self.endpoint,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 提取RelatedTopics
            for topic in data.get("RelatedTopics", [])[:self.max_results]:
                if "Text" in topic and "FirstURL" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                        "source": "DuckDuckGo",
                    })
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"DuckDuckGo搜索失败: {e}")
            return []
        except Exception as e:
            print(f"DuckDuckGo搜索错误: {e}")
            return []


class BaiduSearch(WebSearchEngine):
    """百度搜索 (使用 python-baidusearch 库)"""
    
    def __init__(self, api_key: str = "", config: Dict = None):
        super().__init__(api_key, config)
        if not BAIDU_SEARCH_AVAILABLE:
            print("警告: baidusearch 库未安装")
    
    def search(self, query: str) -> List[Dict]:
        """使用百度搜索"""
        if not BAIDU_SEARCH_AVAILABLE:
            print("警告: baidusearch 库不可用")
            return []
        
        try:
            # 使用 baidusearch 库进行搜索
            results = baidu_search(query, num_results=self.max_results)
            
            parsed_results = []
            for item in results:
                parsed_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("abstract", item.get("description", "")),
                    "source": "百度",
                })
            
            return parsed_results
            
        except Exception as e:
            print(f"百度搜索失败: {e}")
            return []



class MultiSearchEngine:
    """多搜索引擎聚合"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.engines = []
        
        # 根据配置初始化搜索引擎
        self._init_engines()
    
    def _init_engines(self):
        """初始化搜索引擎列表"""
        # 优先使用百度搜索（中文效果好）
        if BAIDU_SEARCH_AVAILABLE:
            self.engines.append(BaiduSearch(config={
                "timeout": 10,
                "max_results": 5,
            }))
            print("✓ 百度搜索已启用 (免费)")
        
        # Bing Search API
        bing_key = self.config.get("bing_api_key", "")
        if bing_key:
            self.engines.append(BingSearchAPI(bing_key, {
                "timeout": 10,
                "max_results": 5,
            }))
            print("✓ Bing搜索已启用")
        
        # SerpAPI
        serp_key = self.config.get("serpapi_key", "")
        if serp_key:
            engine = self.config.get("serpapi_engine", "google")
            self.engines.append(SerpAPISearch(serp_key, {
                "engine": engine,
                "timeout": 10,
                "max_results": 5,
            }))
            print(f"✓ SerpAPI ({engine})已启用")
        
        # DuckDuckGo (免费备用)
        if not self.engines:
            self.engines.append(DuckDuckGoSearch(config={
                "timeout": 10,
                "max_results": 5,
            }))
            print("✓ DuckDuckGo搜索已启用 (免费模式)")
    
    def search(self, query: str) -> List[Dict]:
        """使用多个搜索引擎搜索"""
        all_results = []
        seen_urls = set()
        
        for engine in self.engines:
            try:
                results = engine.search(query)
                
                for result in results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(result)
                
                # 避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"搜索引擎 {engine.__class__.__name__} 错误: {e}")
                continue
        
        # 去重并返回
        return all_results[:self.config.get("max_results", 10)]


# 使用示例和配置指南
USAGE_GUIDE = """
# 网络搜索配置指南

## 方案一: Bing Search API (推荐)
1. 访问 https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
2. 申请 API Key (免费层: 每月1000次请求)
3. 在 config/config.yaml 中配置:
   enrichment:
     search_engines:
       bing_api_key: "YOUR_BING_API_KEY"

## 方案二: SerpAPI (支持多引擎)
1. 访问 https://serpapi.com
2. 注册并获取 API Key (免费层: 每月100次搜索)
3. 在 config/config.yaml 中配置:
   enrichment:
     search_engines:
       serpapi_key: "YOUR_SERPAPI_KEY"
       serpapi_engine: "google"  # google, bing, baidu, duckduckgo

## 方案三: DuckDuckGo (免费，无需API Key)
- 无需配置，默认启用
- 注意: 可能有频率限制

## 配置示例 (config/config.yaml)
```yaml
enrichment:
  enabled: true
  search_engines:
    bing_api_key: ""  # 留空则使用DuckDuckGo
    # serpapi_key: ""
    # serpapi_engine: "google"
```
"""
