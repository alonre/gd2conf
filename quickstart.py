from __future__ import print_function
import confluence
import datetime
import json
from googleapiclient import errors
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
import io
import logging
from mime_types import MimeTypes
from oauth2client import file, client, tools


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/drive'


class GDriveMigrator(object):
    def __init__(self):
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        self.drive_service = build('drive', 'v3', http=creds.authorize(Http()))

    def download_doc(self, file_name, file_id):
        request = self.drive_service.files().export_media(fileId=file_id, mimeType=MimeTypes.MS_WORD_DOC)
        fh = io.BytesIO()
        #fh = open('{}.doc'.format(file_name), 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download {}%.".format(int(status.progress() * 100)))
        fh.seek(0)
        return fh

    def get_metadata(self, item_id):
        root_md = self.drive_service.files().get(fileId=item_id, fields="id, name, mimeType, webViewLink").execute()
        return root_md

    def migrate_google_doc(self, item, page_id):
        try:
            item['file_content'] = self.download_doc(item['name'], item['id'])
            item['file_name'] = '{}.doc'.format(item['name'])
            confluence.import_google_doc(item, page_id)
        except:
            pass

    def migrate_google_spreadsheet(self, item, page_id):
        try:
            self.download_doc(item['name'], item['id'])
        except:
            pass

    def migrate_to_confluence(self, root_item, target_space_key, parent_page_id):
        logger.debug("Migrating item:{} into space:{} parentId:{}".format(root_item['id'], target_space_key, parent_page_id))

        logger.debug("Result: name: {} mimeType: {}".format(root_item['name'], root_item['mimeType']))

        # create root page in Confluence
        c_root = confluence.create_page(target_space_key, root_item['name'], parent_id=parent_page_id)
        if not 'id' in c_root:
            page_title = "{} (GDrive import {})".format(root_item['name'], datetime.date.today())
            c_root = confluence.create_page(target_space_key, page_title, parent_id=parent_page_id)
        logger.debug("Created root page in Confluence: {}".format(c_root))
        root_page_id = c_root.get('id', None)
        import_comment = "Automagically imported from: {}".format(root_item['webViewLink'])
        confluence.comment_on_page(root_page_id, import_comment)

        # according to mimeType, do the right thing
        mimeType = root_item['mimeType']
        if mimeType == MimeTypes.GOOGLE_APPS_FOLDER:
            # traverse folder
            page_token = None
            while True:
                try:
                    param = {
                        'q': "'{}' in parents".format(root_item['id']),
                        'pageSize': 10,
                        'fields': "nextPageToken, files(id, name, mimeType, webViewLink)"
                    }
                    if page_token:
                        param['pageToken'] = page_token
                    results = self.drive_service.files().list(**param).execute()
                    items = results.get('files', [])
                    if not items:
                        logger.debug('No files found.')
                    else:
                        logger.debug('Files:')
                        for item in items:
                            logger.debug('{0} ({1} {2})'.format(item['name'], item['id'], item['mimeType']))
                            self.migrate_to_confluence(item, target_space_key, root_page_id)
                    page_token = results.get('nextPageToken')
                    if not page_token:
                        break
                except errors.HttpError as error:
                    logger.error("{}".format(error))
                    break
        elif mimeType == MimeTypes.GOOGLE_DOC:
            self.migrate_google_doc(root_item, root_page_id)
        elif mimeType == MimeTypes.GOOGLE_SPREADSHEET:
            self.migrate_google_spreadsheet(root_item, root_page_id)
        # elif mimeType == MimeTypes.GOOGLE_SLIDES:



def main():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    migrator = GDriveMigrator()
    root_md = migrator.get_metadata('1f746Qv1Id7gD-EX_3bSbRxWAUw_ANYlg')
    migrator.migrate_to_confluence(root_md, 'ds', "65538")


if __name__ == '__main__':
    main()