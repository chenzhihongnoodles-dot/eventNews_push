# coding=utf-8
"""关键词提取模块 - 从新闻标题中提取活动相关关键词"""

import re
from typing import List, Set, Optional

# 尝试导入jieba分词库
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

# 停用词列表
STOP_WORDS = {
    '的', '了', '和', '是', '就', '都', '而', '及', '与', '着', '或', '一个',
    '没有', '我们', '你们', '他们', '它们', '这个', '那个', '这些', '那些',
    '什么', '怎么', '为什么', '因为', '所以', '但是', '然而', '虽然', '如果',
    '可以', '可能', '应该', '必须', '需要', '能够', '会', '要', '在', '有',
    '不', '也', '很', '还', '再', '又', '更', '最', '太', '非常', '特别',
    '今日', '今天', '昨日', '明天', '现在', '目前', '最近', '刚刚', '已经',
    '正在', '将要', '曾经', '一直', '经常', '偶尔', '从来', '总是', '始终',
    '一起', '一起', '一起', '一起', '一起', '一起', '一起', '一起', '一起',
}


class ActivityKeywordExtractor:
    """从新闻标题中提取活动相关关键词"""

    def __init__(self):
        if JIEBA_AVAILABLE:
            # 加载自定义词典（如有）
            try:
                jieba.load_userdict("config/custom_dict.txt")
            except:
                pass

    def extract_keywords(self, title: str) -> List[str]:
        """从标题中提取关键词"""
        if not title:
            return []

        keywords: Set[str] = set()

        # 使用jieba分词
        if JIEBA_AVAILABLE:
            words = pseg.cut(title)
            for word, flag in words:
                # 过滤停用词和短词
                if word in STOP_WORDS or len(word) < 2:
                    continue
                
                # 提取名词、动词、形容词
                if flag.startswith('n') or flag.startswith('v') or flag.startswith('a'):
                    keywords.add(word)
        else:
            # 降级方案：基于规则提取
            keywords = self._rule_based_extraction(title)

        # 提取长关键词（活动名称等）
        long_keywords = self._extract_long_keywords(title)
        keywords.update(long_keywords)

        return sorted(list(keywords))

    def _rule_based_extraction(self, title: str) -> Set[str]:
        """基于规则的关键词提取（降级方案）"""
        keywords: Set[str] = set()

        # 活动类型关键词
        event_types = [
            '发布会', '峰会', '论坛', '展会', '展览', '庆典', '晚会', '音乐会',
            '音乐节', '演唱会', '发布会', '见面会', '品鉴会', '研讨会', '交流会',
            '启动仪式', '颁奖典礼', '开幕', '闭幕', '嘉年华', '狂欢节', '艺术节',
            '文化节', '美食节', '啤酒节', '马拉松', '比赛', '竞赛', '挑战赛',
            '发布会', '推介会', '招商会', '洽谈会', '交易会', '博览会',
        ]
        
        # 组织/机构关键词
        organizations = [
            '公司', '集团', '企业', '协会', '联盟', '委员会', '政府', '部门',
            '大学', '学院', '研究院', '中心', '机构', '组织', '基金会',
        ]

        for event_type in event_types:
            if event_type in title:
                keywords.add(event_type)

        for org in organizations:
            if org in title:
                # 尝试提取完整的组织名称
                pattern = rf'[\u4e00-\u9fa5]+{org}'
                matches = re.findall(pattern, title)
                for match in matches:
                    if len(match) >= 3:
                        keywords.add(match)

        # 提取数字+单位（如"二十三号"）
        number_patterns = [
            r'\d+号', r'\d+届', r'\d+周年', r'\d+周年庆',
            r'第\d+届', r'第\d+期', r'\d+年',
        ]
        for pattern in number_patterns:
            matches = re.findall(pattern, title)
            keywords.update(matches)

        return keywords

    def _extract_long_keywords(self, title: str) -> Set[str]:
        """提取长关键词（活动名称等）"""
        keywords: Set[str] = set()

        # 尝试提取活动名称（包含关键词的长短语）
        event_keywords = ['发布会', '峰会', '论坛', '音乐节', '活动', '仪式']
        
        for keyword in event_keywords:
            if keyword in title:
                # 向前查找活动名称
                idx = title.index(keyword)
                start_idx = max(0, idx - 15)
                candidate = title[start_idx:idx + len(keyword)]
                
                # 清理候选词
                candidate = re.sub(r'^[\s\-—]+', '', candidate)
                candidate = re.sub(r'[\s\-—]+$', '', candidate)
                
                if len(candidate) >= 4:
                    keywords.add(candidate)

        return keywords

    def build_search_queries(self, title: str, max_queries: int = 3) -> List[str]:
        """根据标题构建搜索查询"""
        keywords = self.extract_keywords(title)
        
        if not keywords:
            return [title]

        queries = []
        
        # 使用完整标题作为第一个查询
        queries.append(title)
        
        # 使用关键词组合
        if len(keywords) >= 2:
            queries.append(' '.join(keywords[:2]))
            queries.append(' '.join(keywords[:3]))
        
        # 使用单个重要关键词
        important_keywords = [k for k in keywords if len(k) >= 3]
        if important_keywords:
            queries.append(important_keywords[0])

        # 去重并限制数量
        unique_queries = list(dict.fromkeys(queries))[:max_queries]
        return unique_queries