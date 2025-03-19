# WMS出库数据自动获取工具

这个项目会自动从WMS系统获取出库看板数据，并通过GitHub Pages展示最近三天的出库数据。

## 功能特点

- 定时（每30分钟）自动爬取WMS系统数据
- 提取最近三天的日期、订单总数和出库数量
- 数据自动保存到仓库中的data.json文件
- 移动端友好的页面展示，随时查看最新数据
- 支持手动刷新数据

## 技术栈

- Python (Selenium, BeautifulSoup)
- GitHub Actions (定时任务)
- GitHub Pages (数据展示)
- HTML/CSS/JavaScript (前端页面)

## 设置说明

1. 在GitHub仓库的Settings -> Secrets and variables -> Actions中添加以下秘密变量：
   - `WMS_URL`: WMS系统登录URL
   - `WMS_USERNAME`: 登录用户名
   - `WMS_PASSWORD`: 登录密码

2. 启用GitHub Pages，选择从main分支的根目录发布

3. 访问部署的GitHub Pages页面查看数据

## 手动触发更新

如需手动触发数据更新，可以在Actions选项卡中手动运行"定时爬取WMS数据"工作流。

## 本地开发

如需本地运行爬虫脚本：

```bash
# 安装依赖
pip install selenium beautifulsoup4 requests webdriver-manager

# 设置环境变量
export WMS_URL="你的WMS系统URL"
export WMS_USERNAME="你的用户名"
export WMS_PASSWORD="你的密码"

# 运行脚本
python scraper.py
```