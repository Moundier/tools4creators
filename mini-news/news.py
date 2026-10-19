#!/usr/bin/env python3
"""mini-news: Claude drafts news posts from a link or a topic, you approve them, they go to X and Facebook.

  python3 news.py                              # web app on http://127.0.0.1:8010 (opens the browser)
  python3 news.py draft https://site.com/news  # draft from a link
  python3 news.py draft "tema da notícia"      # draft from a topic (Claude searches the web)
  python3 news.py list                         # the drafts and their status
  python3 news.py approve <id>
  python3 news.py publish <id> [--dry-run] [--only x|facebook]
  python3 news.py -h                           # list of commands
"""
from news_server.venv_tools import ensure_venv

ensure_venv()  # restarts this command under .venv/bin/python when needed

from news_server.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
