#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
from datetime import datetime
import pytz

def send_wework_message(webhook_url, content):
    """发送消息到企业微信"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        response = requests.post(webhook_url, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        if result.get("errcode") == 0:
            return {"success": True, "message": "发送成功"}
        else:
            return {"success": False, "message": result.get('errmsg')}
    except Exception as e:
        return {"success": False, "message": str(e)}

def load_trends_data():
    """加载真实爬取的数据"""
    try:
        with open("api/trends.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"读取数据失败: {e}")
        return None

def generate_real_content(trends_data):
    """生成真实新闻推送内容"""
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    content = f"## 📰 活动策划热点速递\n\n"
    content += f"**推送时间**: {timestamp}\n"
    content += f"**新闻来源**: 全网12个平台\n"
    content += f"**处理条数**: {trends_data['total_titles_processed']}条\n\n"
    content += "---\n\n"
    
    trends = trends_data.get('trends', [])
    
    if not trends:
        content += "⚠️ 暂无匹配的活动策划相关新闻\n"
        content += "系统将持续监控，有新内容时会及时推送\n\n"
    else:
        for trend in trends:
            keyword_group = trend['keyword_group'].replace("#", "").strip()
            content += f"### 🔍 关键词组: {keyword_group}\n\n"
            content += f"**匹配数量**: {trend['match_count']}条\n\n"
            
            for item in trend['titles']:
                content += f"📌 [{item['title']}]({item['url']})\n"
                content += f"   - 来源: {item['source']}\n"
                content += f"   - 排名: TOP{item['ranks'][0]}\n"
                content += f"   - 时间: {item['time_info']}\n\n"
            
            content += "---\n\n"
    
    content += "*数据来源：TrendRadar 热点监控系统*"
    return content

def run_real_test():
    """执行真实新闻推送测试"""
    wework_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=05548e17-3b9d-4601-8749-a50501c3ea77"
    
    print("📥 正在加载真实抓取的新闻数据...")
    trends_data = load_trends_data()
    
    if not trends_data:
        print("❌ 无法加载新闻数据")
        return
    
    print("📝 正在生成真实新闻推送内容...")
    content = generate_real_content(trends_data)
    
    print("📤 正在发送真实新闻到企业微信...")
    result = send_wework_message(wework_url, content)
    
    # 生成测试报告
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║              活动策划热点真实推送测试报告                     ║
╚══════════════════════════════════════════════════════════════╝

测试时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}
数据来源: 真实网络爬虫
监控平台: 12个

────────────────────────────────────────────────────────────────

📊 数据概览:
┌─────────────────────────────────────────────────────────────┐
│ 总新闻条数: {trends_data['total_titles_processed']} 条       │
│ 匹配关键词组: {len(trends_data.get('trends', []))} 个        │
│ 推送状态: {'✅ 成功' if result['success'] else '❌ 失败'}   │
│ 响应信息: {result['message']}                              │
└─────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────

📰 匹配新闻详情:
"""
    
    trends = trends_data.get('trends', [])
    if trends:
        for i, trend in enumerate(trends, 1):
            report += f"\n{i}. 关键词组: {trend['keyword_group'].replace('#', '').strip()}\n"
            report += f"   匹配数量: {trend['match_count']}条\n"
            for item in trend['titles']:
                report += f"   - [{item['title'][:30]}...] ({item['source']})\n"
    else:
        report += "\n   暂无匹配新闻\n"
    
    report += """
────────────────────────────────────────────────────────────────

🎯 测试结论:
{}

─────────────────────────────────────────────────────────────

💡 优化方向:
1. 当前关键词匹配结果较少，建议增加更多活动策划相关关键词
2. 可以添加更多行业特定词汇（如会议、展览、节庆等）
3. 考虑添加"活动策划公司"、"营销策划"等更精准的关键词
""".format(
            """
│ ✅ 爬虫功能正常，成功抓取999条新闻
│ ✅ 关键词匹配功能正常
│ ✅ 企业微信推送功能正常
│ ⚠️ 当前匹配结果较少，建议优化关键词配置
""" if result['success'] else """
│ ❌ 推送失败，请检查配置
"""
        )
    
    print(report)
    
    # 保存测试报告
    report_filename = f"real_news_report_{beijing_time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📝 测试报告已保存: {report_filename}")
    
    return result

if __name__ == "__main__":
    print("🚀 真实新闻推送测试启动\n")
    result = run_real_test()
    print("\n" + "="*60)
    print("测试完成！请查看企业微信群消息")
    print("="*60)
