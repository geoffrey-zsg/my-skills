# my-skills

AI 写作过程中为提效制作的 Claude Code Skills 集合，统一维护，多端同步。

## 安装方式

### 方式一：克隆到全局 skills 目录（推荐，一次配置永久同步）

```bash
# 首次安装
git clone https://github.com/geoffrey-zsg/my-skills ~/.claude/skills

# 后续更新
cd ~/.claude/skills && git pull
```

### 方式二：只安装某个 skill

```bash
cd ~/.claude/skills
git clone --filter=blob:none --no-checkout https://github.com/geoffrey-zsg/my-skills temp-clone
cd temp-clone && git sparse-checkout set notion-writer && git checkout
cp -r notion-writer ../
cd .. && rm -rf temp-clone
```

---

## Skills 列表

| Skill | 功能 | 触发词 |
|-------|------|--------|
| [notion-writer](./notion-writer/) | 将本地 Markdown 文件或对话内容写入 Notion | `写入notion`、`同步到notion`、`把对话整理写入notion` |

---

## 注意事项

- 每台电脑需要单独配置 `~/.mcp.json`（含 Notion API Token），不要提交到仓库
- Skills 依赖 Python 3（标准库，无需额外安装）
