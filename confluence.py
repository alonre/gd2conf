import json
import logging
import os
import requests
import urllib


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

CONFLUENCE_USER = os.environ.get("CONFLUENCE_USER", "admin")
CONFLUENCE_PASS = os.environ.get("CONFLUENCE_PASS", "admin")
CONFLUENCE_COOKIE = os.environ.get("CONFLUENCE_COOKIE", "")

CONFLUENCE_SERVER_URL = os.environ.get("CONFLUENCE_SERVER_URL", "https://wiki.singular.net")
IMPORT_WORD_URL = "{base}/pages/worddav/importword.action".format(base=CONFLUENCE_SERVER_URL)
DO_IMPORT_URL = "{base}/pages/worddav/doimportword.action".format(base=CONFLUENCE_SERVER_URL)

GOOGLE_SPREADSHEET_SOURCE =
def create_page(space_key, title, body="", parent_id=None):
    url = "{base}/rest/api/content".format(base=CONFLUENCE_SERVER_URL)
    payload = {
        "type": "page",
        "title": title,
        "space": {
            "key": space_key
        },
        "body": {
            "storage": {
                "value": body,
                "representation": "storage"
            }
        }
    }

    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    response = requests.request("POST", url, auth=(CONFLUENCE_USER, CONFLUENCE_PASS), json=payload)
    print(response.status_code)
    return json.loads(response.text)


def comment_on_page(page_id, comment_text):
    url = "{base}/rest/api/content".format(base=CONFLUENCE_SERVER_URL)
    payload = {
        "type": "comment",
        "container": {
            "type": "page",
            "id": page_id
        },
        "body": {
            "storage": {
                "value": comment_text,
                "representation": "storage"
            }
        }
    }

    response = requests.request("POST", url, auth=(CONFLUENCE_USER, CONFLUENCE_PASS), json=payload)
    print(response.status_code)
    return json.loads(response.text)

def upload_attachment(page_id, file_name, file_path, comment):
    url = "{base}/rest/api/content/{page_id}/child/attachment".format(base=CONFLUENCE_SERVER_URL, page_id=page_id)
    files = {'file': (file_name, open(file_path, 'rb'))}
    payload = {
        "comment": comment
    }
    headers = {
        'X-Atlassian-Token': "no-check",
    }
    response = requests.request("POST", url,
                                headers=headers,
                                auth=(CONFLUENCE_USER, CONFLUENCE_PASS),
                                data=payload,
                                files=files)
    print(response.status_code)
    return json.loads(response.text)


def import_google_doc(google_item, page_id):
    _import_word(page_id, google_item['file_name'], google_item['file_content'])
    _do_import_word(page_id, 0, google_item['name'])


def _import_word(page_id, file_name, file_content):
    querystring = {"pageId": page_id}
    files = {'filename': (file_name, file_content)}
    headers = {
        'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        'X-Atlassian-Token': "no-check",
        "Cookie": "JSESSIONID={};".format(CONFLUENCE_COOKIE)
    }

    response = requests.request("POST", IMPORT_WORD_URL,
                                files=files,
                                headers=headers,
                                params=querystring,
                                auth=(CONFLUENCE_USER, CONFLUENCE_PASS))

    print(response.status_code)
    with open('response.html', 'w') as f:
        f.write(response.text)


def _do_import_word(page_id, tree_depth, doc_title, conflict=1, import_to_space=False, overwrite_all=False, level=0):
    payload = {
        "pageId": page_id,
        "treeDepth": tree_depth,
        "advanced": 'true',
        "docTitle": doc_title,
        "importSpace": 'true' if import_to_space else 'false',
        "overwriteAll": 'true' if overwrite_all else 'false',
        "conflict": conflict,
        "lvl": level,
        "submit": "Import"
    }

    data = urllib.parse.urlencode(payload)
    print(data)
    data = data.encode("ascii")

    headers = {
        'Content-Type': "application/x-www-form-urlencoded",
        'X-Atlassian-Token': "no-check",
        "Cookie": "JSESSIONID={};".format(CONFLUENCE_COOKIE)
    }

    response = requests.request("POST", DO_IMPORT_URL,
                                data=data,
                                headers=headers,
                                auth=(CONFLUENCE_USER, CONFLUENCE_PASS))

    print(response.status_code)
    with open('response.html', 'w') as f:
        f.write(response.text)