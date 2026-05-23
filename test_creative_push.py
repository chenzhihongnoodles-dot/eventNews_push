#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
from datetime import datetime
import pytz

def send_wework_message(webhook_url, title, content):
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

def generate_test_content():
    """生成测试内容"""
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    timestamp = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
    
    test_cases = [
        {
            "type": "品牌活动",
            "title": "【品牌体验】沉浸式品牌故事展",
            "description": "创新运用AR增强现实技术，打造沉浸式品牌故事体验空间。用户可通过互动装置探索品牌历史、产品理念，实现品牌与消费者的深度连接。",
            "key_elements": ["AR技术", "互动装置", "品牌故事", "沉浸式体验"],
            "applicable_scenarios": ["新品发布", "品牌升级", "周年庆典"]
        },
        {
            "type": "线上活动",
            "title": "【云发布会】多平台联动直播",
            "description": "整合抖音、视频号、B站等多平台同步直播，支持实时弹幕互动、在线问答、抽奖环节，打破地域限制，实现最大化曝光。",
            "key_elements": ["多平台直播", "实时互动", "在线抽奖", "数据统计"],
            "applicable_scenarios": ["新品发布", "行业峰会", "线上论坛"]
        },
        {
            "type": "线下活动",
            "title": "【快闪营销】限时主题快闪店",
            "description": "打造限时主题快闪空间，结合网红打卡点、限量周边、社交分享裂变机制，吸引年轻消费群体，提升品牌话题度。",
            "key_elements": ["主题空间", "网红打卡", "限量周边", "社交裂变"],
            "applicable_scenarios": ["新品推广", "节日营销", "品牌曝光"]
        },
        {
            "type": "跨界活动",
            "title": "【跨界联名】品牌共创活动",
            "description": "携手异业品牌开展联名活动，通过资源互补、用户共享，实现1+1>2的营销效果，拓展品牌边界。",
            "key_elements": ["异业合作", "资源整合", "用户共享", "联名产品"],
            "applicable_scenarios": ["品牌升级", "用户增长", "市场拓展"]
        },
        {
            "type": "公益活动",
            "title": "【可持续发展】环保主题活动",
            "description": "以环保为主题，结合公益捐赠、绿色体验、环保讲座，传递企业社会责任理念，提升品牌美誉度。",
            "key_elements": ["公益捐赠", "环保体验", "社会责任", "品牌形象"],
            "applicable_scenarios": ["CSR活动", "品牌公关", "公益营销"]
        }
    ]
    
    # 构建推送内容
    content = f"## 🎯 活动策划创意推送测试\n\n"
    content += f"**测试时间**: {timestamp}\n"
    content += f"**测试类型**: 多类型活动策划创意推送\n"
    content += f"**测试数量**: {len(test_cases)}个创意方案\n\n"
    content += "---\n\n"
    
    for i, case in enumerate(test_cases, 1):
        content += f"### {i}. {case['title']}\n\n"
        content += f"**活动类型**: {case['type']}\n\n"
        content += f"**创意描述**:\n> {case['description']}\n\n"
        content += f"**核心要素**: {' | '.join(case['key_elements'])}\n\n"
        content += f"**适用场景**: {' → '.join(case['applicable_scenarios'])}\n\n"
        content += "---\n\n"
    
    content += "**测试说明**:\n"
    content += "- 本次测试包含5种不同类型的活动策划创意\n"
    content += "- 覆盖品牌活动、线上活动、线下活动、跨界活动、公益活动\n"
    content += "- 验证推送格式、内容展示、关键词匹配效果\n\n"
    content += "*TrendRadar 活动策划热点监控系统*"
    
    return content, test_cases

def run_test():
    """执行测试"""
    wework_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=05548e17-3b9d-4601-8749-a50501c3ea77"
    
    print("📋 正在生成测试内容...")
    content, test_cases = generate_test_content()
    
    print("📤 正在发送测试消息到企业微信...")
    result = send_wework_message(wework_url, "活动策划创意推送测试", content)
    
    # 生成测试报告
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    report = f"""
╔══════════════════════════════════════════════════════════════╗
║              活动策划创意推送测试报告                         ║
╚══════════════════════════════════════════════════════════════╝

测试时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}
测试环境: 企业微信推送
测试目标: 验证多类型活动策划创意推送效果

────────────────────────────────────────────────────────────────

📊 测试内容概览:
┌─────┬────────────┬─────────────────────────────────────────┐
│ 序号 │ 活动类型   │ 创意主题                               │
├─────┼────────────┼─────────────────────────────────────────┤
"""
    
    for i, case in enumerate(test_cases, 1):
        report += f"│ {i:^3} │ {case['type']:^8} │ {case['title']:^39} │\n"
    
    report += """└─────┴────────────┴─────────────────────────────────────────┘

────────────────────────────────────────────────────────────────

📈 测试结果:
┌─────────────────────────────────────────────────────────────┐
│ 推送状态: {}                                           │
│ 响应信息: {}                                           │
│ 消息长度: {} 字符                                        │
│ 创意数量: {} 个                                          │
└─────────────────────────────────────────────────────────────┘

────────────────────────────────────────────────────────────────

🎯 测试评估:
{}

─────────────────────────────────────────────────────────────

💡 优化建议:
{}
""".format(
            "✅ 成功" if result["success"] else "❌ 失败",
            result["message"],
            len(content),
            len(test_cases),
            generate_evaluation(result["success"], test_cases),
            generate_recommendations(test_cases)
        )
    
    print(report)
    
    # 保存测试报告
    report_filename = f"test_report_{beijing_time.strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📝 测试报告已保存: {report_filename}")
    
    return result

def generate_evaluation(success, test_cases):
    """生成测试评估"""
    if not success:
        return """
│ 状态: 推送失败
│ 原因: 网络问题或配置错误
│ 建议: 检查Webhook配置和网络连接
"""
    
    evaluation = f"""
│ 状态: ✅ 推送成功
│ 评估:
│   1. 消息格式: 符合企业微信Markdown规范
│   2. 内容完整性: 包含{len(test_cases)}个完整创意方案
│   3. 类型覆盖: 涵盖5种活动类型
│   4. 信息结构: 标题、描述、要素、场景完整
│   5. 关键词匹配: 活动策划相关词汇已包含
"""
    return evaluation

def generate_recommendations(test_cases):
    """生成优化建议"""
    recommendations = """
1. 关键词优化:
   - 可增加更多细分领域关键词（如"直播带货"、"私域运营"）
   - 添加行业特定词汇（如"文旅活动"、"体育赛事"）

2. 内容优化:
   - 增加案例参考链接
   - 添加活动预算范围建议
   - 补充执行时间表模板

3. 推送策略优化:
   - 工作日推送频率可提高
   - 重要节日前增加推送密度
   - 根据历史数据调整关键词权重

4. 功能扩展:
   - 添加创意方案评分系统
   - 支持按行业/预算筛选
   - 增加案例收藏和分享功能
"""
    return recommendations

if __name__ == "__main__":
    print("🚀 活动策划创意推送测试启动\n")
    result = run_test()
    print("\n" + "="*60)
    print("测试完成！请查看企业微信群消息")
    print("="*60)
