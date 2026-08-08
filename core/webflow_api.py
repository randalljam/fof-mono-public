# ===== START OF FILE secondary/webflow.py =====
# Library of functions and execution code to do Webflow tasks

import os
from dotenv import load_dotenv
import markdown
from webflow.client import Webflow
import requests

from core.fileops import *

# ---API KEYS AND SECRETS---
load_dotenv(override=True)  # Load environment variables from .env file
WEBFLOW_API_KEY_FOF_ALL = os.environ["WEBFLOW_API_KEY_FOF_ALL"]
WEBFLOW_API_KEY_FOF_CMS = os.environ["WEBFLOW_API_KEY_FOF_CMS"]

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

# Initialize the Webflow API client
client = Webflow(access_token=WEBFLOW_API_KEY_FOF_CMS)

### WEBFLOW SITES
SITE_ID_FOF = "66f32336260d050c6e0fffa0"
SITE_ID_FLOODLAMP = "65678d3d31e9a39323f82b37"
def mrun_print_site_info():
    pass
#if __name__ == "__main__":
    cur_site_id = SITE_ID_FOF
    site_info = client.sites.get(site_id=cur_site_id)
    print(f"Site Info for site_id: {cur_site_id}")
    print(f"ID: {site_info.id}")
    print(f"Workspace ID: {site_info.workspace_id}")
    print(f"Created On: {site_info.created_on}")
    print(f"Display Name: {site_info.display_name}")
    print(f"Short Name: {site_info.short_name}")
    print(f"Last Published: {site_info.last_published}")
    print(f"Last Updated: {site_info.last_updated}")
    print(f"Preview URL: {site_info.preview_url}")
    print(f"Time Zone: {site_info.time_zone}")
    print(f"Custom Domains: {site_info.custom_domains}")
def webflow_pages_list(site_id, locale_id=None, verbose=False, api_key=None, page_size=100):
    """
    Lists all pages for a Webflow site.

    :param site_id: string, the Webflow site id.
    :param locale_id: string, optional locale id for localized page reads.
    :param verbose: boolean, whether to print page summaries.
    :param api_key: string, optional explicit api key override.
    :param page_size: int, number of pages to request per page.
    :return pages: list, the returned Webflow page objects.
    """
    try:
        all_pages = []
        offset = 0
        while True:
            params = {
                "limit": page_size,
                "offset": offset,
            }
            if locale_id:
                params["localeId"] = locale_id
            response = requests.get(f"https://api.webflow.com/v2/sites/{site_id}/pages", headers=_webflow_headers(api_key=api_key), params=params)
            if response.status_code != 200:
                if verbose:
                    print(colored(f"Error listing pages. Status code: {response.status_code}", "red"))
                    print(f"Response: {response.text}")
                return []
            page_items = response.json().get("pages", [])
            all_pages.extend(page_items)
            pagination = response.json().get("pagination", {})
            total = pagination.get("total")
            if total is not None and len(all_pages) >= total:
                break
            if len(page_items) < page_size:
                break
            offset += page_size
        if verbose:
            print(f"Webflow pages for site {site_id}: {len(all_pages)}")
            for page in all_pages:
                print(f"- {page.get('title') or page.get('name') or 'Untitled'} | slug={page.get('slug')} | id={page.get('id')}")
        return all_pages
    except Exception as e:
        if verbose:
            print(colored(f"Error listing pages: {str(e)}", "red"))
        return []
def webflow_pages_get_page_by_slug(site_id, slug, locale_id=None, verbose=False, api_key=None):
    """
    Gets a Webflow page object by slug.

    :param site_id: string, the Webflow site id.
    :param slug: string, the page slug to look up.
    :param locale_id: string, optional locale id for localized page reads.
    :param verbose: boolean, whether to print the matched page.
    :param api_key: string, optional explicit api key override.
    :return page: dict, the matched page object or an empty dict.
    """
    for page in webflow_pages_list(site_id, locale_id=locale_id, verbose=False, api_key=api_key):
        if page.get("slug") == slug:
            if verbose:
                print(f"Matched page slug '{slug}' to page id {page.get('id')}")
            return page
    if verbose:
        print(f"No Webflow page found for slug '{slug}' on site {site_id}.")
    return {}
