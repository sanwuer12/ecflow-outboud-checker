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
        
        # 等待登录表单加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # 输入用户名和密码
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        
        # 点击登录按钮
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # 等待登录成功
        WebDriverWait(driver, 10).until(
            EC.url_changes(url)
        )
        
        logger.info("登录成功")
        return True
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return False

def navigate_to_outbound_dashboard(driver):
    """导航到出库看板页面"""
    try:
        # 等待页面加载完成
        time.sleep(2)
        
        # 查找并点击"出库看板"链接/按钮
        # 注意: 这里的选择器需要根据实际页面结构调整
        outbound_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '出货看板') or contains(., '出库看板')]"))
        )
        outbound_link.click()
        
        # 等待看板页面加载
        time.sleep(3)
        
        logger.info("成功导航到出库看板页面")
        return True
    except Exception as e:
        logger.error(f"导航到出库看板页面失败: {str(e)}")
        return False

def extract_data(driver):
    """从页面提取数据"""
    try:
        # 等待表格加载完成
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ant-table-tbody"))
        )
        
        # 获取页面HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # 找到表格体
        table_body = soup.select_one('.ant-table-tbody')
        
        if not table_body:
            logger.error("未找到表格数据")
            return []
        
        # 提取行数据
        rows = table_body.select('tr.ant-table-row')
        data = []
        
        for row in rows[:3]:  # 只获取最近三天的数据
            cells = row.select('td.ant-table-cell')
            if len(cells) >= 7:  # 确保有足够的单元格
                date_str = cells[0].text.strip()
                total_orders = cells[1].text.strip()
                outbound_count = cells[6].text.strip()
                
                data.append({
                    'date': date_str,
                    'total_orders': total_orders,
                    'outbound_count': outbound_count
                })
        
        logger.info(f"成功提取了 {len(data)} 天的数据")
        return data
    except Exception as e:
        logger.error(f"提取数据失败: {str(e)}")
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
    
    driver = None
    try:
        # 设置WebDriver
        driver = setup_driver()
        
        # 登录WMS系统
        if not login_to_wms(driver, url, username, password):
            return
        
        # 导航到出库看板
        if not navigate_to_outbound_dashboard(driver):
            return
        
        # 提取数据
        data = extract_data(driver)
        
        if data:
            # 保存数据
            save_to_json(data)
        else:
            logger.error("未能提取到有效数据")
    
    except Exception as e:
        logger.error(f"运行过程中发生错误: {str(e)}")
    
    finally:
        # 关闭WebDriver
        if driver:
            driver.quit()
            logger.info("已关闭WebDriver")

if __name__ == "__main__":
    main()