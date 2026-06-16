# XWiki REST API Skill 调研记录

> 目标：判断把 XWiki 的全部 REST API 封装成一个 Kimi Skill 是否可行，并支持“模拟登录”。
> 调研环境：`http://172.18.5.247`（XWiki 16.7.1），账号 `krli`。

## 1. 结论

**可行。**

XWiki 内置 REST API 是基于 Jersey 的标准 RESTful 接口，可以通过 WADL 自描述，所有资源都可通过 `/rest/application.wadl?detail=true` 枚举。认证方式支持 HTTP Basic Auth 和 XWiki 表单登录后的 Cookie Session；因此“模拟登录”也能实现。最终封装一个 Skill 时，既可以手写常用接口的便捷方法，也可以从 WADL 自动生成完整绑定。

## 2. 探测到的关键信息

| 项目 | 结果 |
|------|------|
| XWiki 版本 | `16.7.1`（响应头 `XWiki-Version`） |
| REST 根路径 | `/rest`（注意部分安装可能是 `/xwiki/rest`） |
| WADL | `/rest/application.wadl?detail=true` |
| 默认返回格式 | XML；加 `Accept: application/json` 可返回 JSON |
| 读接口 | 全部支持 JSON |
| 写接口 | 部分只接受 XML / form / plain text；需 `Content-Type` |
| CSRF Token | 14.10.8+ / 15.2+ 在响应头 `XWiki-Form-Token` 中返回；`text/plain`、`multipart/form-data`、`application/x-www-form-urlencoded` 的 POST/PUT 必须携带 |

## 3. 认证方式实测

### 3.1 HTTP Basic Auth

```bash
curl -u 'krli:password' -H 'Accept: application/json' \
  http://172.18.5.247/rest/wikis/xwiki/spaces/Main/pages/WebHome
```

**结果：** 成功，返回页面 JSON，响应头带 `XWiki-User` 和 `XWiki-Form-Token`。

### 3.2 模拟登录（表单 + Cookie Session）

步骤：

1. `GET /bin/login/XWiki/XWikiLogin` 拿到 `form_token`。
2. `POST /bin/loginsubmit/XWiki/XWikiLogin`，表单字段：`j_username`、`j_password`、`form_token`、`xredirect`。
3. 保存 `JSESSIONID` cookie，后续 REST 调用带上 cookie 即可。

**结果：** 成功登录并访问 `/rest/`，`XWiki-User` 识别为 `xwiki:XWiki.krli`。

## 4. API 覆盖范围

从 WADL 解析出 **82 个资源路径**，涵盖：

- 元数据：`/wikis`、`/spaces`、`/pages`、`/classes`、`/syntaxes`
- 页面 CRUD：GET / PUT / DELETE `/wikis/{wiki}/spaces/{space}/pages/{page}`
- 附件：上传 / 下载 / 元数据 / 历史版本
- 评论、标签、注解、对象（objects）、属性（properties）
- 翻译（translations）
- 搜索 `/search`、XWQL/HQL 查询 `/query`
- LiveData、通知、RSS、任务（jobs）

完整列表见 [`ENDPOINTS.md`](ENDPOINTS.md)。

## 5. Skill 设计

已在本仓库实现最小可用骨架：

```text
.
├── SKILL.md                  # Skill 说明与使用示例
├── README.md                 # 本调研报告
├── ENDPOINTS.md              # 从 WADL 解析的端点清单
├── scripts/
│   └── generate_client.py    # 从 WADL 自动生成 xwiki_skill/generated.py
└── xwiki_skill/
    ├── __init__.py
    ├── client.py             # XWikiClient：认证 + 通用请求 + 手写便捷方法
    ├── generated.py          # 自动生成的 105 个接口方法
    └── cli.py                # 命令行入口（支持调用任意生成方法）
```

### 5.1 自动生成

```bash
python scripts/generate_client.py --base http://172.18.5.247 --user krli --password '***'
```

