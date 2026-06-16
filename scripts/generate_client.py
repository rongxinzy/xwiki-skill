#!/usr/bin/env python3
"""Generate xwiki_skill/generated.py from XWiki's REST WADL.

Usage:
    python scripts/generate_client.py
    python scripts/generate_client.py --base http://172.18.5.247 --user krli --password '***'

When --base is provided the WADL is fetched from the running XWiki instance;
otherwise /tmp/xwiki_wadl.xml is used as the default source.
"""

from __future__ import annotations

import argparse
import base64
import keyword
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

WADL_NS = {"wadl": "http://wadl.dev.java.net/2009/02"}

# Short, Python-friendly names for path template variables.
VAR_MAP: Dict[str, str] = {
    "wikiName": "wiki",
    "spaceName": "space",
    "pageName": "page",
    "attachmentName": "attachment",
    "attachmentVersion": "version",
    "className": "class_name",
    "objectNumber": "object_number",
    "propertyName": "property",
    "propertyId": "property_id",
    "sourceId": "source_id",
    "entryId": "entry_id",
    "typeId": "type_id",
    "jobId": "job_id",
    "iconTheme": "icon_theme",
    "language": "language",
    "version": "version",
    "tagNames": "tag_names",
    "path": "path",
}

# Query parameter names that would shadow builtins / keywords.
SANITIZE_PARAMS = {"type", "class", "property", "id"}


