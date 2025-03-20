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
        
        # 使用Chromium浏览器
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        try:
            # 访问登录页面
            logger.info(f"正在访问登录页面: {url}")
            page.goto(url)
            
            # 填写登录表单
            logger.info("填写登录表单")
            page.fill("input[type='text']", username)
            page.fill("input[type='password']", password)
            
            # 点击登录按钮
            logger.info("点击登录按钮")
            page.click("input[type='submit']")
            
            # 等待登录成功
            logger.info("等待登录成功")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # 等待5秒确保页面完全加载
            
            # 等待可能的弹窗并关闭
            logger.info("检查是否有弹窗")
            try:
                close_button = page.wait_for_selector("button.ant-btn-primary", timeout=5000)
                if close_button:
                    close_button.click()
                    logger.info("关闭了弹窗")
                    page.wait_for_timeout(2000)  # 等待弹窗完全关闭
            except:
                logger.info("没有发现弹窗")
            
            # 等待页面加载完成
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # 再等待5秒确保数据加载完成
            
            # 尝试点击出货管理菜单
            logger.info("尝试点击出货管理菜单")
            try:
                outbound_menu = page.get_by_text("出货管理")
                if outbound_menu:
                    outbound_menu.click()
                    logger.info("点击了出货管理菜单")
                    page.wait_for_timeout(2000)
            except:
                logger.warning("未找到出货管理菜单")
            
            # 尝试点击订单下架菜单
            logger.info("尝试点击订单下架菜单")
            try:
                order_menu = page.get_by_text("订单下架")
                if order_menu:
                    order_menu.click()
                    logger.info("点击了订单下架菜单")
                    page.wait_for_timeout(2000)
            except:
                logger.warning("未找到订单下架菜单")
            
            # 等待页面加载完成
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # 再等待5秒确保数据加载完成
            
            # 保存页面源码用于调试
            page_html = page.content()
            with open("page.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            logger.info("已保存页面源码用于调试")
            
            # 提取数据
            data = extract_table_data(page, page_html)
            
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
            # 保存最终页面截图
            try:
                page.screenshot(path="final.png")
                logger.info("保存了最终页面截图")
            except:
                pass
            
            # 关闭浏览器
            context.close()
            browser.close()
            logger.info("浏览器已关闭")

def extract_table_data(page, html):
    """从页面HTML中提取表格数据"""
    logger.info("尝试提取表格数据")
    
    base_selector = "#root > div > div.right > div > div > div.common.one > div.ant-table-wrapper > div > div > div > div > div.ant-table-body > table > tbody"
    data = []
    
    # 检查表格容器是否存在
    table_container = page.query_selector(base_selector)
    if not table_container:
        logger.error(f"未找到表格容器: {base_selector}")
        return []
    
    logger.info("找到表格容器")
    
    # 获取前3行数据
    for row in range(2, 5):  # 2,3,4 分别对应第1,2,3行
        try:
            # 获取日期
            date_selector = f"{base_selector} > tr:nth-child({row}) > td:nth-child(1)"
            # 获取订单总数
            total_selector = f"{base_selector} > tr:nth-child({row}) > td:nth-child(2)"
            # 获取已出库数量
            outbound_selector = f"{base_selector} > tr:nth-child({row}) > td:nth-child(7)"
            
            logger.info(f"尝试获取第{row-1}行数据")
            logger.info(f"日期选择器: {date_selector}")
            logger.info(f"订单总数选择器: {total_selector}")
            logger.info(f"已出库选择器: {outbound_selector}")
            
            date_element = page.query_selector(date_selector)
            total_element = page.query_selector(total_selector)
            outbound_element = page.query_selector(outbound_selector)
            
            if date_element and total_element and outbound_element:
                date_str = date_element.inner_text().strip()
                total_orders = total_element.inner_text().strip()
                outbound_count = outbound_element.inner_text().strip()
                
                logger.info(f"行 {row-1}: 日期={date_str}, 订单总数={total_orders}, 已出库={outbound_count}")
                
                data.append({
                    'date': date_str,
                    'total_orders': total_orders,
                    'outbound_count': outbound_count
                })
            else:
                logger.warning(f"行 {row-1} 某些单元格未找到")
                if not date_element:
                    logger.warning("未找到日期单元格")
                if not total_element:
                    logger.warning("未找到订单总数单元格")
                if not outbound_element:
                    logger.warning("未找到已出库单元格")
        except Exception as e:
            logger.error(f"处理行 {row-1} 时出错: {str(e)}")
            continue
    
    logger.info(f"成功提取了 {len(data)} 天的数据")
    return data

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
        logger.error("环境变量未设置完全，请确保设置了 URL, USERNAME, PASSWORD")
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