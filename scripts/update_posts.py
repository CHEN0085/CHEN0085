"""从博客 RSS 取最新文章，写进 README 的 BLOG-POST-LIST 标记之间。

只用标准库，GitHub Actions 上不用装任何依赖。
标题以【示例】开头的文章会被跳过，等真文章发出来后自动显示。
"""

import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://kaiuniverse.vercel.app/rss.xml"
README = Path(__file__).resolve().parent.parent / "README.md"
MAX_POSTS = 5
SKIP_PREFIXES = ("【示例】",)
START = "<!-- BLOG-POST-LIST:START -->"
END = "<!-- BLOG-POST-LIST:END -->"


def fetch_feed(source: str) -> bytes:
    if source.startswith("http"):
        req = urllib.request.Request(source, headers={"User-Agent": "profile-readme-updater"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    return Path(source).read_bytes()


def parse_items(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        if not title or not link or title.startswith(SKIP_PREFIXES):
            continue
        date = parsedate_to_datetime(pub) if pub else None
        items.append({"title": title, "link": link, "date": date})
    # RSS 一般已按时间倒序，这里再排一次保险
    items.sort(key=lambda x: x["date"].timestamp() if x["date"] else 0, reverse=True)
    return items[:MAX_POSTS]


def render(items: list[dict]) -> str:
    if not items:
        return "- 第一篇文章正在路上 ✍️"
    lines = []
    for it in items:
        title = it["title"].replace("[", "\\[").replace("]", "\\]")
        date = f" · {it['date']:%Y-%m-%d}" if it["date"] else ""
        lines.append(f"- [{title}]({it['link']}){date}")
    return "\n".join(lines)


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else FEED_URL
    items = parse_items(fetch_feed(source))
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        print("README 里找不到 BLOG-POST-LIST 标记", file=sys.stderr)
        return 1
    new = pattern.sub(lambda _: f"{START}\n{render(items)}\n{END}", text)
    if new == text:
        print("文章列表没有变化")
    else:
        README.write_text(new, encoding="utf-8")
        print(f"已更新 {len(items)} 篇文章")
    return 0


if __name__ == "__main__":
    sys.exit(main())
