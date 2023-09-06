import asyncio
import sys
import os
import shutil
import errno
import time
import string
import random
import re
import json
from enum import Enum
from typing import Tuple,Generator,NamedTuple,List
from pathlib import Path
import zipfile
from ftplib import FTP,error_reply
from io import BytesIO, FileIO
from shutil import rmtree
from traceback import format_exc
from datetime import datetime

from frozendict import frozendict
import aiohttp
from google.auth.external_account_authorized_user import Credentials as cred_type_hint
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
#from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload, DEFAULT_CHUNK_SIZE
from psnawp_api import PSNAWP
from psnawp_api.core.psnawp_exceptions import PSNAWPNotFound
import interactions
from ps4debug import PS4Debug

def load_creds() -> Tuple[str,cred_type_hint]: 
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json",['https://www.googleapis.com/auth/drive'])
      
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json',['https://www.googleapis.com/auth/drive'])
            creds = flow.run_local_server(port=0)
        with open('token.json','w') as f:
            f.write(creds.to_json())
    drive_service = build('drive','v3',credentials=creds)
    return drive_service


drive_service = load_creds()

def is_ps4_title_id(input_str: str,/) -> bool: 
    return input_str.startswith('CUSA') and len(input_str) == 9 and input_str[-5:].isdigit()

id = '13yZnMsqj4le9Hw7LsJk1JvKapfcdCZx-'

def list_files_in_folder(parent_folder_id: str, parent_path: str | Path,lst: list = None) -> list[tuple[Path,str]]:
    if lst is None:
        lst = []
    results = drive_service.files().list(
        q=f"'{parent_folder_id}' in parents",
        fields="files(id, name, mimeType)"
    ).execute().get('files', [])

    

    for file in results:
        file_name = file['name']
        file_id = file['id']
        file_mime_type = file['mimeType']

        if 'application/vnd.google-apps.folder' in file_mime_type:
            # If it's a folder, recursively list its contents
            folder_path = Path(parent_path, file_name)
            list_files_in_folder(file_id, folder_path,lst)
        lst.append((Path(parent_path, file_name),file_id))
    return lst


class _PathWithNoIDInHash():
    def __init__(self,file_thing: tuple[Path,str]):
        self.file_thing = file_thing
    
    def __hash__(self):
        return hash(self.file_thing[0])
    
    def __eq__(self,other):
        return self.file_thing[0] == other.file_thing[0]

    def __getitem__(self,index):
        return self.file_thing[index]
    
    def __repr__(self):
        return f'{type(self).__name__}({self.file_thing!r})'


def _get_valid_saves_out_names_only(the_folder: list[tuple[Path,str]]) -> Generator[Tuple[Tuple[Path, str],Tuple[Path, str]], None, None]:
    """
    this function messes up if you use exact same path, but who tf be doing that
    """
    no_ids = {_PathWithNoIDInHash(x): x for x in the_folder}
    
    for filepath in no_ids:
        if is_ps4_title_id(filepath[0].parent.name):
            if filepath[0].name.endswith('.bin'):
                try:
                    white_file = no_ids[_PathWithNoIDInHash((filepath[0].with_suffix(''),''))]
                except KeyError:
                    pass
                else:
                    yield filepath,white_file
            else:
                try:
                    bin_file = no_ids[_PathWithNoIDInHash((filepath[0].with_suffix('.bin'),''))]
                except KeyError:
                    pass
                else:
                    yield bin_file,filepath

def get_valid_saves_out_names_only(the_folder: list[tuple[Path,str]]) -> set[Tuple[Tuple[Path, str],Tuple[Path, str]]]:
    return {x for x in _get_valid_saves_out_names_only(the_folder)}

import pickle

with open('HELLNAH.bin','rb') as f:
    e = pickle.load(f)


with open('HELLNAH.bin','wb') as f:
    pickle.dump(e, f)

for x in get_valid_saves_out_names_only(e):
    print('SYOP???',x)