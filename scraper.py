#!/usr/bin/env python3
import os
import json
import time
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scrape_wms_data(url, username, password):
    """使用Playwright爬取WMS数据"""
    with sync_playwright() as playwright:
        logger.info("启动Playwright")
        
        # 使用Chromium浏览器
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # 访问登录页面
            logger.info(f"正在访问登录页面: {url}")
            page.goto(url)
            
            # 保存登录页面HTML用于调试
            login_html = page.content()
            with open("login_page.html", "w", encoding="utf-8") as f:
                f.write(login_html)
            logger.info("已保存登录页面HTML到 login_page.html")
            
            # 记录页面信息
            logger.info(f"页面标题: {page.title()}")
            logger.info(f"当前URL: {page.url}")
            
            # 查找并填写登录表单
            logger.info("尝试查找登录表单元素")
            
            # 尝试多种选择器找用户名输入框
            username_selectors = [
                "input[name='username']",
                "input#username",
                "input[type='text']",
                "input[placeholder='用户名']",
                "input.username"
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    if page.query_selector(selector):
                        logger.info(f"找到用户名输入框: {selector}")
                        username_input = selector
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector} 失败: {str(e)}")
            
            if not username_input:
                logger.error("未找到用户名输入框")
                return []
            
            # 尝试多种选择器找密码输入框
            password_selectors = [
                "input[name='password']",
                "input#password",
                "input[type='password']",
                "input[placeholder='密码']"
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    if page.query_selector(selector):
                        logger.info(f"找到密码输入框: {selector}")
                        password_input = selector
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector} 失败: {str(e)}")
            
            if not password_input:
                logger.error("未找到密码输入框")
                return []
            
            # 填写用户名和密码
            logger.info("填写用户名和密码")
            page.fill(username_input, username)
            page.fill(password_input, password)
            
            # 尝试多种选择器找登录按钮
            button_selectors = [
                "button[type='submit']",
                "button:has-text('登录')",
                "button.login",
                "button.ant-btn-primary",
                "button > span:has-text('登录')"
            ]
            
            login_button = None
            for selector in button_selectors:
                try:
                    if page.query_selector(selector):
                        logger.info(f"找到登录按钮: {selector}")
                        login_button = selector
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector} 失败: {str(e)}")
            
            if not login_button:
                logger.error("未找到登录按钮")
                return []
            
            # 点击登录
            logger.info("点击登录按钮")
            
            # 等待URL变化，表示登录成功
            with page.expect_navigation():
                page.click(login_button)
            
            logger.info("登录成功")
            logger.info(f"登录后页面标题: {page.title()}")
            logger.info(f"登录后URL: {page.url}")
            
            # 保存登录后页面源码
            after_login_html = page.content()
            with open("after_login_page.html", "w", encoding="utf-8") as f:
                f.write(after_login_html)
            logger.info("已保存登录后页面源码")
            
            # 寻找出库看板链接
            logger.info("尝试找到出库看板链接")
            dashboard_selectors = [
                "a:has-text('出货看板')",
                "a:has-text('出库看板')",
                "a > span:has-text('出货看板')",
                "a > span:has-text('出库看板')",
                "div:has-text('出货看板')",
                "div:has-text('出库看板')",
                ".ant-menu-item:has-text('出库')",
                ".ant-menu-item:has-text('出货')"
            ]
            
            dashboard_link = None
            for selector in dashboard_selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        logger.info(f"找到出库看板链接: {selector}")
                        dashboard_link = selector
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector} 失败: {str(e)}")
            
            # 尝试导航到出库看板
            if dashboard_link:
                logger.info("点击出库看板链接")
                # 等待导航完成
                with page.expect_navigation():
                    page.click(dashboard_link)
            else:
                # 尝试直接访问可能的URL
                logger.info("未找到出库看板链接，尝试直接访问URL")
                base_url = page.url
                dashboard_urls = [
                    f"{base_url}outbound/dashboard",
                    f"{base_url}dashboard/outbound",
                    f"{base_url}outbound"
                ]
                
                for dashboard_url in dashboard_urls:
                    try:
                        logger.info(f"尝试访问URL: {dashboard_url}")
                        page.goto(dashboard_url)
                        # 检查是否有表格
                        if page.query_selector(".ant-table-tbody"):
                            logger.info(f"成功通过URL导航到出库看板: {dashboard_url}")
                            break
                    except Exception as e:
                        logger.warning(f"访问URL {dashboard_url} 失败: {str(e)}")
            
            # 等待一下，确保页面加载完成
            page.wait_for_load_state("networkidle")
            
            # 保存页面源码
            dashboard_html = page.content()
            with open("dashboard_page.html", "w", encoding="utf-8") as f:
                f.write(dashboard_html)
            logger.info("已保存看板页面源码")
            
            # 检查是否有表格
            table_element = page.query_selector(".ant-table-tbody")
            if not table_element:
                logger.error("未找到数据表格")
                return []
            
            # 提取数据
            logger.info("开始提取数据")
            
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(dashboard_html, 'html.parser')
            
            # 查找表格行
            rows = soup.select("tr.ant-table-row") or soup.select(".ant-table-tbody tr")
            
            if not rows:
                logger.error("未找到表格行")
                return []
            
            logger.info(f"找到 {len(rows)} 行数据")
            
            # 提取前三行的数据
            data = []
            for i, row in enumerate(rows[:3]):
                try:
                    cells = row.select("td.ant-table-cell") or row.select("td")
                    if len(cells) >= 7:
                        date_str = cells[0].text.strip()
                        total_orders = cells[1].text.strip()
                        outbound_count = cells[6].text.strip()
                        
                        logger.info(f"行 {i+1}: 日期={date_str}, 订单总数={total_orders}, 已出库={outbound_count}")
                        
                        data.append({
                            'date': date_str,
                            'total_orders': total_orders,
                            'outbound_count': outbound_count
                        })
                    else:
                        logger.warning(f"行 {i+1} 单元格数量不足: {len(cells)}")
                except Exception as e:
                    logger.error(f"处理行 {i+1} 时出错: {str(e)}")
                    continue
            
            logger.info(f"成功提取了 {len(data)} 天的数据")
            return data
            
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
    url = os.environ.get('URL')
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    
    if not all([url, username, password]):
        logger.error("环境变量未设置完全，请确保设置了 WMS_URL, WMS_USERNAME, WMS_PASSWORD")
        return
    
    logger.info(f"使用URL: {url}")
    logger.info(f"用户名: {username}")
    logger.info("密码已设置")
    
    # 进行多次尝试
    max_retries = 3
    data = []
    
    for retry_count in range(max_retries):
        if retry_count > 0:
            logger.info(f"第 {retry_count+1} 次尝试...")
            time.sleep(3)  # 暂停几秒后重试
        
        # 爬取数据
        data = scrape_wms_data(url, username, password)
        
        if data:
            logger.info("成功获取数据")
            break
        else:
            logger.error(f"第 {retry_count+1} 次尝试失败")
    
    # 处理最终结果
    if data:
        # 保存数据
        save_to_json(data)
        logger.info("脚本执行成功")
    elif os.path.exists('data.json'):
        # 如果仍然没有数据但data.json存在，尝试添加错误信息
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # 添加错误信息但保留原有数据
            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['error'] = f"数据获取失败，显示的是上次成功获取的数据"
            
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            logger.info("已更新现有data.json文件，添加了错误信息")
        except Exception as e:
            logger.error(f"更新现有data.json失败: {str(e)}")
    else:
        # 如果没有data.json，创建一个带错误信息的文件
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