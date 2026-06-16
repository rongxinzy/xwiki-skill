# XWiki REST API Skill

A Python wrapper around the XWiki built-in REST API. The client methods are **auto-generated from the XWiki WADL** so every endpoint exposed by the running instance gets a corresponding Python method.

Supported authentication:
- HTTP Basic Auth
- Simulated XWiki form login (cookie/session)

## Auto-generation

The file `xwiki_skill/generated.py` is produced by:

```bash
python scripts/generate_client.py --base http://<host> --user <user> --password <pass>
# or from a local WADL file
python scripts/generate_client.py --wadl /tmp/xwiki_wadl.xml
```

The generator reads `/rest/application.wadl?detail=true` and creates one Python method per WADL resource/method (105 methods for XWiki 16.7.1). Method names are derived from the URL, e.g.:

| URL | Generated method |
|-----|------------------|
| `GET /wikis/{wikiName}` | `get_wiki(wiki)` |
| `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` | `get_wiki_space_page(wiki, space, page)` |
| `PUT /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` | `put_wiki_space_page(wiki, space, page, body=..., content_type=...)` |
| `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}/attachments/{attachmentName}` | `get_wiki_space_page_attachment(wiki, space, page, attachment, raw=True)` |

## Authentication modes

### HTTP Basic Auth (default)

```python
from xwiki_skill import XWikiClient

client = XWikiClient("http://172.18.5.247", "krli", "password")
print(client.get_wiki_space_page("xwiki", "Main", "WebHome"))
```

### Simulated web login / session cookie

```python
client = XWikiClient("http://172.18.5.247", "krli", "password", auth="session")
client.login()
print(client.get_wiki_space_page("xwiki", "Main", "WebHome"))
```

## Python examples

```python
from xwiki_skill import XWikiClient

client = XWikiClient("http://172.18.5.247", "krli", "password")

# Read a page
page = client.get_wiki_space_page("xwiki", "Main", "WebHome")
print(page["title"], page["content"])

# List spaces
spaces = client.get_wiki_spaces("xwiki")

# Search
results = client.get_wiki_search("xwiki", q="XWiki")

# XWQL query
results = client.get_wiki_query("xwiki", q="where doc.space='Main'", type_="xwql")

# Download attachment (raw bytes)
data = client.get_wiki_space_page_attachment(
    "xwiki", "Main", "WebHome", "example.png"
)

# Create/update a page (manual XML/JSON helper)
client.put_page("xwiki", "Sandbox", "Demo", title="Demo", content="Hello")
```

## CLI examples

```bash
# Call any auto-generated method
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page xwiki Main WebHome

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_search xwiki q=XWiki

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_query xwiki q="where doc.space='Main'" type_=xwql

# Download attachment to a file
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page_attachment xwiki Main WebHome example.png raw=True \
  > example.png

# Session login
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  --auth session method get_wikis
```

Environment variables: `XWIKI_BASE_URL`, `XWIKI_USER`, `XWIKI_PASSWORD`, `XWIKI_AUTH`.

## Writing data

The auto-generated methods accept `body` and `content_type` for `POST`/`PUT` endpoints. Example:

```python
client.put_wiki_space_page(
    "xwiki", "Sandbox", "DemoPage",
    body="<page xmlns='http://www.xwiki.org'><title>Demo</title><content>Hello</content></page>",
    content_type="application/xml",
)
```

For endpoints that require the CSRF form token (mainly `text/plain`, `multipart/form-data`, `application/x-www-form-urlencoded`), the skill captures `XWiki-Form-Token` from response headers and replays it automatically.

## Notes

- REST base path is deployment-specific (`/rest` in the tested instance, sometimes `/xwiki/rest`).
- Nested spaces use dots (`Help.Applications`) and are expanded automatically by the manual helpers; the generated methods take each space level as a separate `space` argument.
- The generated client uses JSON by default (`Accept: application/json`); attachments return raw bytes when `raw=True`.
- Custom authenticators (OIDC, SAML, trusted headers) are not handled by default but can be added by extending `XWikiClient`.

## Dependencies

Only the Python standard library (`urllib`, `http.cookiejar`, `ssl`, etc.). No external packages are required.
