---
name: notion-writer
description: "Write content to a Notion page. Use this skill whenever the user wants to write/export/sync a local markdown or Obsidian file to Notion, organize the current conversation and write it to Notion, or summarize chat history into a Notion doc. Trigger on phrases like '写入notion', '同步到notion', '发到notion', '整理成md写入notion', '把我们的对话写进notion', '记录到notion', 'put this in Notion', 'save to Notion', 'export to Notion', 'write our conversation to Notion'. Always activate this skill even if the user does not say 'skill'."
---

# Notion Writer

把内容写入 Notion 页面，支持两种输入模式：
- **文件模式**：本地 Markdown / Obsidian 文件
- **对话模式**：将当前对话内容整理后写入

---

## 前置：获取 Notion Token

自动从 `~/.mcp.json` 读取，无需用户手动提供：

```bash
python "~/.claude/skills/notion-writer/scripts/notion_writer.py" get-token
```

若读取失败，再向用户索要（格式 `ntn_...` 或 `secret_...`，来自 https://www.notion.so/my-integrations）。

---

## 模式一：文件模式

用户提供本地文件路径时使用。

**触发信号**：用户给出了文件路径，如 `E:\workspace\obsidian\work\xxx.md`

### 步骤

**1. 确认文件路径**
直接使用用户给出的路径；若未给出，询问完整路径。

**2. 查找父页面**（见"查找父页面"小节）

**3. 调用脚本**
```bash
python "~/.claude/skills/notion-writer/scripts/notion_writer.py" create \
  --file "<FILE_PATH>" \
  --parent-id <PARENT_PAGE_ID>
```
可选 `--title "自定义标题"` 覆盖文件内的 H1 标题。

---

## 模式二：对话模式

用户想把当前对话内容整理后写入 Notion 时使用。

**触发信号**：用户说"把我们的对话/沟通/聊天内容整理一下写入 Notion"，或"把刚才讨论的内容记录到 Notion"。

### 步骤

**1. 整理对话内容为 Markdown**

阅读完整对话历史，将其整理成结构清晰的 Markdown 文档：
- 提炼标题（反映本次对话的核心主题）
- 用 `##` 划分主要话题或阶段
- 保留关键决策、结论、代码片段、操作步骤
- 去除无关的寒暄、重复内容和中间错误尝试
- 如有代码，放入 ` ``` ` 代码块并标明语言

整理质量很重要——目标是让读者无需看原始对话就能理解全部内容。

**2. 写入临时文件**

将整理好的 Markdown 写入临时文件：
```
~/.claude/skills/notion-writer/_temp_upload.md
```
（使用 Write 工具写入，路径固定，避免残留多个临时文件。）

**3. 查找父页面**（见"查找父页面"小节）

**4. 调用脚本**
```bash
python "~/.claude/skills/notion-writer/scripts/notion_writer.py" create \
  --file "~/.claude/skills/notion-writer/_temp_upload.md" \
  --parent-id <PARENT_PAGE_ID>
```

**5. 清理临时文件**

上传成功后删除临时文件：
```bash
rm "~/.claude/skills/notion-writer/_temp_upload.md"
```

---

## 查找父页面

两种模式共用此步骤：

```bash
python "~/.claude/skills/notion-writer/scripts/notion_writer.py" search
```

输出 JSON 列表，每项含 `id` 和 `title`：

- **只有一个页面**：自动使用，告知用户："将创建在「{title}」页面下。"
- **多个页面**：列出供用户选择，等待确认。
- **没有页面**：提示用户去 Notion 将目标页面共享给 Integration，再重试。

---

## 汇报结果

脚本输出 JSON，据此告知用户：

```
✅ 已写入 Notion！
📄 标题：{title}
🔗 链接：{page_url}
📦 共 {total_blocks} 个内容块
```

---

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| HTTP 400 validation_error | 父页面 ID 有误，或 Integration 无权访问 | 让用户去 Notion 共享该页面给 Integration |
| HTTP 401 unauthorized | Token 无效或已过期 | 让用户提供新 Token |
| HTTP 404 object_not_found | 父页面不存在 | 让用户提供有效页面链接 |
| FileNotFoundError | 文件路径不存在 | 确认路径是否正确 |

---

## 支持的 Markdown 元素

`# ## ###` 标题 / `> ` 引用 / ` ``` ` 代码块（自动识别语言） / `- * +` 无序列表 / `1.` 有序列表 / `- [ ] - [x]` 待办 / `---` 分隔线 / `**粗体**` / `` `行内代码` `` / 普通段落
