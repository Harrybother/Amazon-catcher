# 🧭 Fire-Maple Amazon 商品信息采集工具

## 已更新英美澳站点脚本，该说明依然以澳洲站为例。

这是一个用于采集 **Amazon** 上商品信息的轻量级爬虫工具。  
它可以批量抓取商品详情，包括价格、排名、评论、卖家、是否 FBA 发货等信息，并输出为带有缩略图的 Excel 文件。

---

## ✨ 功能特点

- 🔗 批量抓取指定商品链接（来自 `urls.txt`）
- 🖼️ 自动提取商品主图（Excel 文件中会显示缩略图）
- 💲 抓取价格、排名、评分、评论数
- 🏬 自动识别并清洗卖家名称（去掉“Sold by”等冗余）
- 🚚 判断是否 FBA（由 Amazon 发货）
- 📊 输出为：
  - `firemaple_playwright.csv`
  - `firemaple_playwright.xlsx`（带图片预览）

---

## 💻 环境安装步骤（非程序员也能轻松完成）

### 🪟 1. 安装 Python（如果你的电脑没有）

1. 打开 [Python 官方网站](https://www.python.org/downloads/)
2. 下载 **Windows Installer（64-bit）**
3. 运行安装程序，**务必勾选 “Add Python to PATH”**
4. 点击 “Install Now”，等待几分钟即可。

> ✅ 验证是否安装成功：  
> 打开命令提示符（Win+R → 输入 `cmd` → 回车），输入：
> ```bash
> python --version
> ```
> 如果显示出版本号（例如 Python 3.11.5），说明安装成功。

---

### 📦 2. 安装依赖库

打开命令提示符（或终端），进入项目文件夹：
```bash
cd 桌面\火枫
```

然后复制粘贴以下命令并回车（一次安装好全部依赖）：

```bash
pip install playwright beautifulsoup4 lxml pandas openpyxl pillow requests tqdm
python -m playwright install chromium
```

解释一下上面命令做的事：
- `pip install ...`：安装本程序需要的工具包；
- `playwright install chromium`：下载一个小型的浏览器供程序使用。

这一步只需要做一次，之后不用重复。

---

### 🧾 3. 准备链接文件

在同目录下创建一个文本文件：  
文件名为 `urls.txt`，内容示例：

```
https://www.amazon.com.au/dp/B07YXZB8F5
https://www.amazon.com.au/dp/B0C9T1WT9D
https://www.amazon.com.au/dp/B0B1PYD29Q
```

每一行一个商品链接。

---

### 🚀 4. 运行程序

在命令提示符中运行：

```bash
python firemaple_playwright.py
```

运行后程序会自动打开浏览器并提示：

```
🔹 正在打开 Amazon AU 首页，请手动将收货地址修改为澳洲（建议邮编 2000）
👉 修改完成后返回终端按 Enter 键继续抓取...
```

此时请在浏览器中：
1. 手动将 Amazon 地址切换为澳大利亚（邮编 2000）；  
2. 设置完成后回到终端按 Enter 继续。

程序会依次抓取每个链接，大约每个页面耗时 3~5 秒。

---

## 📊 5. 查看结果

完成后会生成两个文件：

| 文件名 | 说明 |
|:--|:--|
| `firemaple_playwright.csv` | 原始数据表（纯文本） |
| `firemaple_playwright.xlsx` | 含图片缩略图的可视化表格 |

### Excel 文件示例：

| 产品图片 | 链接 | 价格 | 评分 | 店铺名称 | 是否FBA |
|-----------|------|------|------|----------|-----------|
| （缩略图） | https://www.amazon.com.au/dp/B07YXZB8F5 | $79.99 | 4.8 | Conglin AU | 是 |

💡 Excel 文件中，程序会自动下载主图并嵌入单元格中，如图片下载失败则留空。

---

## ⚠️ 常见问题

| 问题 | 原因 | 解决办法 |
|:--|:--|:--|
| 程序打开浏览器后无反应 | 在等你手动修改 Amazon 地址 | 改成澳洲邮编 2000，回到终端按 Enter |
| 输出中价格为空 | Amazon 页面结构略有变化 | 稍后再试或换其他链接 |
| 显示 “疑似风控/验证码页面” | Amazon 临时防爬机制 | 关闭浏览器稍等几分钟再运行 |
| Excel 图片不显示 | 旧版 Excel 不支持 | 建议使用 Office 2019+ 或 WPS |

---

## 🧩 后续可拓展功能（计划中）

- 🔍 支持关键词搜索（自动分页抓取）
- ⚡ 多线程异步模式（显著提速）
- 🔁 自动重试验证码页面
- 🧱 输出分 Sheet（按卖家或品牌分类）

---

## 🏁 一句话总结

> Fire-Maple Amazon AU Scraper 让你无需手动复制粘贴，  
> 一键批量获取所有 Fire-Maple 商品的详细信息和图片，  
> 生成干净、可直接汇报或上架分析用的 Excel 文件。

---

作者：虎哥
版本：v1.3 (2025.11)
