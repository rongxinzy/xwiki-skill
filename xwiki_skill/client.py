"""XWiki REST API client.

Supports:
- HTTP Basic authentication
- Simulated XWiki form-login (cookie/session based)
- JSON responses for read endpoints
- CSRF token capture and automatic replay
- Raw bytes for attachments
"""

from __future__ import annotations

import base64
import http.cookiejar
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

from .generated import GeneratedMethodsMixin


class XWikiError(Exception):
    """Generic XWiki API error."""

    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class XWikiClient(GeneratedMethodsMixin):
    """Client for the XWiki built-in REST API.

    Example (Basic auth)::

        client = XWikiClient("http://172.18.5.247", "krli", "secret")
        print(client.get_page("xwiki", "Main", "WebHome"))

    Example (session / simulated login)::

        client = XWikiClient("http://172.18.5.247", "krli", "secret", auth="session")
        client.login()
        print(client.get_page("xwiki", "Main", "WebHome"))
    """

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth: str = "basic",
        verify_ssl: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth = auth.lower()
        self.verify_ssl = verify_ssl

        self.form_token: Optional[str] = None
        self.xwiki_version: Optional[str] = None
        self.user_reference: Optional[str] = None

        self._cookie_jar = http.cookiejar.CookieJar()
        handlers: List[Any] = [urllib.request.HTTPCookieProcessor(self._cookie_jar)]
        if not verify_ssl:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        self._opener = urllib.request.build_opener(*handlers)

    # ------------------------------------------------------------------ #
    # Low level request helpers
    # ------------------------------------------------------------------ #

    def _make_url(self, path: str) -> str:
        path = path if path.startswith("/") else "/" + path
        return self.base_url + path

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    @staticmethod
    def _urlencode(params: Dict[str, Any]) -> str:
        """Like urllib.parse.urlencode, but emits lowercase booleans."""
        encoded = []
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            encoded.append((key, str(value)))
        return urllib.parse.urlencode(encoded)

    @staticmethod
    def _space_path(space: str) -> str:
        """Convert dotted space notation to nested /spaces/... segments."""
        parts = space.strip("/").split(".")
        return "".join(f"/spaces/{XWikiClient._quote(p)}" for p in parts)

    def _extract_form_token(self, text: str) -> Optional[str]:
        m = re.search(r'name="form_token"\s+value="([^"]+)"', text)
        if m:
            return m.group(1)
        m = re.search(r'value="([^"]+)"\s+name="form_token"', text)
        return m.group(1) if m else None

    def _capture_headers(self, response: urllib.request.addinfourl) -> None:
        headers = response.headers
        if "XWiki-Form-Token" in headers:
            self.form_token = headers["XWiki-Form-Token"]
        if "XWiki-Version" in headers:
            self.xwiki_version = headers["XWiki-Version"]
        if "XWiki-User" in headers:
            self.user_reference = headers["XWiki-User"]

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Union[str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        accept: str = "application/json",
        raw: bool = False,
    ) -> Any:
        """Execute an HTTP request against the XWiki REST API.

        Parameters
        ----------
        method: HTTP method (GET, POST, PUT, DELETE, ...).
        path: API path (must start with /).
        body: Optional request body.
        headers: Extra headers.
        content_type: Content-Type header value.
        accept: Accept header value.
        raw: If True, return raw bytes (useful for attachments).

        Returns
        -------
        Parsed JSON (dict), text (str) or bytes depending on response and *raw*.
        """
        url = self._make_url(path)
        req = urllib.request.Request(url, method=method)

        req.add_header("Accept", accept)
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)

        if self.auth == "basic" and self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")

        if content_type:
            req.add_header("Content-Type", content_type)

        if self.form_token:
            req.add_header("XWiki-Form-Token", self.form_token)

        data = body.encode("utf-8") if isinstance(body, str) else body

        try:
            response = self._opener.open(req, data=data, timeout=60)
        except urllib.error.HTTPError as exc:
            self._capture_headers(exc)
            body_text = exc.read().decode("utf-8", errors="replace")
            raise XWikiError(
                f"XWiki request failed: {method} {url} -> {exc.code} {exc.reason}",
                status=exc.code,
                body=body_text,
            ) from exc

        self._capture_headers(response)
        content = response.read()
        if raw:
            return content

        ct = response.headers.get("Content-Type", "")
        if "application/json" in ct:
            return json.loads(content) if content else {}
        return content.decode("utf-8", errors="replace")

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    def login(self) -> Dict[str, Any]:
        """Perform a simulated XWiki form login and keep the session cookie.

        This is the equivalent of logging in through the web UI; subsequent
        REST calls reuse the JSESSIONID cookie.
        """
        if self.auth != "session":
            raise ValueError("login() is only available when auth='session'")
        if not self.username or not self.password:
            raise ValueError("username and password are required for session login")

        # The login page itself returns HTTP 401 with a login form, but it still
        # contains the CSRF form_token we need. Read the body from the HTTPError.
        login_url = self._make_url("/bin/login/XWiki/XWikiLogin")
        login_req = urllib.request.Request(login_url, method="GET")
        login_req.add_header("Accept", "text/html")
        try:
            login_resp = self._opener.open(login_req, timeout=60)
            login_page = login_resp.read().decode("utf-8", errors="replace")
            self._capture_headers(login_resp)
        except urllib.error.HTTPError as exc:
            login_page = exc.read().decode("utf-8", errors="replace")
            self._capture_headers(exc)

        form_token = self._extract_form_token(login_page)
        if not form_token:
            raise XWikiError("Could not extract form_token from XWiki login page")

        payload = urllib.parse.urlencode(
            {
                "j_username": self.username,
                "j_password": self.password,
                "form_token": form_token,
                "xredirect": "",
            }
        )

        submit_url = self._make_url("/bin/loginsubmit/XWiki/XWikiLogin")
        submit_req = urllib.request.Request(
            submit_url,
            data=payload.encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            response = self._opener.open(submit_req, timeout=60)
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise XWikiError(
                f"XWiki login failed: {exc.code} {exc.reason}",
                status=exc.code,
                body=body_text,
            ) from exc

        self._capture_headers(response)
        # Hit a REST endpoint to confirm the cookie is accepted.
        root = self.request("GET", "/rest/", accept="application/json")
        return {
            "user": self.user_reference,
            "version": self.xwiki_version,
            "form_token": self.form_token,
            "root": root,
        }

    # ------------------------------------------------------------------ #
    # Convenience wrappers
    # ------------------------------------------------------------------ #

    def root(self) -> Dict[str, Any]:
        """Return the REST root document (version, top-level links)."""
        return self.request("GET", "/rest/")

    def get_wikis(self) -> Dict[str, Any]:
        return self.request("GET", "/rest/wikis")

    def get_wiki(self, wiki: str) -> Dict[str, Any]:
        return self.request("GET", f"/rest/wikis/{self._quote(wiki)}")

    def get_spaces(self, wiki: str = "xwiki") -> Dict[str, Any]:
        return self.request("GET", f"/rest/wikis/{self._quote(wiki)}/spaces")

    def get_space(self, wiki: str, space: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}",
        )

    def get_pages(self, wiki: str, space: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages",
        )

    def get_page(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}",
        )

    def get_page_history(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}/history",
        )

    def get_page_children(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}/children",
        )

    def get_page_attachments(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}/attachments",
        )

    def get_attachment(
        self, wiki: str, space: str, page: str, attachment: str, *, raw: bool = True
    ) -> Union[bytes, Dict[str, Any]]:
        """Fetch an attachment. By default returns raw bytes."""
        path = (
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}"
            f"/pages/{self._quote(page)}/attachments/{self._quote(attachment)}"
        )
        return self.request("GET", path, accept="*/*", raw=raw)

    def get_attachment_metadata(self, wiki: str, space: str, page: str, attachment: str) -> Dict[str, Any]:
        path = (
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}"
            f"/pages/{self._quote(page)}/attachments/{self._quote(attachment)}/metadata"
        )
        return self.request("GET", path)

    def get_comments(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}/comments",
        )

    def get_objects(self, wiki: str, space: str, page: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}/pages/{self._quote(page)}/objects",
        )

    def get_classes(self, wiki: str = "xwiki") -> Dict[str, Any]:
        return self.request("GET", f"/rest/wikis/{self._quote(wiki)}/classes")

    def get_class(self, wiki: str, class_name: str) -> Dict[str, Any]:
        return self.request(
            "GET",
            f"/rest/wikis/{self._quote(wiki)}/classes/{self._quote(class_name)}",
        )

    def search(self, wiki: str, query: str, *, number: Optional[int] = None, start: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"q": query, "media": "json"}
        if number is not None:
            params["number"] = number
        if start is not None:
            params["start"] = start
        qs = self._urlencode(params)
        return self.request("GET", f"/rest/wikis/{self._quote(wiki)}/search?{qs}")

    def query(
        self,
        wiki: str,
        query: str,
        *,
        qtype: str = "xwql",
        number: Optional[int] = None,
        start: Optional[int] = None,
        order_field: Optional[str] = None,
        order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run an XWQL/HQL query.

        The ``query`` argument should be the query body (e.g. ``where doc.space='Main'``
        for XWQL). See the XWiki REST query endpoint documentation for details.
        """
        params: Dict[str, Any] = {"q": query, "type": qtype, "media": "json"}
        if number is not None:
            params["number"] = number
        if start is not None:
            params["start"] = start
        if order_field is not None:
            params["orderField"] = order_field
        if order is not None:
            params["order"] = order
        qs = self._urlencode(params)
        return self.request("GET", f"/rest/wikis/{self._quote(wiki)}/query?{qs}")

    # ------------------------------------------------------------------ #
    # Write helpers
    # ------------------------------------------------------------------ #

    def put_page(
        self,
        wiki: str,
        space: str,
        page: str,
        title: str,
        content: str,
        *,
        syntax: str = "xwiki/2.1",
        content_type: str = "application/xml",
        parent: Optional[str] = None,
    ) -> Any:
        """Create or update a page.

        XWiki's PUT page resource accepts XML, plain text and form-encoded
        payloads. This helper builds a minimal XML body.
        """
        path = (
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}"
            f"/pages/{self._quote(page)}"
        )
        parent_xml = f"<parent>{self._escape_xml(parent)}</parent>" if parent else ""
        body = f"""<?xml version="1.0" encoding="UTF-8"?>
<page xmlns="http://www.xwiki.org">
  <title>{self._escape_xml(title)}</title>
  <content>{self._escape_xml(content)}</content>
  <syntax>{self._escape_xml(syntax)}</syntax>
  {parent_xml}
</page>"""
        return self.request("PUT", path, body=body, content_type=content_type)

    def delete_page(self, wiki: str, space: str, page: str) -> Any:
        path = (
            f"/rest/wikis/{self._quote(wiki)}{self._space_path(space)}"
            f"/pages/{self._quote(page)}"
        )
        return self.request("DELETE", path)

    @staticmethod
    def _escape_xml(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    # ------------------------------------------------------------------ #
    # Generic access to any WADL endpoint
    # ------------------------------------------------------------------ #

    def call(self, method: str, path: str, **kwargs: Any) -> Any:
        """Direct access for endpoints not covered by convenience methods."""
        return self.request(method, path, **kwargs)
