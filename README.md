# xwiki-skill

一个面向 [XWiki](https://www.xwiki.org) 的 Python Skill / REST API 客户端。

特性：

- **全自动生成**：从 XWiki 的 WADL 描述自动生成全部 REST 端点的 Python 方法，无需手写每个接口。
- **完整覆盖**：当前基于 XWiki 16.7.1 的 WADL 生成 105 个方法，覆盖页面、空间、附件、评论、对象、类、搜索、查询、LiveData、任务、通知等全部非 OPTIONS 端点。
- **模拟登录**：支持 HTTP Basic Auth 和 XWiki 表单登录后的 Cookie Session（模拟用户在网页端登录）。
- **标准库实现**：仅依赖 Python 标准库，无需额外第三方包。
- **CLI 工具**：命令行可直接调用任意生成的方法。

## 安装

```bash
pip install git+https://github.com/rongxinzy/xwiki-skill.git
```

或克隆后本地使用：

```bash
git clone https://github.com/rongxinzy/xwiki-skill.git
cd xwiki-skill
python -m xwiki_skill.cli --help
```

## 快速开始

### Python

```python
from xwiki_skill import XWikiClient

# HTTP Basic Auth
client = XWikiClient("http://172.18.5.247", "krli", "password")
page = client.get_wiki_space_page("xwiki", "Main", "WebHome")
print(page["title"], page["content"])

# 模拟登录（表单 + Cookie）
client = XWikiClient("http://172.18.5.247", "krli", "password", auth="session")
client.login()
print(client.get_wikis())

# 搜索 / XWQL 查询
print(client.get_wiki_search("xwiki", q="XWiki"))
print(client.get_wiki_query("xwiki", q="where doc.space='Main'", type_="xwql"))

# 下载附件（返回 bytes）
data = client.get_wiki_space_page_attachment(
    "xwiki", "Main", "WebHome", "example.png"
)
```

### CLI

```bash
# 调用任意自动生成的方法
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page xwiki Main WebHome

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_search xwiki q=XWiki

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_query xwiki q="where doc.space='Main'" type_=xwql

# 下载附件到文件
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page_attachment xwiki Main WebHome example.png raw=True \
  > example.png

# 使用环境变量
export XWIKI_BASE_URL=http://172.18.5.247
export XWIKI_USER=krli
export XWIKI_PASSWORD='***'
python -m xwiki_skill.cli method get_wikis
```

## 自动生成客户端

`xwiki_skill/generated.py` 由 `scripts/generate_client.py` 从 XWiki WADL 自动生成。

```bash
# 从运行中的 XWiki 实例拉取 WADL 并生成
python scripts/generate_client.py --base http://<host> --user <user> --password <pass>

# 或从本地 WADL 文件生成
python scripts/generate_client.py --wadl /tmp/xwiki_wadl.xml
```

生成器会为每个 WADL 资源/方法生成一个 Python 方法，方法名从 URL 推导：

| REST 端点 | 生成的方法 |
|-----------|-----------|
| `GET /wikis/{wikiName}` | `get_wiki(wiki)` |
| `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` | `get_wiki_space_page(wiki, space, page)` |
| `PUT /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` | `put_wiki_space_page(wiki, space, page, body=..., content_type=...)` |
| `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}/attachments/{attachmentName}` | `get_wiki_space_page_attachment(wiki, space, page, attachment, raw=True)` |

当 XWiki 升级或安装新扩展后，重新运行生成器即可同步新端点。

## 项目结构

```text
.
├── LICENSE
├── pyproject.toml
├── README.md
├── RESEARCH.md          # 调研过程记录
├── SKILL.md             # Skill 使用说明
├── ENDPOINTS.md         # 从 WADL 解析的端点清单
├── scripts/
│   └── generate_client.py   # WADL 生成器
└── xwiki_skill/
    ├── __init__.py
    ├── client.py            # XWikiClient：认证、通用请求、手写便捷方法
    ├── generated.py         # 自动生成的接口方法
    └── cli.py               # 命令行入口
```

## 手写便捷方法

除了自动生成的方法外，`XWikiClient` 还保留了一些更易用的手写方法：

- `get_page(wiki, space, page)`：支持用点号表示嵌套空间，例如 `"Help.Applications"`。
- `put_page(...)` / `delete_page(...)`：快速创建/删除页面。
- `search(...)` / `query(...)`：封装搜索与 XWQL 查询。
- `request(method, path, ...)`：底层通用请求。
- `call(method, path, ...)`：直接调用任意端点的逃生口。

## 认证说明

- **Basic Auth**：默认模式，每次请求携带 `Authorization: Basic ...`。
- **Session / 模拟登录**：设置 `auth="session"` 后调用 `login()`，会模拟网页表单登录并保存 `JSESSIONID` Cookie。

## 注意事项

- REST 根路径因部署而异，测试环境为 `/rest`，部分安装可能是 `/xwiki/rest`，请通过 `base_url` 指定。
- 写操作（POST/PUT/DELETE）可能需要 `XWiki-Form-Token`，客户端会自动从响应头捕获并重放。
- 附件下载等二进制接口请使用 `raw=True`。

## 许可证

[MIT](LICENSE)
