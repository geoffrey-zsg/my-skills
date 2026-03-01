#!/usr/bin/env python3
"""
Notion Writer - Convert and upload local Markdown files to Notion pages.
Usage:
  python notion_writer.py get-token
  python notion_writer.py search --token <TOKEN>
  python notion_writer.py create --token <TOKEN> --file <PATH> --parent-id <ID> [--title <TITLE>]
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

LANG_MAP = {
    'ts': 'typescript', 'typescript': 'typescript',
    'js': 'javascript', 'javascript': 'javascript',
    'jsx': 'javascript', 'tsx': 'typescript',
    'css': 'css', 'scss': 'scss', 'less': 'less',
    'bash': 'bash', 'sh': 'shell', 'shell': 'shell',
    'zsh': 'shell', 'fish': 'shell', 'powershell': 'powershell',
    'python': 'python', 'py': 'python',
    'markdown': 'markdown', 'md': 'markdown',
    'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
    'toml': 'toml', 'html': 'html', 'xml': 'xml',
    'sql': 'sql', 'graphql': 'graphql',
    'rust': 'rust', 'go': 'go', 'java': 'java',
    'kotlin': 'kotlin', 'swift': 'swift',
    'c': 'c', 'cpp': 'c++', 'c++': 'c++',
    'cs': 'c#', 'c#': 'c#',
    'ruby': 'ruby', 'rb': 'ruby', 'php': 'php',
    'r': 'r', 'dart': 'dart', 'lua': 'lua',
    'dockerfile': 'docker', 'docker': 'docker',
    'makefile': 'makefile',
    '': 'plain text',
}


def map_lang(lang: str) -> str:
    return LANG_MAP.get(lang.lower().strip(), 'plain text')


def api_request(token: str, method: str, path: str, data=None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    body = json.dumps(data, ensure_ascii=False).encode('utf-8') if data else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8')
        raise Exception(f"HTTP {e.code}: {err}")


def make_rich_text(text: str) -> list:
    """Convert text with **bold** and `code` markers to Notion rich_text array."""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]

    parts = []
    # Split on ** for bold sections
    bold_segments = re.split(r'\*\*', text)
    for bidx, seg in enumerate(bold_segments):
        if not seg:
            continue
        is_bold = (bidx % 2 == 1)
        # Within each segment, split on `code`
        code_parts = re.split(r'`([^`]+)`', seg)
        for cidx, cp in enumerate(code_parts):
            if not cp:
                continue
            is_code = (cidx % 2 == 1)
            ann = {}
            if is_bold:
                ann['bold'] = True
            if is_code:
                ann['code'] = True
            entry = {"type": "text", "text": {"content": cp}}
            if ann:
                entry["annotations"] = ann
            parts.append(entry)

    return parts if parts else [{"type": "text", "text": {"content": text}}]


def parse_markdown(content: str):
    """Parse markdown and return (title, blocks)."""
    lines = content.split('\n')
    blocks = []
    i = 0
    title = 'Untitled'

    # Extract title from first H1
    if lines and lines[0].startswith('# '):
        title = lines[0][2:].strip()
        i = 1
    elif lines and lines[0].startswith('#'):
        title = lines[0].lstrip('#').strip()
        i = 1

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith('```'):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            code = '\n'.join(code_lines)
            # Notion rich_text limit: 2000 chars
            if len(code) > 2000:
                code = code[:1997] + '...'
            blocks.append({
                "type": "code",
                "code": {
                    "language": map_lang(lang),
                    "rich_text": [{"type": "text", "text": {"content": code}}],
                },
            })
            i += 1  # skip closing ```
            continue

        # H3
        if line.startswith('### '):
            blocks.append({
                "type": "heading_3",
                "heading_3": {"rich_text": make_rich_text(line[4:].strip())},
            })
            i += 1
            continue

        # H2
        if line.startswith('## '):
            blocks.append({
                "type": "heading_2",
                "heading_2": {"rich_text": make_rich_text(line[3:].strip())},
            })
            i += 1
            continue

        # H1 (inline, not used as title)
        if line.startswith('# '):
            blocks.append({
                "type": "heading_1",
                "heading_1": {"rich_text": make_rich_text(line[2:].strip())},
            })
            i += 1
            continue

        # Divider (---, ***, ___)
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line.strip()):
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # Blockquote
        if line.startswith('> '):
            blocks.append({
                "type": "quote",
                "quote": {"rich_text": make_rich_text(line[2:].strip())},
            })
            i += 1
            continue

        # To-do: - [ ] or - [x]
        m = re.match(r'^[-*] \[( |x|X)\] (.+)', line)
        if m:
            checked = m.group(1).lower() == 'x'
            blocks.append({
                "type": "to_do",
                "to_do": {
                    "rich_text": make_rich_text(m.group(2)),
                    "checked": checked,
                },
            })
            i += 1
            continue

        # Ordered list
        m = re.match(r'^\d+[.)]\s+(.+)', line)
        if m:
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": make_rich_text(m.group(1))},
            })
            i += 1
            continue

        # Bullet list
        if re.match(r'^[-*+] ', line):
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": make_rich_text(line[2:].strip())},
            })
            i += 1
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Paragraph
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": make_rich_text(line.strip())},
        })
        i += 1

    return title, blocks


def get_token_from_mcp() -> str | None:
    """Auto-detect Notion token from ~/.mcp.json"""
    mcp_path = Path.home() / '.mcp.json'
    if not mcp_path.exists():
        return None
    try:
        with open(mcp_path, 'r', encoding='utf-8') as f:
            mcp = json.load(f)
        notion = mcp.get('mcpServers', {}).get('notion', {})
        env = notion.get('env', {})
        headers_str = env.get('OPENAPI_MCP_HEADERS', '')
        if headers_str:
            headers = json.loads(headers_str)
            auth = headers.get('Authorization', '')
            if auth.startswith('Bearer '):
                return auth[7:]
    except Exception:
        pass
    return None


# --- Commands ---

def cmd_get_token(_args):
    token = get_token_from_mcp()
    if token:
        print(token)
    else:
        print("ERROR: Token not found in ~/.mcp.json", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    data = {"filter": {"value": "page", "property": "object"}, "page_size": 50}
    result = api_request(args.token, 'POST', '/search', data)
    pages = []
    for item in result.get('results', []):
        item_id = item.get('id')
        props = item.get('properties', {})
        title_prop = props.get('title', props.get('Name', {}))
        title_arr = title_prop.get('title', [])
        title = ''.join([t.get('plain_text', '') for t in title_arr]) or '(no title)'
        pages.append({'id': item_id, 'title': title})
    print(json.dumps(pages, ensure_ascii=False, indent=2))


def cmd_create(args):
    with open(args.file, 'r', encoding='utf-8') as f:
        content = f.read()

    title, blocks = parse_markdown(content)
    if args.title:
        title = args.title

    print(f"[notion-writer] Title: {title}", file=sys.stderr)
    print(f"[notion-writer] Blocks: {len(blocks)}", file=sys.stderr)

    page_data = {
        "parent": {"type": "page_id", "page_id": args.parent_id},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
        "children": blocks[:100],
    }
    result = api_request(args.token, 'POST', '/pages', page_data)
    page_id = result['id']
    page_url = result.get('url', '')

    # Append remaining blocks in batches of 100
    remaining = blocks[100:]
    for idx in range(0, len(remaining), 100):
        batch = remaining[idx:idx + 100]
        api_request(args.token, 'PATCH', f'/blocks/{page_id}/children', {"children": batch})
        print(f"[notion-writer] Appended batch {idx // 100 + 1} ({len(batch)} blocks)", file=sys.stderr)

    output = {
        "page_id": page_id,
        "page_url": page_url,
        "title": title,
        "total_blocks": len(blocks),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='Notion Writer - Upload Markdown to Notion')
    parser.add_argument('--token', help='Notion API token (auto-detected from ~/.mcp.json if omitted)')

    subparsers = parser.add_subparsers(dest='command')

    # get-token
    subparsers.add_parser('get-token', help='Print the auto-detected Notion token')

    # search
    subparsers.add_parser('search', help='List accessible Notion pages')

    # create
    create_p = subparsers.add_parser('create', help='Create a Notion page from a Markdown file')
    create_p.add_argument('--file', required=True, help='Path to the Markdown file')
    create_p.add_argument('--parent-id', required=True, help='Notion parent page ID')
    create_p.add_argument('--title', help='Override the page title (default: first H1 in file)')

    args = parser.parse_args()

    # Auto-detect token for commands that need it
    if args.command in ('search', 'create') and not args.token:
        args.token = get_token_from_mcp()
        if not args.token:
            print(
                "Error: Notion token not found. Provide --token or configure ~/.mcp.json",
                file=sys.stderr,
            )
            sys.exit(1)

    if args.command == 'get-token':
        cmd_get_token(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'create':
        cmd_create(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
