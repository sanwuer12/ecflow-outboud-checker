#!/usr/bin/env python3
import os
import json
import time
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_wms_data(url, username, password):
    """使用Playwright爬取WMS数据"""
    with sync_playwright() as playwright:
        logger.info("启动Playwright")
        
        # 使用Firefox浏览器，设置为非headless模式
        browser = playwright.firefox.launch(headless=True)  # 改为headless模式
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # 访问登录页面
            logger.info(f"正在访问登录页面: {url}")
            page.goto(url)
            
            # 等待登录表单加载
            logger.info("等待登录表单加载")
            page.wait_for_selector("form#ec_login", timeout=10000)
            
            # 填写登录表单
            logger.info("填写登录表单")
            page.fill("input[name='userName']", username)
            page.fill("input[name='userPass']", password)
            
            # 点击登录按钮
            logger.info("点击登录按钮")
            page.click("input#login[value='立即登录']")
            
            # 等待登录成功和页面加载
            logger.info("等待登录成功和页面加载")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)  # 等待3秒确保页面完全加载
            
            # 等待并切换到iframe
            logger.info("等待iframe加载")
            iframe = page.wait_for_selector("iframe", timeout=10000)
            if not iframe:
                logger.error("未找到iframe")
                return []
            
            frame = page.frames[1]  # 第二个frame是我们需要的
            if not frame:
                logger.error("未找到目标frame")
                return []
            
            logger.info(f"切换到frame: {frame.url}")
            
            # 等待数据加载
            logger.info("等待数据加载")
            frame.wait_for_load_state("networkidle")
            frame.wait_for_timeout(3000)  # 减少等待时间
            
            # 提取数据
            data = extract_table_data(frame)
            
            if data:
                logger.info("成功获取数据")
                return data
            else:
                logger.error("未能获取到数据")
                return []
            
        except Exception as e:
            logger.error(f"爬取过程中出错: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return []
        
        finally:
            # 关闭浏览器
            context.close()
            browser.close()
            logger.info("浏览器已关闭")

def extract_table_data(frame):
    """从页面HTML中提取表格数据"""
    logger.info("等待数据面板加载")
    
    try:
        # 等待主要内容区域加载
        logger.info("等待内容区域出现")
        frame.wait_for_selector("div.common.one", timeout=10000)
        logger.info("内容区域已加载")
        
        # 等待内容更新（等待表格加载）
        logger.info("等待表格数据加载")
        frame.wait_for_timeout(2000)  # 减少等待时间
        
        # 检查表格是否存在
        table_selector = "div.common.one table tbody"
        table_container = frame.query_selector(table_selector)
        
        if not table_container:
            logger.error(f"未找到表格容器: {table_selector}")
            return []
        
        logger.info("找到表格容器，开始提取数据")
        data = []
        
        # 获取前3行数据
        for row in range(2, 5):  # 2,3,4 分别对应第1,2,3行
            try:
                # 使用更简单的选择器
                date_selector = f"div.common.one table tbody tr:nth-child({row}) td:nth-child(1)"
                total_selector = f"div.common.one table tbody tr:nth-child({row}) td:nth-child(2)"
                outbound_selector = f"div.common.one table tbody tr:nth-child({row}) td:nth-child(7)"
                
                date_element = frame.query_selector(date_selector)
                total_element = frame.query_selector(total_selector)
                outbound_element = frame.query_selector(outbound_selector)
                
                if date_element and total_element and outbound_element:
                    date_str = date_element.inner_text().strip()
                    total_orders = total_element.inner_text().strip()
                    outbound_count = outbound_element.inner_text().strip()
                    
                    logger.info(f"获取数据: 日期={date_str}, 订单总数={total_orders}, 已出库={outbound_count}")
                    
                    data.append({
                        'date': date_str,
                        'total_orders': total_orders,
                        'outbound_count': outbound_count
                    })
                else:
                    logger.warning(f"行 {row-1} 某些单元格未找到")
            except Exception as e:
                logger.error(f"处理行 {row-1} 时出错: {str(e)}")
                continue
        
        logger.info(f"成功提取了 {len(data)} 天的数据")
        return data
        
    except Exception as e:
        logger.error(f"等待内容加载时出错: {str(e)}")
        return []

def save_to_json(data, filename='data.json'):
    """将数据保存到JSON文件"""
    try:
        # 添加更新时间戳
        output = {
            'last_updated': datetime.now().isoformat(),
            'data': data
        }
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据已保存到 {filename}")
        return True
    except Exception as e:
        logger.error(f"保存数据失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 从环境变量获取登录信息
    url = os.environ.get('WMS_URL')
    username = os.environ.get('WMS_USERNAME')
    password = os.environ.get('WMS_PASSWORD')
    
    if not all([url, username, password]):
        logger.error("环境变量未设置完全，请确保设置了 WMS_URL, WMS_USERNAME, WMS_PASSWORD")
        return
    
    logger.info(f"使用URL: {url}")
    logger.info(f"用户名: {username}")
    logger.info("密码已设置")
    
    # 爬取数据
    data = scrape_wms_data(url, username, password)
    
    # 保存数据
    if data:
        save_to_json(data)
        logger.info("脚本执行成功")
    else:
        error_data = {
            'last_updated': datetime.now().isoformat(),
            'error': "获取数据失败，请检查日志",
            'data': []
        }
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)
        
        logger.error("创建了带有错误信息的data.json")

if __name__ == "__main__":
    main()