#!/usr/bin/env python3
"""
抖音视频文案提取 Skill CLI
用法: python skill_extract.py <抖音链接> [--format markdown|json|plain]

环境变量:
    SILICONFLOW_API_KEY: 硅基流动 API Key（必填）
    COOKIE_FILE: Cookie 文件路径，默认 cookies.txt
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
import yaml
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# 加载 .env 文件
load_dotenv()


def extract_douyin_url(text: str) -> str:
    """从用户复制的抖音分享文本中提取干净的视频URL。"""
    short_url_pattern = r'https?://v\.douyin\.com/[a-zA-Z0-9_-]+'
    long_url_pattern = r'https?://www\.douyin\.com/video/[a-zA-Z0-9_-]+'
    jingxuan_pattern = r'https?://www\.douyin\.com/jingxuan\?modal_id=[0-9]+'

    for pattern in [short_url_pattern, long_url_pattern, jingxuan_pattern]:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return text.strip()


def _parse_netscape_cookies(cookie_file: str) -> list:
    """Parse Netscape format cookie file into Playwright cookie dicts."""
    cookies = []
    with open(cookie_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path, secure, expires, name, value = parts[:7]
            if not name:
                continue
            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": secure.upper() == "TRUE",
            }
            try:
                exp = int(expires)
                if exp > 0:
                    cookie["expires"] = float(exp)
            except ValueError:
                pass
            cookies.append(cookie)
    return cookies


async def _get_video_url_via_browser(url: str, cookie_file: str) -> str:
    """Launch headless Chromium, load Douyin cookies, navigate to video page."""
    video_url = None
    aweme_id = None

    video_match = re.search(r'/video/([0-9]+)', url)
    if video_match:
        aweme_id = video_match.group(1)
    modal_match = re.search(r'modal_id=([0-9]+)', url)
    if modal_match:
        aweme_id = modal_match.group(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            window.chrome = { runtime: {} };
        """)

        if cookie_file and os.path.exists(cookie_file):
            cookies = _parse_netscape_cookies(cookie_file)
            if cookies:
                await context.add_cookies(cookies)

        page = await context.new_page()

        async def handle_response(response):
            nonlocal video_url
            if video_url:
                return
            url = response.url
            if not any(x in url for x in ["aweme/detail", "aweme/related", "aweme/favorite"]):
                return
            try:
                data = await response.json()
                aweme = None
                if "aweme_detail" in data:
                    aweme = data.get("aweme_detail")
                elif "aweme_list" in data and data["aweme_list"]:
                    aweme = data["aweme_list"][0]
                elif "data" in data and isinstance(data["data"], list) and data["data"]:
                    aweme = data["data"][0]

                if not aweme:
                    return
                url_list = (
                    aweme.get("video", {})
                    .get("play_addr", {})
                    .get("url_list", [])
                )
                if url_list:
                    video_url = url_list[0]
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            await page.goto(
                "https://www.douyin.com", wait_until="domcontentloaded", timeout=20000
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            pass

        if not aweme_id and "modal_id=" in page.url:
            modal_match = re.search(r'modal_id=([0-9]+)', page.url)
            if modal_match:
                aweme_id = modal_match.group(1)

        if aweme_id:
            video_page_url = f"https://www.douyin.com/video/{aweme_id}"
            try:
                await page.goto(video_page_url, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass

        await page.wait_for_timeout(5000)
        await browser.close()

    if not video_url:
        raise RuntimeError(
            "无法从抖音页面提取视频地址。可能原因：\n"
            "1. cookies.txt 中的登录 Cookie 已过期，请重新导出\n"
            "2. 该视频仅限 App 查看（无法通过网页提取）\n"
            "3. 视频已被删除或设为私密"
        )

    return video_url


_BROWSER_WORKER_CODE = """\
import sys, asyncio
sys.path.insert(0, sys.argv[3])
from skill_extract import _get_video_url_via_browser
try:
    result = asyncio.run(_get_video_url_via_browser(sys.argv[1], sys.argv[2]))
    print(result)
except Exception as exc:
    import sys as _sys
    print(exc, file=_sys.stderr)
    _sys.exit(1)
"""


def _subprocess_get_video_url(url: str, cookie_file: str) -> str:
    """Spawn a fresh Python process that runs _get_video_url_via_browser."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        [sys.executable, "-c", _BROWSER_WORKER_CODE, url, cookie_file, project_root],
        capture_output=True,
        timeout=120,
    )
    encoding = sys.stdout.encoding or "utf-8"
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode(encoding, errors="replace").strip()
        err = err or "Browser subprocess exited with no output"
        raise RuntimeError(err)
    return (proc.stdout or b"").decode(encoding, errors="replace").strip()


def _ffmpeg_to_mp3(video_path: str, mp3_path: str) -> bool:
    """Run ffmpeg synchronously. Returns True on success."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn", "-acodec", "mp3", "-ab", "128k", "-y", mp3_path,
            ],
            capture_output=True,
            timeout=60,
        )
        return result.returncode == 0 and os.path.exists(mp3_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


async def _download_video(video_url: str, output_path: str) -> None:
    """Download video from CDN URL to output_path via async streaming."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.douyin.com/",
    }
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET", video_url, headers=headers, follow_redirects=True, timeout=120
        ) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=8192):
                    f.write(chunk)


async def extract_audio(url: str, cookie_file: str = "cookies.txt") -> str:
    """Extract audio from a Douyin video URL. Returns path to audio file."""
    clean_url = extract_douyin_url(url)
    video_url = await asyncio.to_thread(_subprocess_get_video_url, clean_url, cookie_file)

    tmp_dir = tempfile.mkdtemp()
    video_path = os.path.join(tmp_dir, "video.mp4")
    await _download_video(video_url, video_path)

    mp3_path = os.path.join(tmp_dir, "audio.mp3")
    success = await asyncio.to_thread(_ffmpeg_to_mp3, video_path, mp3_path)
    if success:
        os.unlink(video_path)
        return mp3_path

    return video_path


def transcribe_audio(audio_path: str, api_key: str) -> str:
    """Transcribe audio using SiliconFlow Whisper API."""
    import openai

    if not api_key:
        raise ValueError("SiliconFlow API key is required for transcription")

    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
    )

    with open(audio_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="FunAudioLLM/SenseVoiceSmall",
            file=audio_file,
            response_format="text",
        )

    return response if isinstance(response, str) else response.text


def format_transcript(transcript: str, format_type: str) -> str:
    """格式化文案输出"""
    # 处理可能的 JSON 格式响应
    if transcript.strip().startswith('{"text":"'):
        try:
            data = json.loads(transcript)
            transcript = data.get("text", transcript)
        except json.JSONDecodeError:
            pass

    if format_type == "plain":
        return transcript

    if format_type == "json":
        return json.dumps({
            "transcript": transcript,
            "word_count": len(transcript),
        }, ensure_ascii=False, indent=2)

    # markdown format
    lines = transcript.split('\n')
    paragraphs = []
    current_para = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
        else:
            current_para.append(line)

    if current_para:
        paragraphs.append(' '.join(current_para))

    result = ["# 视频文案\n"]

    for i, para in enumerate(paragraphs[:3], 1):
        result.append(f"## 段落 {i}")
        result.append(para)
        result.append("")

    if len(paragraphs) > 3:
        result.append("## 后续内容")
        result.append('\n\n'.join(paragraphs[3:]))

    result.append(f"\n---\n*字数: {len(transcript)}*")

    return '\n'.join(result)


async def extract_douyin_transcript(url: str, format_type: str = "markdown", cookie_file: str = "cookies.txt") -> str:
    """提取抖音视频文案"""
    clean_url = extract_douyin_url(url)

    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 SILICONFLOW_API_KEY")

    audio_path = None
    try:
        audio_path = await extract_audio(clean_url, cookie_file)
        transcript = transcribe_audio(audio_path, api_key=api_key)
        return format_transcript(transcript, format_type)
    finally:
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)
            parent = os.path.dirname(audio_path)
            try:
                os.rmdir(parent)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="抖音视频文案提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python skill_extract.py "https://v.douyin.com/xxxxx"
  python skill_extract.py "https://v.douyin.com/xxxxx" --format json
  python skill_extract.py "复制链接 7.48 复制..." --format plain
        """
    )
    parser.add_argument("url", help="抖音视频链接（支持从分享文本中自动提取）")
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "plain"],
        default="markdown",
        help="输出格式 (默认: markdown)"
    )
    parser.add_argument(
        "--cookie-file", "-c",
        default="cookies.txt",
        help="Cookie 文件路径 (默认: cookies.txt)"
    )

    args = parser.parse_args()

    try:
        result = asyncio.run(extract_douyin_transcript(args.url, args.format, args.cookie_file))
        print(result)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
