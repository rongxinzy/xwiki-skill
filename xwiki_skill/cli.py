"""Minimal command line interface for the XWiki skill.

Examples
--------
# Basic auth: list wikis
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' wikis

# Session login: read a page
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' --auth session page xwiki Main WebHome
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .client import XWikiClient, XWikiError


def env_or_prompt(name: str, secret: bool = False) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if secret:
        try:
            import getpass
            return getpass.getpass(f"{name}: ")
        except (EOFError, KeyboardInterrupt):
            return None
    return None


def _coerce(value: str) -> str | int | float | bool:
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XWiki REST API CLI")
    parser.add_argument("--base", default=os.environ.get("XWIKI_BASE_URL"), help="XWiki base URL")
    parser.add_argument("--user", default=os.environ.get("XWIKI_USER"), help="Username")
    parser.add_argument("--password", default=os.environ.get("XWIKI_PASSWORD"), help="Password")
    parser.add_argument(
        "--auth",
        choices=["basic", "session"],
        default=os.environ.get("XWIKI_AUTH", "basic"),
        help="Authentication mode (default: basic)",
    )
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("root", help="GET /rest/")
    sub.add_parser("wikis", help="List wikis")
    p_spaces = sub.add_parser("spaces", help="List spaces")
    p_spaces.add_argument("wiki", nargs="?", default="xwiki")
    p_pages = sub.add_parser("pages", help="List pages in a space")
    p_pages.add_argument("wiki", nargs="?", default="xwiki")
    p_pages.add_argument("space")
    p_page = sub.add_parser("page", help="Get a page")
    p_page.add_argument("wiki", nargs="?", default="xwiki")
    p_page.add_argument("space")
    p_page.add_argument("page")
    p_search = sub.add_parser("search", help="Full-text search")
    p_search.add_argument("wiki", nargs="?", default="xwiki")
    p_search.add_argument("query")
    p_query = sub.add_parser("query", help="XWQL query")
    p_query.add_argument("wiki", nargs="?", default="xwiki")
    p_query.add_argument("--type", default="xwql")
    p_query.add_argument("query")
    p_method = sub.add_parser("method", help="Call any auto-generated method by name")
    p_method.add_argument("method_name", help="Generated method name, e.g. get_wiki_space_page")
    p_method.add_argument("args", nargs="*", help="positional args and key=value kwargs")

    args = parser.parse_args(argv)

    if not args.base:
        print("error: --base or XWIKI_BASE_URL required", file=sys.stderr)
        return 1
    if not args.user:
        args.user = env_or_prompt("XWIKI_USER")
    if not args.password:
        args.password = env_or_prompt("XWIKI_PASSWORD", secret=True)

    client = XWikiClient(
        args.base,
        username=args.user,
        password=args.password,
        auth=args.auth,
        verify_ssl=not args.no_verify_ssl,
    )

    try:
        if args.auth == "session":
            client.login()

        if args.command == "root":
            result = client.root()
        elif args.command == "wikis":
            result = client.get_wikis()
        elif args.command == "spaces":
            result = client.get_spaces(args.wiki)
        elif args.command == "pages":
            result = client.get_pages(args.wiki, args.space)
        elif args.command == "page":
            result = client.get_page(args.wiki, args.space, args.page)
        elif args.command == "search":
            result = client.search(args.wiki, args.query)
        elif args.command == "query":
            result = client.query(args.wiki, args.query, qtype=args.type)
        elif args.command == "method":
            import inspect
            func = getattr(client, args.method_name)
            sig = inspect.signature(func)
            pos_args: list[Any] = []
            kwargs: dict[str, Any] = {}
            for a in args.args:
                if "=" in a:
                    k, v = a.split("=", 1)
                    kwargs[k] = _coerce(v)
                else:
                    pos_args.append(_coerce(a))
            result = func(*pos_args, **kwargs)
        else:
            raise AssertionError("unknown command")

        if isinstance(result, bytes):
            sys.stdout.buffer.write(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except XWikiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if exc.status:
            print(f"status: {exc.status}", file=sys.stderr)
        if exc.body:
            print(exc.body[:2000], file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