生成器读取 `/rest/application.wadl?detail=true`，为每个 WADL 资源/方法创建一个 Python 方法。当前实例共生成 **105 个方法**。方法名从 URL 推导，例如：

- `GET /wikis/{wikiName}` → `get_wiki(wiki)`
- `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` → `get_wiki_space_page(wiki, space, page)`
- `PUT /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}` → `put_wiki_space_page(wiki, space, page, body=..., content_type=...)`
- `GET /wikis/{wikiName}/spaces/{spaceName}/pages/{pageName}/attachments/{attachmentName}` → `get_wiki_space_page_attachment(wiki, space, page, attachment, raw=True)`

### 5.2 核心能力

- **两种认证**：`auth="basic"` 与 `auth="session"`（模拟登录）。
- **通用请求**：`client.request(method, path, ...)`，自动处理 `Accept`、`Authorization`、CSRF token。
- **自动生成方法**：105 个方法覆盖 WADL 中所有非 OPTIONS 端点。
- **手写便捷方法**：保留 `get_page`、`put_page`、`search`、`query` 等常用方法，并支持嵌套空间点号写法。
- **写操作**：自动生成方法直接接受 `body` / `content_type`；手写 `put_page`  helper 可快速创建页面。
- **逃生口**：`client.call(method, path, ...)` 可直接访问任意端点。

### 5.3 使用示例

```python
from xwiki_skill import XWikiClient

# Basic Auth
client = XWikiClient("http://172.18.5.247", "krli", "password")
page = client.get_wiki_space_page("xwiki", "Main", "WebHome")
print(page["title"], page["content"])

# 模拟登录
client = XWikiClient("http://172.18.5.247", "krli", "password", auth="session")
client.login()
print(client.get_wikis())

# 手写便捷方法（支持点号嵌套空间）
print(client.get_page("xwiki", "Help.Applications", "WebHome"))
```

### 5.4 CLI 示例

```bash
# 调用任意自动生成的方法
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page xwiki Main WebHome

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_search xwiki q=XWiki

python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_query xwiki q="where doc.space='Main'" type_=xwql

# 下载附件
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' \
  method get_wiki_space_page_attachment xwiki Main WebHome example.png raw=True \
  > example.png

# 保留的手写子命令
python -m xwiki_skill.cli --base http://172.18.5.247 --user krli --password '***' page xwiki Main WebHome
```

支持环境变量：`XWIKI_BASE_URL`、`XWIKI_USER`、`XWIKI_PASSWORD`、`XWIKI_AUTH`。

## 6. 可行性与风险

| 方面 | 评估 |
|------|------|
| 全部接口封装 | **已实现**：105 个方法由 WADL 自动生成，覆盖全部非 OPTIONS 端点 |
| 模拟登录 | 可行；表单登录 + Cookie 已实现并验证 |
| 读写分离 | 读接口 JSON 友好；写接口需注意 XML 载荷和 CSRF token |
| 二进制附件 | 自动生成方法支持 `raw=True`，CLI 可直接下载到文件 |
| 嵌套空间 | 手写便捷方法用点号展开；生成方法按 URL 逐级传参 |
| 版本差异 | XWiki 各版本 REST API 基本一致，但 14.10.8+/15.2+ 引入了 CSRF token，需要兼容 |
| 自定义认证 | OIDC/SAML/Trusted Header 等需在 `XWikiClient` 中额外扩展 |
| 数据安全 | Skill 默认只读；写操作需要显式调用，使用方需自行确认权限 |

## 7. 建议的后续步骤

1. 增加附件上传流式处理（`PUT` binary）。
2. 针对 CSRF token 过期做自动重试（捕获 403 后刷新 token 并重发一次）。
3. 为生成的方法增加类型注解或 Pydantic 模型（可从 WADL XSD 推导）。
4. 编写单元测试，使用本地实例的只读接口做回归验证。
5. 当 XWiki 升级或安装新扩展后，重新运行 `scripts/generate_client.py` 即可同步新端点。