def mrun_webflow_pages_list():
    pass
#if __name__ == "__main__":
    cur_site_id = SITE_ID_FLOODLAMP
    webflow_pages_list(cur_site_id, verbose=True)

DEUTSCH_INTERVIEWS_VRBS_ID = "6711b684a9e995b7c0f06e17"  # for test one - not the real interviews collection
FDA_C19_TOWNHALLS_ID = "6780532037b7b191793c3544"
SOVEREIGN_CHILD_ID = "67b1eb365b3e0e9c63aa3cf5"

### WEBFLOW CMS
def _webflow_headers(api_key=None, include_json=False):
    """
    Builds headers for Webflow v2 API requests.

    :param api_key: string, optional explicit api key override.
    :param include_json: boolean, whether to include a JSON content-type header.
    :return headers: dict, the request headers.
    """
    resolved_api_key = api_key or WEBFLOW_API_KEY_FOF_ALL
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {resolved_api_key}"
    }
    if include_json:
        headers["content-type"] = "application/json"
    return headers
def webflow_cms_get_collection_details(collection_id, debug=False, verbose=True, api_key=None):
    """
    Get the full details of a collection from its ID.

    :param collection_id: str, the ID of the Webflow CMS collection.
    :param debug: bool, if True prints raw API response details.
    :param verbose: bool, if True prints formatted collection details.
    :param api_key: string, optional explicit api key override.
    :return: dict, a dictionary containing the collection details or None if an error occurs.
    """
    try:
        # Construct the URL
        url = f"https://api.webflow.com/v2/collections/{collection_id}"

        # Make the request
        response = requests.get(url, headers=_webflow_headers(api_key=api_key))
        
        if debug: 
            print("Raw API response:")
            print(f"Status Code: {response.status_code}")
            print("Headers:")
            print(response.headers)
            print("Content:")
            print(response.text)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        
        collection_details = {
            "id": data.get("id"),
            "name": data.get("displayName"),
            "slug": data.get("slug"),
            "singularName": data.get("singularName"),
            "fields": data.get("fields", []),
            "createdOn": data.get("createdOn"),
            "lastUpdated": data.get("lastUpdated")
        }

        if verbose:
            print(f"Collection Details for {collection_details['name']}:")
            for key, value in collection_details.items():
                if key != "fields":
                    print(f"{key}: {value}")
                else:
                    filtered_fields = [f for f in value if f.get('slug') not in ['name', 'slug']]
                    print(f"Number of fields: {len(filtered_fields)}")
                    print("Fields:")
                    # Print header row
                    print(f"{'Field Name':<25} {'Type':<15} {'Status':<15} {'Slug'}")
                    print("-" * 80)  # Separator line
                    for field in filtered_fields:
                        field_type = field.get('type', 'Unknown')
                        field_name = field.get('displayName', 'Unnamed')
                        field_slug = field.get('slug', 'no-slug')
                        field_required = "Required" if field.get('isRequired') else "Optional"
                        print(f"\033[33m{field_name:<25}\033[0m {field_type:<15} {field_required:<15} {field_slug}")
                    print("-" * 80)  # Separator line

        return collection_details
    except requests.exceptions.RequestException as e:
        print(f"Error fetching collection details: {str(e)}")
        return None
def mrun_get_collection_details():
    pass
if __name__ == "__main__":
    cur_collection_id = SOVEREIGN_CHILD_ID
    collection_details = webflow_cms_get_collection_details(cur_collection_id, verbose=True)

