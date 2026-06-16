# XWiki REST endpoints (82 resources)

| Path | Methods |
|------|---------|
| `/` | GET |
| `/client` | GET |
| `/count` | GET |
| `/currentuser/properties/{propertyName}/next` | PUT |
| `/default` | GET |
| `/icons` | GET |
| `/joblog/{jobId: .+}` | GET |
| `/jobs` | PUT |
| `/jobstatus/{jobId: .+}` | GET |
| `/liveData/sources` | GET |
| `/liveData/sources/{sourceId}` | GET |
| `/liveData/sources/{sourceId}/entries` | GET,POST |
| `/liveData/sources/{sourceId}/entries/{entryId}` | DELETE,GET,PUT |
| `/liveData/sources/{sourceId}/entries/{entryId}/properties/{propertyId}` | GET,PUT |
| `/liveData/sources/{sourceId}/properties` | GET,POST |
| `/liveData/sources/{sourceId}/properties/{propertyId}` | DELETE,GET,PUT |
| `/liveData/sources/{sourceId}/types` | GET |
| `/liveData/sources/{sourceId}/types/{typeId}` | GET |
| `/notifications` | GET,POST |
| `/rss` | GET |
| `/syntaxes` | GET |
| `/wikis` | GET |
| `/wikis/query` | GET |
| `/wikis/{wikiName}` | GET,POST |
| `/wikis/{wikiName}/attachments` | GET |
| `/wikis/{wikiName}/children` | GET |
| `/wikis/{wikiName}/classes` | GET |
| `/wikis/{wikiName}/classes/{className}` | GET |
| `/wikis/{wikiName}/classes/{className}/objects` | GET |
| `/wikis/{wikiName}/classes/{className}/properties` | GET |
| `/wikis/{wikiName}/classes/{className}/properties/{propertyName}` | GET |
| `/wikis/{wikiName}/classes/{className}/properties/{propertyName}/values` | GET |
| `/wikis/{wikiName}/imageStyles` | GET |
| `/wikis/{wikiName}/localization/translations` | GET |
| `/wikis/{wikiName}/modifications` | GET |
| `/wikis/{wikiName}/pages` | GET |
| `/wikis/{wikiName}/query` | GET |
| `/wikis/{wikiName}/search` | GET |
| `/wikis/{wikiName}/spaces` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/attachments` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}` | DELETE,GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/annotation/{id}` | DELETE,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/annotations` | GET,POST |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/attachments` | GET,POST |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/attachments/{attachmentName}` | DELETE,GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/attachments/{attachmentName}/history` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/attachments/{attachmentName}/history/{attachmentVersion}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/attachments/{attachmentName}/metadata` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/channels` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/children` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/comments` | GET,POST |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/comments/{id}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/attachments` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/attachments/{attachmentName}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/comments` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/comments/{id}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/objects` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/objects/{className}/{objectNumber}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/objects/{className}/{objectNumber}/properties` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/history/{version}/objects/{className}/{objectNumber}/properties/{propertyName}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/objects` | GET,POST |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/objects/{className}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/objects/{className}/{objectNumber}` | DELETE,GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/objects/{className}/{objectNumber}/properties` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/objects/{className}/{objectNumber}/properties/{propertyName}` | GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/tags` | GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/translations` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/translations/{language}` | DELETE,GET,PUT |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/translations/{language}/annotations` | GET,POST |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/translations/{language}/history` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/pages/{pageName}/translations/{language}/history/{version}` | GET |
| `/wikis/{wikiName}/spaces/{spaceName: .+}/search` | GET |
| `/wikis/{wikiName}/tags` | GET |
| `/wikis/{wikiName}/tags/{tagNames}` | GET |
| `/wikis/{wikiName}{spaceName : (/spaces/[^/]+)*}{pageName : (/pages/[^/]+)?}/notificationsWatches` | DELETE,GET,PUT |
| `/{iconTheme}/icons` | GET |
| `application.wadl` | GET |
| `{path}` | GET |
