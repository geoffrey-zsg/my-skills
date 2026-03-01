# 抖音文案提取 Skill

从抖音视频链接自动提取文案内容，支持语音识别转文字并格式化输出。

## 功能特点

- 🔗 支持抖音短链 (`v.douyin.com`) 和长链 (`douyin.com/video/xxx`)
- 📋 自动从分享文本中提取链接
- 🎯 使用 Playwright + Cookie 登录态绕过反爬
- 🎙️ 基于 SiliconFlow Whisper 语音识别
- 📝 支持多种输出格式：Markdown / 纯文本 / JSON

## 前置要求

1. **Python 3.10+**
2. **依赖安装**: `pip install -r requirements.txt`
3. **Playwright**: `python -m playwright install chromium`
4. **抖音 Cookie**: 导出登录后的 `cookies.txt` 到项目根目录
5. **API Key**: 获取 [SiliconFlow](https://siliconflow.cn) API Key

## 安装

```bash
# 克隆 douyin 项目（此 Skill 依赖完整项目）
git clone https://github.com/geoffrey-zsg/douyin.git
cd douyin

# 安装依赖
pip install -r requirements.txt
python -m playwright install chromium

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 SILICONFLOW_API_KEY

# 导出抖音 Cookie（使用 Get cookies.txt LOCALLY 扩展）
# 保存为 cookies.txt 放在项目根目录
```

## 使用方法

### 方式一：直接使用 CLI

```bash
# 默认 Markdown 格式输出
python skill_extract.py "https://v.douyin.com/xxxxx"

# 纯文本格式
python skill_extract.py "<链接>" --format plain

# JSON 格式（含字数统计）
python skill_extract.py "<链接>" --format json

# 从分享文本自动提取链接
python skill_extract.py "8.41 复制打开抖音 https://v.douyin.com/xxxxx/ 看更多..."
```

### 方式二：Python 调用

```python
from skill_extract import extract_douyin_transcript
import asyncio

result = asyncio.run(extract_douyin_transcript(
    "https://v.douyin.com/xxxxx",
    format_type="markdown"
))
print(result)
```

### 方式三：在 Claude Code 中使用

将此 skill 复制到 `.claude/skills/douyin-extract.json`，然后在对话中：

> "提取这个抖音链接的文案 https://v.douyin.com/xxxxx"

## 输出示例

```markdown
# 视频文案

## 段落 1
来做一个消费测试，给你2秒钟，你看到的是什么？
如果你看到的是A一个吃剩的苹果，那么你是...

## 段落 2
这就是巴纳姆效应。因为它会轻易让人产生一种懂我感，
于是就成了品牌营销中一个重要的策略方法...

---
*字数: 1153*
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `skill_extract.py` | Skill 主程序，提供 CLI 和 Python API |
| `bin/douyin-extract` | Linux/Mac 快捷入口 |
| `bin/douyin-extract.bat` | Windows 快捷入口 |

## 注意事项

- Cookie 有效期约 30-60 天，过期需重新导出
- 部分视频仅限 App 查看，无法提取
- 首次运行需下载 Chromium，耗时较长
- 提取过程约 20-60 秒（取决于视频长度）

## 依赖项目

此 Skill 依赖完整的 [douyin](https://github.com/geoffrey-zsg/douyin) 项目：
- `services/extractor.py` - 视频提取逻辑
- `services/transcriber.py` - 语音识别
- `config.yaml` - 配置文件

## License

MIT
