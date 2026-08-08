# Webflow APIs
## URLs

Data API
Introduction
Token
GET
Get Authorization User Info
GET
Get Authorization Info
Sites
GET
List Sites
GET
Get Site
GET
Get Custom Domains
POST
Publish Site
Pages
GET
List Pages
GET
Get Page Metadata
PUT
Update Page Metadata
GET
Get Page Content
POST
Update Page Content
CMS

Collections
GET
List Collections
GET
Get Collection Details
POST
Create Collection
DEL
Delete Collection

Collection Fields
POST
Create Collection Field
PATCH
Update Collection Field
DEL
Delete Collection Field
Field Types & Item Values

Collection Items

Items
GET
List Collection Items
GET
Get Collection Item
POST
Create Collection Item
POST
Create Item for Multiple Locales
PATCH
Update Collection Item
DEL
Delete Collection Item
POST
Publish Collection Item

Live Items
GET
List Live Collection Items
GET
Get Live Collection Item
POST
Create Live Collection Item
PATCH
Update Live Collection Item
DEL
Delete Live Collection Item

https://developers.webflow.com/v2.0.0/data/reference/cms/collections/list

https://developers.webflow.com/v2.0.0/data/reference/cms/collections/get

https://developers.webflow.com/v2.0.0/data/reference/cms/collections/create

https://developers.webflow.com/v2.0.0/data/reference/cms/collections/delete

https://developers.webflow.com/v2.0.0/data/reference/cms/collection-fields/create


## Webflow CMS API
### Collections
#### Get Collection Details
CMS
Collections
Get Collection Details
GET
https://api.webflow.com/v2/collections/:collection_id
Get the full details of a collection from its ID.

Required scope | cms:read
Path parameters

collection_id
string
Required
Unique identifier for a Collection
Response

Request was successful
id
string
Unique identifier for a Collection
fields
list of objects
The list of fields in the Collection

Show 7 properties
displayName
string
Optional
Name given to the Collection
singularName
string
Optional
The name of one Item in Collection (e.g. ”Blog Post” if the Collection is called “Blog Posts”)
slug
string
Optional
Slug of Collection in Site URL structure
createdOn
datetime
Optional
Defaults to 1970-01-01T00:00:00.000Z
The date the collection was created
lastUpdated
datetime
Optional
Defaults to 1970-01-01T00:00:00.000Z
The date the collection was last updated
Errors


400
Collections Get Request Bad Request Error

401
Collections Get Request Unauthorized Error

404
Collections Get Request Not Found Error

429
Collections Get Request Too Many Requests Error

500
Collections Get Request Internal Server Error

200
Retrieved

{
  "id": "580e63fc8c9a982ac9b8b745",
  "fields": [
    {
      "id": "23cc2d952d4e4631ffd4345d2743db4e",
      "isRequired": true,
      "type": "PlainText",
      "displayName": "Name",
      "isEditable": true,
      "slug": "name",
      "helpText": "helpText"
    }
  ],
  "displayName": "Blog Posts",
  "singularName": "Blog Post",
  "slug": "post",
  "createdOn": "2016-10-24T19:41:48Z",
  "lastUpdated": "2016-10-24T19:42:38Z"
}