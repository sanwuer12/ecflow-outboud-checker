#!/usr/bin/env python3
import os
import json
import time
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_driver():
    """配置并返回 Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 初始化WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_to_wms(driver, url, username, password):
    """登录到WMS系统"""
    try:
        logger.info(f"正在访问登录页面: {url}")
        driver.get(url)
        
        # 保存登录页面HTML用于调试
        login_html = driver.page_source
        with open("login_page.html", "w", encoding="utf-8") as f:
            f.write(login_html)
        logger.info("已保存登录页面HTML到 login_page.html")
        
        # 检查页面是否包含常见的登录元素
        logger.info(f"页面标题: {driver.title}")
        logger.info(f"当前URL: {driver.current_url}")
        
        # 等待登录表单加载
        logger.info("等待登录表单加载")
        try:
            # 尝试不同的输入字段选择器
            username_selectors = [
                (By.NAME, "username"),
                (By.ID, "username"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.XPATH, "//input[@placeholder='用户名']"),
                (By.XPATH, "//input[contains(@class, 'username')]")
            ]
            
            password_selectors = [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@placeholder='密码']"),
                (By.XPATH, "//input[contains(@class, 'password')]")
            ]
            
            username_field = None
            for selector_type, selector in username_selectors:
                try:
                    elements = driver.find_elements(selector_type, selector)
                    if elements:
                        logger.info(f"找到用户名输入框: {selector_type}={selector}")
                        username_field = elements[0]
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector_type}={selector} 失败: {str(e)}")
            
            if not username_field:
                logger.error("未找到用户名输入框")
                return False
                
            password_field = None
            for selector_type, selector in password_selectors:
                try:
                    elements = driver.find_elements(selector_type, selector)
                    if elements:
                        logger.info(f"找到密码输入框: {selector_type}={selector}")
                        password_field = elements[0]
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector_type}={selector} 失败: {str(e)}")
            
            if not password_field:
                logger.error("未找到密码输入框")
                return False
            
            # 输入用户名和密码
            logger.info("输入用户名和密码")
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            
            # 查找登录按钮
            button_selectors = [
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(text(), '登录')]"),
                (By.XPATH, "//button[contains(@class, 'login')]"),
                (By.CSS_SELECTOR, "button.ant-btn-primary"),
                (By.XPATH, "//span[contains(text(), '登录')]/parent::button")
            ]
            
            login_button = None
            for selector_type, selector in button_selectors:
                try:
                    elements = driver.find_elements(selector_type, selector)
                    if elements:
                        logger.info(f"找到登录按钮: {selector_type}={selector}")
                        login_button = elements[0]
                        break
                except Exception as e:
                    logger.warning(f"选择器 {selector_type}={selector} 失败: {str(e)}")
            
            if not login_button:
                logger.error("未找到登录按钮")
                return False
            
            # 点击登录按钮
            logger.info("点击登录按钮")
            driver.execute_script("arguments[0].click();", login_button)
            
            # 等待登录成功
            logger.info("等待登录成功")
            WebDriverWait(driver, 10).until(
                EC.url_changes(url)
            )
            
            # 保存登录后页面HTML用于调试
            after_login_html = driver.page_source
            with open("after_login_page.html", "w", encoding="utf-8") as f:
                f.write(after_login_html)
            logger.info("已保存登录后页面HTML到 after_login_page.html")
            
            logger.info(f"登录后页面标题: {driver.title}")
            logger.info(f"登录后URL: {driver.current_url}")
            
            logger.info("登录成功")
            return True
            
        except Exception as e:
            logger.error(f"登录表单处理失败: {str(e)}")
            import traceback
            logger.error(f"登录表单处理异常堆栈: {traceback.format_exc()}")
            return False
        
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return False

def navigate_to_outbound_dashboard(driver):
    """导航到出库看板页面"""
    try:
        # 等待页面加载完成
        logger.info("等待主页面加载完成")
        time.sleep(3)
        
        # 尝试多种可能的选择器来找到出库看板链接
        selectors = [
            "//a[contains(text(), '出货看板')]",
            "//a[contains(text(), '出库看板')]",
            "//span[contains(text(), '出货看板')]/parent::a",
            "//span[contains(text(), '出库看板')]/parent::a",
            "//div[contains(text(), '出货看板')]",
            "//div[contains(text(), '出库看板')]",
            "//li[contains(@class, 'ant-menu-item')]//span[contains(text(), '出库')]",
            "//li[contains(@class, 'ant-menu-item')]//span[contains(text(), '出货')]"
        ]
        
        # 记录页面源码以进行调试
        logger.info("页面标题: %s", driver.title)
        logger.info("当前URL: %s", driver.current_url)
        
        outbound_link = None
        for selector in selectors:
            try:
                logger.info(f"尝试选择器: {selector}")
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.info(f"找到 {len(elements)} 个匹配元素")
                    outbound_link = elements[0]
                    break
            except Exception as e:
                logger.warning(f"选择器 {selector} 失败: {str(e)}")
        
        if not outbound_link:
            # 如果没有找到链接，尝试直接访问URL
            logger.info("未找到出库看板链接，尝试直接访问URL")
            dashboard_urls = [
                # 可能的看板URL，根据实际情况调整
                driver.current_url + "outbound/dashboard",
                driver.current_url + "dashboard/outbound",
                driver.current_url + "outbound"
            ]
            
            for url in dashboard_urls:
                try:
                    logger.info(f"尝试访问URL: {url}")
                    driver.get(url)
                    time.sleep(2)
                    # 检查是否有表格元素出现
                    if len(driver.find_elements(By.CLASS_NAME, "ant-table-tbody")) > 0:
                        logger.info(f"成功通过URL导航到出库看板: {url}")
                        return True
                except Exception as e:
                    logger.warning(f"访问URL {url} 失败: {str(e)}")
            
            logger.error("无法找到或导航到出库看板")
            return False
        
        # 点击找到的链接
        logger.info("点击出库看板链接")
        driver.execute_script("arguments[0].click();", outbound_link)
        
        # 等待看板页面加载
        time.sleep(3)
        
        # 验证是否导航成功
        if len(driver.find_elements(By.CLASS_NAME, "ant-table-tbody")) > 0:
            logger.info("成功导航到出库看板页面")
            return True
        else:
            logger.error("导航后未找到表格数据")
            return False
            
    except Exception as e:
        logger.error(f"导航到出库看板页面失败: {str(e)}")
        return False

def extract_data(driver):
    """从页面提取数据"""
    try:
        # 等待表格加载完成
        logger.info("等待表格加载完成")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ant-table-tbody"))
        )
        
        # 获取页面HTML
        html = driver.page_source
        logger.info("已获取页面源代码")
        
        # 保存页面源代码用于调试
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("已保存页面源代码到 page_source.html")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 找到表格体 - 尝试多种选择器
        table_body = None
        selectors = [
            '.ant-table-tbody',
            'tbody.ant-table-tbody',
            '.ant-table .ant-table-tbody',
            'table tbody'
        ]
        
        for selector in selectors:
            logger.info(f"尝试选择器: {selector}")
            table_body = soup.select_one(selector)
            if table_body:
                logger.info(f"使用选择器 {selector} 找到了表格体")
                break
        
        if not table_body:
            logger.error("未找到表格数据，尝试使用Selenium直接获取")
            # 尝试使用Selenium直接获取表格行
            rows_elements = driver.find_elements(By.CSS_SELECTOR, "tr.ant-table-row")
            if not rows_elements:
                logger.error("使用Selenium也未找到表格行")
                return []
            
            # 使用Selenium提取数据
            data = []
            for i, row in enumerate(rows_elements[:3]):  # 只获取最近三天的数据
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, "td.ant-table-cell")
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
                except Exception as e:
                    logger.error(f"处理行 {i+1} 时出错: {str(e)}")
                    continue
            
            logger.info(f"使用Selenium成功提取了 {len(data)} 天的数据")
            return data
        
        # 使用BeautifulSoup提取行数据
        logger.info("使用BeautifulSoup提取数据")
        rows = table_body.select('tr.ant-table-row') or table_body.select('tr')
        logger.info(f"找到 {len(rows)} 行数据")
        
        data = []
        
        for i, row in enumerate(rows[:3]):  # 只获取最近三天的数据
            try:
                cells = row.select('td.ant-table-cell') or row.select('td')
                if len(cells) >= 7:  # 确保有足够的单元格
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
        
        # 处理空数据情况
        if not data:
            logger.warning("没有提取到数据，尝试查看页面内容")
            # 记录页面主要内容，帮助调试
            main_content = soup.select_one('main') or soup.select_one('body')
            if main_content:
                logger.info(f"页面主要内容: {main_content.text[:500]}...")
        
        return data
    except Exception as e:
        logger.error(f"提取数据失败: {str(e)}")
        # 获取堆栈跟踪信息
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
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
    
    driver = None
    max_retries = 3
    retry_count = 0
    data = []
    
    while retry_count < max_retries and not data:
        try:
            if retry_count > 0:
                logger.info(f"第 {retry_count} 次重试...")
            
            # 设置WebDriver
            if driver:
                driver.quit()
                logger.info("已关闭旧的WebDriver实例")
            
            driver = setup_driver()
            logger.info("WebDriver已初始化")
            
            # 登录WMS系统
            if not login_to_wms(driver, url, username, password):
                logger.error("登录失败，尝试重试")
                retry_count += 1
                continue
            
            # 导航到出库看板
            if not navigate_to_outbound_dashboard(driver):
                logger.error("导航到出库看板失败，尝试重试")
                retry_count += 1
                continue
            
            # 提取数据
            data = extract_data(driver)
            
            if not data:
                logger.error("未能提取到有效数据，尝试重试")
                retry_count += 1
                continue
            
            # 保存数据
            logger.info("成功获取数据，准备保存")
            
        except Exception as e:
            logger.error(f"运行过程中发生错误: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            retry_count += 1
            
            # 短暂休息后重试
            time.sleep(5)
        
        finally:
            # 在每次尝试结束时关闭WebDriver
            if driver and retry_count < max_retries - 1 and not data:
                driver.quit()
                logger.info("已关闭WebDriver，准备重试")
    
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
    
    # 确保关闭WebDriver
    if driver:
        driver.quit()
        logger.info("已关闭WebDriver")

if __name__ == "__main__":
    main()