def webflow_cms_import_heading(collection_id, file_path, heading):
    """
    Imports a markdown heading and its content into a Webflow CMS collection.

    :param collection_id: str, the ID of the Webflow CMS collection to import into.
    :param file_path: str, the path to the markdown file to extract content from.
    :param heading: str, the heading to extract from the markdown file, including '#' characters.
    :return created_item_id: str, the ID of the newly created Webflow CMS item or None if heading not found.
    """
    # Get the markdown content for the specified heading
    markdown_text = get_heading(file_path, heading)

    if markdown_text is None:
        print(f"Heading '{heading}' not found in file '{file_path}'")
        return None

    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_text)

    # Create a title for the item based on the heading
    item_title = os.path.splitext(os.path.basename(file_path))[0] + '_' + heading.strip('#').strip()
    item_slug = item_title.lower().replace(' ', '-')

    new_item = {
        'fields': {
            'name': item_title,  # Required name field
            'slug': item_slug,   # Required slug field
            'transcript-vrb': html_content  # This is your custom rich text field
        }
    }

    # Create the item in the Webflow collection
    created_item = client.collections.create_item(collection_id=collection_id, data=new_item)
    print(f"Created new item with ID: {created_item['_id']}")

    return created_item['_id']

def webflow_cms_list_items(collection_id, include_archived=True, verbose=False, api_key=None, page_size=100):
    """
    Lists all items in a Webflow collection.

    :param collection_id: str, the ID of the Webflow CMS collection
    :param include_archived: bool, whether to include archived/trashed items
    :param verbose: bool, whether to print API response details
    :param api_key: string, optional explicit api key override.
    :param page_size: int, number of items to request per page.
    :return: list of items or None if the request fails
    """
    try:
        all_items = []
        offset = 0
        while True:
            params = {
                "limit": page_size,
                "offset": offset,
            }
            if include_archived:
                params["archived"] = "true"
            response = requests.get(f'https://api.webflow.com/v2/collections/{collection_id}/items', headers=_webflow_headers(api_key=api_key), params=params)
            if response.status_code != 200:
                if verbose:
                    print(colored(f"Error listing items. Status code: {response.status_code}", "red"))
                    print(f"Response: {response.text}")
                return None
            page_items = response.json().get('items', [])
            all_items.extend(page_items)
            if len(page_items) < page_size:
                break
            offset += page_size
        if verbose:
            for item in all_items:
                archived_status = " (ARCHIVED)" if item.get('archived', False) else ""
                print(f"ID: {item['id']}, Name: {item['fieldData'].get('name', 'N/A')}, "
                      f"Slug: {item['fieldData'].get('slug', 'N/A')}{archived_status}")
            print(f"\nTotal items: {len(all_items)}")
        return all_items
            
    except Exception as e:
        if verbose:
            print(colored(f"Error listing items: {str(e)}", "red"))
        return None
def mrun_webflow_cms_list_items():
    pass
#if __name__ == "__main__":
    cur_collection_id = SOVEREIGN_CHILD_ID
    items = webflow_cms_list_items(cur_collection_id, verbose=True)

def webflow_cms_import_transcript_and_qa(collection_id, transcript_file_path, qa_suffix='_qa-qonly', verbose=False):
    """
    Imports a transcript and its associated URLs into a Webflow CMS collection.

    :param collection_id: str, the ID of the Webflow CMS collection to import into.
    :param transcript_file_path: str, the path to the markdown file containing the transcript.
    :param qa_suffix: str, unused parameter kept for backwards compatibility.
    :param verbose: bool, whether to print truncated field values.
    :return created_item_id: str, the ID of the newly created Webflow CMS item or None if error occurs.
    """
    # Get URLs and transcript text - extract just the URL string if it's a tuple
    pdf_url = read_metadata_field_from_file(transcript_file_path, 'link pdf')
    pdf_url = pdf_url[1] if isinstance(pdf_url, tuple) else pdf_url
    
    youtube_url = read_metadata_field_from_file(transcript_file_path, 'link youtube')
    youtube_url = youtube_url[1] if isinstance(youtube_url, tuple) else youtube_url
    
    #transcript_text = get_heading(transcript_file_path, '### transcript')
    transcript_text = 'This is dummy transcript text'
    
    if transcript_text is None:
        print(f"Transcript not found in file '{transcript_file_path}'")
        return None

    # Create a title and slug from the filename
    item_title = os.path.splitext(os.path.basename(transcript_file_path))[0]
    item_slug = item_title.lower().replace(' ', '-')

    # Restructure the data format to match v2 API requirements
    new_item = {
        'fieldData': {
            'name': item_title,
            'slug': item_slug,
            'md-mod-txt': transcript_text,
            'pdf-url': pdf_url if pdf_url else '',
            'youtube-url-3': youtube_url if youtube_url else ''
        }
    }

    if verbose:
        print("\nField values (truncated to 100 chars):")
        for field, value in new_item['fieldData'].items():
            truncated_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"{field}: {truncated_value}")

    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {WEBFLOW_API_KEY_FOF_ALL}"
        }
        
        # The v2 API expects a wrapper object with 'items' array
        request_body = {
            'items': [new_item]
        }
        
        response = requests.post(
            f'https://api.webflow.com/v2/collections/{collection_id}/items',
            headers=headers,
            json=request_body
        )
        
        if response.status_code == 200:
            created_item = response.json()
            print(f"Created new item with ID: {created_item['id']}")
            return created_item['id']
        else:
            print(f"Error creating item. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating item: {str(e)}")
        return None
