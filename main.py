# coding=utf-8
"""TrendRadar - 热点趋势雷达入口文件"""

import argparse

from src.utils.config_loader import init_config, get_config
from src.utils.logger import logger


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description="TrendRadar: 新闻热点分析工具。")
    parser.add_argument(
        '--serve-api',
        action='store_true',
        help='以API服务器模式运行，监听在 http://0.0.0.0:5001'
    )
    parser.add_argument(
        '--generate-json',
        action='store_true',
        help='仅生成静态的 trends.json, news.jpg 和相关HTML文件并退出'
    )
    args = parser.parse_args()

    try:
        # 初始化配置
        init_config()
        config = get_config()
        
        logger.info("=" * 60)
        logger.info("📊 TrendRadar v2.2.0 - 热点趋势雷达")
        logger.info("=" * 60)

        if args.serve_api:
            # API服务器模式
            try:
                from src.server import app
                logger.info("以API服务器模式启动...")
                app.run(host='0.0.0.0', port=5001, debug=False)
            except ImportError:
                logger.error("错误：无法启动API服务器，因为 Flask 模块未安装。")
                logger.error("请运行 'pip install Flask' 来安装。")
                return

        elif args.generate_json:
            # 仅生成静态API文件
            logger.info("仅生成静态API文件...")
            from src.crawler.data_processor import read_all_today_titles
            from src.report.api_generator import APIGenerator
            
            all_results, id_to_name, title_info = read_all_today_titles()
            
            # 构建报告数据（all_results 按标题去重：{标题: {sources,ranks,urls,mobileUrls}}）
            title_list = []
            for news_title, info in all_results.items():
                url = (info.get("urls", [""]) or [""])[0]
                mobile_url = (info.get("mobileUrls", [""]) or [""])[0]
                sources = info.get("sources", [])
                source_name = id_to_name.get(sources[0], sources[0]) if sources else "未知"
                
                title_list.append({
                    "title": news_title,
                    "url": url,
                    "mobile_url": mobile_url,
                    "source": source_name,
                    "ranks": info.get("ranks", []),
                })
            
            report_data = {
                "stats": [{
                    "id": "today",
                    "name": "今日热点",
                    "titles": title_list,
                }],
            }
            
            # 生成API文件
            api_generator = APIGenerator()
            api_generator.save(report_data)
            logger.info("文件生成完毕。")

        else:
            # 单次脚本模式
            logger.info("以单次脚本模式运行...")
            
            # ========== 静默推送时间检查 ==========
            push_config = config.get("push", {}) or config.get("notification", {})
            silent_push = push_config.get("silent_push", {})
            if silent_push.get("enabled", False):
                from datetime import datetime, timezone, timedelta
                import os
                
                beijing_tz = timezone(timedelta(hours=8))
                now_beijing = datetime.now(beijing_tz)
                current_time_str = now_beijing.strftime("%H:%M")
                today_str = now_beijing.strftime("%Y-%m-%d")
                
                time_range = silent_push.get("time_range", {})
                start_str = time_range.get("start", "08:30")
                end_str = time_range.get("end", "09:30")
                
                # 检查是否在推送时间范围内
                if not (start_str <= current_time_str <= end_str):
                    logger.info(f"当前北京时间 {current_time_str}，不在静默推送时段 {start_str}-{end_str}，跳过推送")
                    logger.info("数据爬取和保存照常进行...")
                    from src.crawler.data_fetcher import DataFetcher
                    from src.crawler.data_processor import save_titles_to_file
                    crawler_config = config.get_crawler_config()
                    platforms_config = config.get("platforms", []) or crawler_config.get("platforms", [])
                    platforms = []
                    for p in platforms_config:
                        if isinstance(p, dict):
                            platforms.append((p["id"], p["name"]))
                        else:
                            platforms.append(p)
                    if platforms:
                        fetcher = DataFetcher()
                        results, id_to_name, failed_ids = fetcher.crawl_websites(platforms)
                        if results:
                            save_titles_to_file(results, id_to_name, failed_ids)
                    return
                
                # 检查是否已推送过（once_per_day 功能）
                once_per_day = silent_push.get("once_per_day", False)
                if once_per_day:
                    # 创建推送记录目录
                    record_dir = ".push_records"
                    os.makedirs(record_dir, exist_ok=True)
                    record_file = os.path.join(record_dir, f"{today_str}.txt")
                    
                    if os.path.exists(record_file):
                        logger.info(f"今日 {today_str} 已推送过，跳过推送")
                        logger.info("数据爬取和保存照常进行...")
                        from src.crawler.data_fetcher import DataFetcher
                        from src.crawler.data_processor import save_titles_to_file
                        crawler_config = config.get_crawler_config()
                        platforms_config = config.get("platforms", []) or crawler_config.get("platforms", [])
                        platforms = []
                        for p in platforms_config:
                            if isinstance(p, dict):
                                platforms.append((p["id"], p["name"]))
                            else:
                                platforms.append(p)
                        if platforms:
                            fetcher = DataFetcher()
                            results, id_to_name, failed_ids = fetcher.crawl_websites(platforms)
                            if results:
                                save_titles_to_file(results, id_to_name, failed_ids)
                        return
                    else:
                        # 创建推送记录文件
                        with open(record_file, "w") as f:
                            f.write(f"Push recorded at {now_beijing.strftime('%Y-%m-%d %H:%M:%S')}")
                        logger.info(f"创建今日推送记录: {today_str}")
                
                logger.info(f"当前北京时间 {current_time_str}，在静默推送时段内，执行完整流程")
            
            from src.crawler.data_fetcher import DataFetcher
            from src.crawler.data_processor import (
                save_titles_to_file,
                load_frequency_words,
                read_all_today_titles,
            )
            from src.notifier.wework import WeWorkNotifier
            
            # 获取配置
            crawler_config = config.get_crawler_config()
            webhook_config = config.get_webhook_config()
            
            # 爬取数据 - 支持两种配置格式
            # platforms 可能在根级别或 crawler 下
            platforms_config = config.get("platforms", []) or crawler_config.get("platforms", [])
            if not platforms_config:
                logger.warning("未配置监控平台")
                return
            
            # 解析平台配置（支持新格式：[{"id": "...", "name": "..."}]）
            platforms = []
            for p in platforms_config:
                if isinstance(p, dict):
                    platforms.append((p["id"], p["name"]))
                else:
                    platforms.append(p)
            
            fetcher = DataFetcher()
            results, id_to_name, failed_ids = fetcher.crawl_websites(platforms)
            
            # 保存数据
            if results:
                save_titles_to_file(results, id_to_name, failed_ids)
            
            # 读取当天数据（按标题去重合并）
            all_results, final_id_to_name, title_info = read_all_today_titles(
                [p[0] if isinstance(p, tuple) else p for p in platforms]
            )
            
            # ========== 第1步：加载关键词并立即过滤 ==========
            word_groups, filter_words = load_frequency_words()
            all_keywords = []
            for g in word_groups:
                all_keywords.extend(g.get("required", []))
                all_keywords.extend(g.get("normal", []))
            
            matched_items = []
            for news_title, info in all_results.items():
                if not any(k in news_title for k in all_keywords):
                    continue
                url = (info.get("urls", [""]) or [""])[0]
                mobile_url = (info.get("mobileUrls", [""]) or [""])[0]
                sources = info.get("sources", [])
                source_name = final_id_to_name.get(sources[0], sources[0]) if sources else "未知"
                matched_items.append({
                    "title": news_title,
                    "url": url,
                    "mobile_url": mobile_url,
                    "source": source_name,
                    "ranks": info.get("ranks", []),
                })
            
            logger.info(f"关键词过滤: {len(all_results)}条 -> {len(matched_items)}条匹配")
            
            if not matched_items:
                logger.info("今日暂无匹配的活动策划相关新闻")
                notifier = WeWorkNotifier({"enabled": True, "webhook_url": webhook_config.get("wework_url", "")})
                notifier.send("📭 今日暂无匹配的活动策划相关新闻")
                return
            
            # ========== 第2步：事件去重（同事件合并为一条）==========
            llm_config = config.get("llm", {})
            from src.analyzer.llm_analyzer import LLMContentAnalyzer
            analyzer = LLMContentAnalyzer(llm_config)
            deduped_events = analyzer.deduplicate_events(matched_items)
            
            # ========== 第3步：信息扩充 + 大模型创意分析 + 推送 ==========
            wework_url = webhook_config.get("wework_url", "")
            wework_config = {
                "enabled": True if wework_url else False,
                "webhook_url": wework_url,
                "message_batch_size": config.get("push.message_batch_size", 4000),
            }
            
            notifier = WeWorkNotifier(wework_config)
            notifier.send_deduped_events(deduped_events, all_results, analyzer)
            
            logger.info("任务完成！")

    except FileNotFoundError as e:
        logger.error(f"配置文件错误: {e}")
        logger.error("\n请确保以下文件存在:")
        logger.error("  • config/config.yaml")
        logger.error("  • config/frequency_words.txt")
        logger.error("\n参考项目文档进行正确配置")
    except Exception as e:
        logger.error(f"程序运行错误: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()