---
name: project-init
description: 初始化空白项目。当用户说"创建空白项目"、"初始化新项目"、"建立新仓库"、"新建项目目录"或类似请求时触发。自动创建项目目录、初始化 git、生成基础文件，并可选地创建 GitHub 远程仓库。即使用户没有明确说"skill"或"project-init"，只要提到创建新项目、初始化项目等意图，都应该使用这个 skill。
---

# Project Init

快速初始化一个空白项目，包含 git 仓库、基础文件和可选的 GitHub 远程仓库。

## ⚠️ 重要提醒

**执行此 skill 前，必须先完整阅读本文档，严格按照步骤 1-7 执行，不要遗漏任何文件！**

特别注意：
- 必须创建 `.claude/settings.local.json` 配置文件（步骤 4）
- 不要创建 `.claude/CLAUDE.md` 文件（未在步骤中定义）
- 严格按照文档中的文件内容模板创建文件

## 工作流程

### 1. 收集项目信息

询问用户以下信息：
- **项目名称**（project-name）：将作为目录名
- **项目根目录**：项目将在哪个目录下创建（例如：`~/projects`、`C:\workspace`）
- **项目描述**（可选）：用于 README 和 GitHub 仓库描述

### 2. 创建项目目录

在指定的根目录下创建项目文件夹：
```bash
mkdir -p <root-directory>/<project-name>
cd <root-directory>/<project-name>
```

### 3. 初始化 Git 仓库

```bash
git init
```

### 4. 创建基础文件

创建以下基础文件：

**README.md**：
```markdown
# <project-name>

<project-description>

## 项目说明

这是一个新建的项目。

## 开始使用

待补充...
```

**.gitignore**（通用模板）：
```
# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp

# Environment
.env
.env.local

# Dependencies (common)
node_modules/
vendor/
__pycache__/
*.pyc
.pytest_cache/

# Build outputs
dist/
build/
*.egg-info/
```

**.claude/settings.local.json**（Claude 配置文件）：
```json
{
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read(*)",
      "Write(*)",
      "Edit(*)",
      "Glob(*)",
      "Grep(*)",
      "WebFetch",
      "WebSearch",
      "Bash(git push *)",
      "Bash(git push)",
      "Bash(npm *)",
      "Bash(pnpm *)",
      "Skill(agent-browser)"
    ],
    "deny": [
      "Read(.env*)",
      "Read(**/.env*)",
      "Read(~/.ssh/**)",
      "Bash(rm *)",
      "Bash(del *)",
      "Bash(rmdir *)"
    ]
  }
}
```

### 5. 创建初始提交

```bash
git add .
git commit -m "chore: 初始化项目

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### 6. GitHub 远程仓库（可选）

询问用户："是否需要创建 GitHub 远程仓库？"

如果用户选择是：

1. 使用 `gh` CLI 创建远程仓库（默认 public）：
```bash
gh repo create <project-name> --public --source=. --remote=origin --description="<project-description>"
```

2. 推送初始代码：
```bash
git push -u origin main
```

如果用户没有安装 `gh` CLI，提示用户：
- 安装方法：访问 https://cli.github.com/
- 或者手动在 GitHub 网站创建仓库后，使用以下命令关联：
```bash
git remote add origin https://github.com/<username>/<project-name>.git
git push -u origin main
```

### 7. 完成确认

告知用户项目已创建完成，显示：
- 项目路径
- Git 状态
- 如果创建了 GitHub 仓库，显示仓库 URL

## 注意事项

- 在创建目录前，检查目标路径是否已存在同名目录，如果存在则警告用户
- 确保用户有权限在指定的根目录下创建文件夹
- 如果 `gh` 命令失败，提供手动创建 GitHub 仓库的指导
- 项目描述如果用户不提供，可以使用默认值："A new project"

## 错误处理

- 如果目录已存在：询问用户是否要使用不同的名称或在现有目录中初始化
- 如果 git 未安装：提示用户安装 git
- 如果 gh 未安装但用户想创建 GitHub 仓库：提供安装指导或手动创建步骤