def mrun_webflow_cms_import_transcript_and_qa():
    pass
#if __name__ == "__main__":
    cur_collection_id = FDA_C19_TOWNHALLS_ID
    transcript_file_path = 'data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto/2020-12-09_Virtual Town Hall 36_fixnames.md'
    webflow_cms_import_transcript_and_qa(cur_collection_id, transcript_file_path, verbose=True)
def webflow_cms_create_item(collection_id, field_data, collection_validation=True, verbose=False, api_key=None):
    """
    Creates a new item in a Webflow collection after validating the field data.

    :param collection_id: str, the ID of the Webflow CMS collection.
    :param field_data: dict, the data for all fields to be created.
    :param collection_validation: bool, whether to validate fields against collection schema
    :param verbose: bool, whether to print field validation and API response details.
    :param api_key: string, optional explicit api key override.
    :return: str, the ID of the newly created item or None if validation/creation fails.
    """
    # Get collection details and validate fields only if collection_validation is True
    if collection_validation:
        collection_details = webflow_cms_get_collection_details(collection_id, verbose=False, api_key=api_key)
        if not collection_details:
            print("Failed to fetch collection details for validation")
            return None

        # Extract required fields from collection schema
        required_fields = {
            field.get('slug'): field.get('type') 
            for field in collection_details['fields'] 
            if field.get('isRequired')
        }
        
        # Validate required fields
        missing_fields = [field for field in required_fields.keys() if field not in field_data]
        if missing_fields:
            print(f"Error: Missing required fields: {', '.join(missing_fields)}")
            return None

    if verbose:
        print("\nField values (truncated to 100 chars):")
        for field, value in field_data.items():
            truncated_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            print(f"{field}: {truncated_value}")

    # Prepare request data
    new_item = {
        'fieldData': field_data
    }
    
    request_body = {
        'items': [new_item]
    }

    try:
        response = requests.post(
            f'https://api.webflow.com/v2/collections/{collection_id}/items',
            headers=_webflow_headers(api_key=api_key, include_json=True),
            json=request_body
        )
        
        if response.status_code in [200, 202]:
            created_item = response.json()
            if verbose:
                print(colored(f"Successfully created item name: {created_item['items'][0]['fieldData']['name']}  ID: {created_item['items'][0]['id']}", "green"))
            return created_item['items'][0]['id']
        else:
            print(colored(f"Error creating item. Status code: {response.status_code}", "red"))
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(colored(f"Error creating item: {str(e)}", "red"))
        return None
def mtest_webflow_cms_create_item():
    pass
#if __name__ == "__main__":
    cur_collection_id = FDA_C19_TOWNHALLS_ID
    field_data = {
        'name': 'Test Item',
        'slug': 'test-item',
        'md-mod-txt': 'This is a test item',
        'pdf-url': 'https://example.com/test.pdf',
        'youtube-url-3': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    }
    webflow_cms_create_item(cur_collection_id, field_data, collection_validation=False, verbose=True)