def to_snake(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def py_name(name: str) -> str:
    name = to_snake(name)
    if keyword.iskeyword(name) or name in SANITIZE_PARAMS:
        return name + "_"
    return name


def python_default(value: Optional[str], xs_type: Optional[str]) -> str:
    """Convert a WADL default string into a Python literal for the signature."""
    if value is None:
        return "None"
    if xs_type in ("xs:boolean", "boolean"):
        return "True" if value.lower() == "true" else "False"
    if xs_type in ("xs:int", "xs:integer", "xs:long", "xs:short"):
        try:
            return str(int(value))
        except ValueError:
            return repr(value)
    return repr(value)


def parse_template(segment: str) -> Tuple[bool, List[str]]:
    """Return (is_simple, variable_names) for a path segment.

    A simple segment contains only ``{varName}`` style templates, optionally
    with a regex after a colon (e.g. ``{spaceName: .+}``). Segments with
    concatenated templates or embedded regex slashes are rejected.
    """
    # Remove regex colons: turn "{spaceName: .+}" into "{spaceName}"
    normalized = re.sub(r"\{([^}:]+)(?:\s*:\s*[^{}]+)?\}", r"{\1}", segment)
    if re.search(r"[{}]", normalized):
        # Must be exactly a single template or a static string.
        if normalized.startswith("{") and normalized.endswith("}"):
            inner = normalized[1:-1]
            if "," not in inner and "/" not in inner:
                return True, [inner]
        return False, []
    return True, []


def build_fstring_path(parts: List[Tuple[str, Optional[str]]]) -> str:
    """Build an f-string expression for the path from (segment, var_short_name).

    ``parts`` is a list of (static_segment_or_full_segment, variable_short_name).
    If variable_short_name is None the segment is static. Otherwise the segment
    is a template and is replaced by ``{self._quote(var)}``.
    """
    pieces: List[str] = ['f"/rest']
    for segment, var in parts:
        if var is None:
            pieces.append(segment)
        else:
            pieces.append("/{" + f"self._quote({var})" + "}")
    pieces.append('"')
    return "".join(pieces)


def path_parts(path: str) -> Optional[List[Tuple[str, Optional[str]]]]:
    """Break a resource path into URL-building pieces.

    Returns None if the path contains unsupported templates.
    """
    segments = path.strip("/").split("/")
    out: List[Tuple[str, Optional[str]]] = []
    for seg in segments:
        simple, vars_ = parse_template(seg)
        if not simple:
            return None
        if not vars_:
            out.append(("/" + seg, None))
        else:
            var = vars_[0]
            short = VAR_MAP.get(var, to_snake(var))
            out.append((seg, short))
    return out


# Map plural resource names to their singular short names.
# Used to produce shorter method names while keeping them unambiguous.
SINGULAR: Dict[str, str] = {
    "wikis": "wiki",
    "spaces": "space",
    "pages": "page",
    "attachments": "attachment",
    "classes": "class",
    "objects": "object",
    "properties": "property",
    "translations": "translation",
    "tags": "tag",
    "entries": "entry",
    "types": "type",
    "icons": "icon",
    "syntaxes": "syntax",
    "modifications": "modification",
    "children": "child",
    "comments": "comment",
    "annotations": "annotation",
}


def method_name(method: str, parts: List[Tuple[str, Optional[str]]]) -> str:
    """Generate a valid snake_case method name from HTTP method and path pieces."""
    bits = [method.lower()]
    i = 0
    while i < len(parts):
        segment, var = parts[i]
        if var is None:
            name = to_snake(segment.lstrip("/"))
            name = re.sub(r"[^a-z0-9_]", "_", name)
            singular = SINGULAR.get(name)
            # When a plural resource segment is immediately followed by its
            # singular path variable, use the singular name once and skip the
            # variable in the method name (the variable still exists as a
            # parameter). Example: /wikis/{wikiName} -> get_wiki.
            if singular and i + 1 < len(parts) and parts[i + 1][1] == singular:
                bits.append(singular)
                i += 2
                continue
            bits.append(name)
        else:
            bits.append(var)
        i += 1
    return "_".join(bits)


def is_attachment_download(parts: List[Tuple[str, Optional[str]]]) -> bool:
    """Heuristic: the endpoint returns binary attachment data."""
    # Last segment must be the attachment variable and the preceding static
    # segment must be 'attachments'.
    if len(parts) < 2:
        return False
    last_var = parts[-1][1]
    prev_static = parts[-2][0].lstrip("/")
    return last_var == "attachment" and prev_static == "attachments"


def fetch_wadl(base_url: str, username: Optional[str], password: Optional[str]) -> bytes:
    url = base_url.rstrip("/") + "/rest/application.wadl?detail=true"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.sun.wadl+xml")
    if username and password:
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def generate(wadl_path: Optional[str] = None, base_url: Optional[str] = None,
             username: Optional[str] = None, password: Optional[str] = None,
             out_path: str = "xwiki_skill/generated.py") -> None:
    if wadl_path:
        tree = ET.parse(wadl_path)
    elif base_url:
        data = fetch_wadl(base_url, username, password)
        tree = ET.ElementTree(ET.fromstring(data))
    else:
        raise ValueError("Either --wadl or --base must be provided")

    root = tree.getroot()
    resources_elem = root.find("wadl:resources", WADL_NS)
    base = ""
    if resources_elem is not None:
        base = resources_elem.get("base", "")

    endpoints: List[Dict[str, Any]] = []
    seen_names: Dict[str, int] = {}

    for resource in root.findall(".//wadl:resource", WADL_NS):
        path = resource.get("path", "")
        if not path or path == "/":
            continue

        parts = path_parts(path)
        if parts is None:
            # Skip endpoints with weird templates (e.g. notificationsWatches).
            continue

        # Resource-level template params (path variables) may include types.
        resource_params: Dict[str, Tuple[str, str]] = {}
        for param in resource.findall("wadl:param", WADL_NS):
            name = param.get("name", "")
            style = param.get("style", "")
            xs_type = param.get("type", "xs:string")
            if style == "template":
                resource_params[name] = (style, xs_type)

        for method_elem in resource.findall("wadl:method", WADL_NS):
            http_method = method_elem.get("name", "")
            if http_method == "OPTIONS":
                continue

            method_id = method_elem.get("id", "")
            request_elem = method_elem.find("wadl:request", WADL_NS)
            response_elem = method_elem.find("wadl:response", WADL_NS)

            query_params: List[Dict[str, Any]] = []
            request_media_types: List[str] = []
            response_media_types: List[str] = []

            if request_elem is not None:
                for param in request_elem.findall("wadl:param", WADL_NS):
                    style = param.get("style", "")
                    if style == "query":
                        query_params.append(
                            {
                                "name": param.get("name", ""),
                                "type": param.get("type", "xs:string"),
                                "default": param.get("default"),
                            }
                        )
                for rep in request_elem.findall("wadl:representation", WADL_NS):
                    mt = rep.get("mediaType")
                    if mt:
                        request_media_types.append(mt)

            if response_elem is not None:
                for rep in response_elem.findall("wadl:representation", WADL_NS):
                    mt = rep.get("mediaType")
                    if mt:
                        response_media_types.append(mt)

            name = method_name(http_method, parts)
            if name in seen_names:
                seen_names[name] += 1
                name = f"{name}_{seen_names[name]}"
            else:
                seen_names[name] = 1

            endpoints.append(
                {
                    "name": name,
                    "path": path,
                    "method": http_method,
                    "method_id": method_id,
                    "parts": parts,
                    "query_params": query_params,
                    "request_media_types": request_media_types,
                    "response_media_types": response_media_types,
                }
            )

    lines: List[str] = []
    lines.append('"""Auto-generated XWiki REST API methods.')
    lines.append("")
    lines.append("This file is generated by scripts/generate_client.py from the XWiki WADL.")
    lines.append("Do not edit manually; re-run the generator instead.")
    lines.append('"""')
    lines.append("")
    lines.append("from typing import Any, Dict, Optional")
    lines.append("")
    lines.append("")
    lines.append("class GeneratedMethodsMixin:")
    lines.append('    """Mixin that adds one Python method per WADL resource/method."""')
    lines.append("")

    for ep in endpoints:
        name = ep["name"]
        http_method = ep["method"]
        path = ep["path"]
        parts = ep["parts"]
        query_params = ep["query_params"]
        request_media_types = ep["request_media_types"]
        response_media_types = ep["response_media_types"]

        # Signature arguments
        args: List[str] = ["self"]
        # Path variables are positional/required
        path_vars: List[str] = []
        for _, var in parts:
            if var is not None and var not in path_vars:
                args.append(var)
                path_vars.append(var)

        # Keyword-only section
        kw_args: List[str] = []
        for qp in query_params:
            pname = py_name(qp["name"])
            default = python_default(qp["default"], qp["type"])
            kw_args.append(f"{pname}: Optional[Any] = {default}")

        has_body = http_method in ("POST", "PUT") or request_media_types
        if has_body:
            default_ct = repr(request_media_types[0]) if request_media_types else "None"
            kw_args.append("body: Optional[Any] = None")
            kw_args.append(f"content_type: Optional[str] = {default_ct}")

        raw_default = "True" if (http_method == "GET" and is_attachment_download(parts)) else "False"
        kw_args.append(f"raw: bool = {raw_default}")
        kw_args.append("accept: str = 'application/json'")
        kw_args.append("headers: Optional[Dict[str, str]] = None")

        if kw_args:
            args.append("*, " + ", ".join(kw_args))

        # Docstring
        lines.append(f"    def {name}({', '.join(args)}) -> Any:")
        lines.append(f'        """{http_method} {path}"""')
        lines.append("")

        # Path construction
        path_expr = build_fstring_path(parts)
        lines.append(f"        path = {path_expr}")
        lines.append("")

        # Query string
        if query_params:
            lines.append("        params: Dict[str, Any] = {}")
            for qp in query_params:
                pname = py_name(qp["name"])
                lines.append(f"        if {pname} is not None:")
                lines.append(f"            params[{repr(qp['name'])}] = {pname}")
            lines.append("        if params:")
            lines.append("            path += '?' + self._urlencode(params)")
            lines.append("")

        # Request call
        call_kwargs = [f"method={repr(http_method)}", "path=path", "headers=headers", "accept=accept", f"raw={raw_default}"]
        if has_body:
            call_kwargs.extend(["body=body", "content_type=content_type"])
        lines.append(f"        return self.request({', '.join(call_kwargs)})")
        lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated {len(endpoints)} methods -> {out_path}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate XWiki REST client from WADL")
    parser.add_argument("--wadl", default="/tmp/xwiki_wadl.xml", help="Path to WADL XML file")
    parser.add_argument("--base", help="XWiki base URL to fetch WADL from")
    parser.add_argument("--user", help="Username for fetching WADL")
    parser.add_argument("--password", help="Password for fetching WADL")
    parser.add_argument("--out", default="xwiki_skill/generated.py", help="Output Python file")
    args = parser.parse_args(argv)

    generate(
        wadl_path=args.wadl if not args.base else None,
        base_url=args.base,
        username=args.user,
        password=args.password,
        out_path=args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