def webflow_cms_update_item(collection_id, item_id, field_data, collection_validation=True, verbose=False, api_key=None):
    """
    Updates an existing item in a Webflow collection.

    :param collection_id: str, the ID of the Webflow CMS collection
    :param item_id: str, the ID of the item to update
    :param field_data: dict, the updated field data
    :param collection_validation: bool, whether to validate fields against collection schema
    :param verbose: bool, whether to print field validation and API response details
    :param api_key: string, optional explicit api key override.
    :return: bool indicating success or failure
    """
    if collection_validation:
        collection_details = webflow_cms_get_collection_details(collection_id, verbose=False, api_key=api_key)
        if not collection_details:
            print("Failed to fetch collection details for validation")
            return False

    try:
        request_body = {
            "fieldData": field_data
        }
        
        response = requests.patch(
            f'https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}',
            headers=_webflow_headers(api_key=api_key, include_json=True),
            json=request_body
        )
        
        if response.status_code in [200, 202]:
            if verbose:
                print(f"Successfully updated item with ID: {item_id}  name: {field_data.get('name', '(unknown)')}")
            return True
        else:
            if verbose:
                print(f"Error updating item. Status code: {response.status_code}")
                print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        if verbose:
            print(f"Error updating item: {str(e)}")
        return False
def webflow_cms_delete_item(collection_id, item_id, verbose=False, api_key=None):
    """
    Deletes an existing item from a Webflow collection.

    :param collection_id: str, the ID of the Webflow CMS collection.
    :param item_id: str, the ID of the item to delete.
    :param verbose: bool, whether to print API response details.
    :param api_key: string, optional explicit api key override.
    :return: bool, True when the delete succeeds.
    """
    try:
        response = requests.delete(
            f'https://api.webflow.com/v2/collections/{collection_id}/items/{item_id}',
            headers=_webflow_headers(api_key=api_key)
        )
        if response.status_code in [200, 202, 204]:
            if verbose:
                print(f"Successfully deleted item with ID: {item_id}")
            return True
        if verbose:
            print(f"Error deleting item. Status code: {response.status_code}")
            print(f"Response: {response.text}")
        return False
    except Exception as e:
        if verbose:
            print(f"Error deleting item: {str(e)}")
        return False

### WEBFLOW CMS helpers
def webflow_cms_get_collection_field_slugs(collection_id, include_builtin=True, verbose=False, api_key=None):
    """
    Gets the field slugs for a Webflow collection.

    :param collection_id: string, the id of the Webflow CMS collection.
    :param include_builtin: boolean, whether to include the built-in name and slug fields.
    :param verbose: boolean, whether to print the returned field slugs.
    :param api_key: string, optional explicit api key override.
    :return field_slugs: list, the collection field slugs.
    """
    collection_details = webflow_cms_get_collection_details(collection_id, verbose=False, api_key=api_key)
    if not collection_details:
        return []
    field_slugs = []
    for field in collection_details.get("fields", []):
        field_slug = field.get("slug")
        if not field_slug:
            continue
        if not include_builtin and field_slug in ["name", "slug"]:
            continue
        field_slugs.append(field_slug)
    if verbose:
        print(f"Collection field slugs ({len(field_slugs)}):")
        for field_slug in field_slugs:
            print(f"- {field_slug}")
    return field_slugs
def webflow_cms_get_existing_items_map(collection_id, key_field="name", include_archived=True, verbose=False, api_key=None):
    """
    Builds a lookup map for existing Webflow CMS items.

    :param collection_id: string, the id of the Webflow CMS collection.
    :param key_field: string, the fieldData key to use as the lookup key.
    :param include_archived: boolean, whether to include archived items in the lookup.
    :param verbose: boolean, whether to print a summary of the lookup map.
    :param api_key: string, optional explicit api key override.
    :return items_map: dict, mapping field values to item ids.
    """
    items = webflow_cms_list_items(collection_id, include_archived=include_archived, verbose=False, api_key=api_key)
    if not items:
        if verbose:
            print(f"No existing items found for collection {collection_id}.")
        return {}
    items_map = {}
    for item in items:
        field_data = item.get("fieldData", {})
        field_value = field_data.get(key_field)
        item_id = item.get("id")
        if not field_value or not item_id:
            continue
        items_map[field_value] = item_id
    if verbose:
        print(f"Existing Webflow items indexed by '{key_field}': {len(items_map)}")
    return items_map
# ===== END OF FILE secondary/webflow.py =====
