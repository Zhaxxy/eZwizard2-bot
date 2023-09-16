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
from sqlitedict import SqliteDict
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

from savemount_py import PatchMemoryPS4900,MountSave,AccountID,MemoryIsPatched,unmount_save
from custom_cheats import shantae_pirate_curse_cheats
from custom_cheats import black_ops_cold_war
from custom_cheats import red_dead_redemption_2
from custom_cheats import littlebigplanet_3

FILE_SIZE_TOTAL_LIMIT = 600_000_000 # 600mb
ATTACHMENT_MAX_FILE_SIZE = 24_000_000 # 24mb
ZIP_LOOSE_FILES_MAX_AMT = 100
MAX_RESIGNS_PER_ONCE = 99

SUCCESS_MSG = 'Your save was accepted! please wait until we ping you with a link to the new save'
BOT_IN_USE_MSG = 'Sorry, the bot is currently in use! please wait...'
INVALID_GDRIVE_URl_TEMPLATE = 'Invalid gdrive folder url {}. did you make sure its public? is it a folder link?'


class DriveFileWithParentDir(NamedTuple):
    parent_dir: dict
    file: dict

class TempThingIdk(NamedTuple):
    error_code: int
    def __bool__(self):
        return False
    
async def download_file(url, destination: Path):
    """
    function by chatGPT
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(destination, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
            else:
                raise Exception(f"Error: Unable to download file from {url}, status code: {response.status}")


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
                    yield no_ids[filepath],white_file
            else:
                try:
                    bin_file = no_ids[_PathWithNoIDInHash((filepath[0].with_suffix('.bin'),''))]
                except KeyError:
                    pass
                else:
                    yield bin_file,no_ids[filepath]

def get_valid_saves_out_names_only(the_folder: list[tuple[Path,str]]) -> set[Tuple[Tuple[Path, str],Tuple[Path, str]]]:
    return {x for x in _get_valid_saves_out_names_only(the_folder)}


def make_folder_name_safe(name: str) -> str:
    name = name.replace(' ','_').replace('/','_').replace('\\','_').replace('\\','_')
    result = "".join(c for c in name if c.isalnum() or c in ('_','-')).rstrip()
    return result if result else 'no_name'



def initialise_database():
    pass


def get_user_account_id(author_id: str):
    with SqliteDict("user_stuff.sqlite", tablename="user_account_ids") as db:
        return db[author_id]

def add_user_account_id(author_id: str,new_account_id: str):
    author_id = str(author_id)
    new_account_id = str(new_account_id)
    with SqliteDict("user_stuff.sqlite", tablename="user_account_ids") as db:
        db[author_id] = new_account_id
        db.commit()

leh_current_time = 0 
def sgt() -> None:
    global leh_current_time
    leh_current_time = time.perf_counter()

def istl() -> bool:
    global leh_current_time
    return time.perf_counter() - leh_current_time < 14*60

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
    return creds,drive_service


def load_config() -> Tuple[str,int,str,str]:
    try:
        with open('ps4_stuff_config.json','r') as f:
            config = json.load(f)
            
            PS4_IP,USER_ID,TITLE_ID,SAVE_DIR = config['ps4_ip'], int(config['user_id'],16), config['title_id'], config['save_dir']
    except FileNotFoundError:
        with open('ps4_stuff_config.json','w') as f:
            json.dump({'ps4_ip':'1.1.1.2','user_id':'1eb71bbd','title_id':'','save_dir':''},f,indent=2)
        raise ValueError('Please configure the script in the ps4_stuff_config.json file')

    if not(PS4_IP and USER_ID and TITLE_ID and SAVE_DIR):
        raise ValueError('Please configure the script in the ps4_stuff_config.json file')
    
    return PS4_IP,USER_ID,TITLE_ID,SAVE_DIR

def ftp_login_and_connect(HOST, PORT=21): #simple function used to login in anymouslly to a ftp server
    ftp = FTP()
    ftp.connect(HOST, PORT)
    ftp.login()
    return ftp

def ftpdownload(ftp, FILE, DIR='', DESTINATION_NAME=''): #download a file from ftp, you must define the dir though or just looks in root
    old_mememory = ftp.pwd()
    if not DIR == '':
        ftp.cwd(DIR)
    
    if DESTINATION_NAME == '':
        ftp.retrbinary("RETR " + FILE ,open(FILE, 'wb').write)
    else:
        ftp.retrbinary("RETR " + FILE ,open(DESTINATION_NAME, 'wb').write)
    ftp.cwd(old_mememory)

def ftpupload(ftp, FILE, DIR='', REAL_NAME=''): #upload file to ftp server, must define a dir though or just looks in root
    old_mememory = ftp.pwd()
    if not DIR == '':
        ftp.cwd(DIR)
    
    if REAL_NAME == '':
        ftp.storbinary('STOR ' + FILE, open(FILE, 'rb'))
    else:
        ftp.storbinary('STOR ' + FILE, open(REAL_NAME, 'rb'))
    ftp.cwd(old_mememory)


def ftp_login_and_connect(HOST, PORT=21): #simple function used to login in anymouslly to a ftp server
    ftp = FTP()
    ftp.connect(HOST, PORT)
    ftp.login()
    return ftp

def _get_list_LIST(path,ftp):
    lines = []
    ftp.retrlines('LIST ' +path , lines.append)
    lines.pop(0); lines.pop(0) #ill come up with a cleaner method later, get rid of useless non files
    return lines

def list_all_files_in_folder_ftp(ftp,source_folder='') -> list[tuple[str,bool]]: #gets a list of all the folders and files in a folder (inlcuding subdirs), this one took me a while to make!
    old_mememory = ftp.pwd()
    filesnfolders = []
    ftp.cwd(source_folder)

    def recur_over_folder(list,path=source_folder):
        for file in _get_list_LIST(path,ftp):
            clean_path = f'{path}/{file.split()[-1]}'
            filesnfolders.append((clean_path,file.startswith("-")))
            if not file.startswith("-"): #again need a cleaner method, used to detirmine if its a file or folder, if it starts with - then its a file
                ftp.cwd(f'{path}/{file.split()[-1]}')
                recur_over_folder(filesnfolders,f'{path}/{file.split()[-1]}')
    recur_over_folder(filesnfolders)
    ftp.cwd(old_mememory)
    return filesnfolders

def ftp_delete_file(ftp: FTP, ftp_path: str):
    try:
        ftp.delete(ftp_path)
    except error_reply as e:
        if not e.args[0].startswith('226'): # this is soo idiotic, why does it even raise that error?
            raise


def delete_folder_contents(ftp: FTP, folder_with_stuff: str,*,dont_delete_sce_sys: bool = True):
    old_memory = ftp.pwd()
    ftp.cwd(folder_with_stuff)
    
    for file in list_all_files_in_folder_ftp(ftp,folder_with_stuff):
        if dont_delete_sce_sys and file[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys'):
            continue
        if file[1]:
            ftp_delete_file(ftp,file[0])
    
    for folder in list_all_files_in_folder_ftp(ftp,folder_with_stuff):#
        if dont_delete_sce_sys and folder[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys'):
            continue
        assert not folder[1], 'we should of already deleted all files!'
        ftp.rmd(folder[0])
        
    ftp.cwd(old_memory)

def download_ftp_folder(ftp: FTP, folder2download: str, download_loc: Path):
    for file in list_all_files_in_folder_ftp(ftp,folder2download):
        i_want_this = Path(file[0]).relative_to(Path(folder2download))
        if file[1]:
            Path(download_loc,i_want_this.parent).mkdir(parents=True, exist_ok=True)
            ftpdownload(ftp,Path(Path(file[0]).name).as_posix(),Path(Path(file[0]).parent).as_posix(),Path(download_loc,i_want_this))
        else:
            Path(download_loc,i_want_this).mkdir(parents=True, exist_ok=True)


def upload_folder_contents(ftp: FTP,folder2uploadto: str, folderwithstuff: Path):
    old_mem = ftp.pwd()
    ftp.cwd(folder2uploadto)
    for filename in folderwithstuff.rglob('*'):  
        i_want_this = Path(filename).relative_to(Path(folderwithstuff))
        if filename.is_dir():
            try:
                ftp.mkd(i_want_this.as_posix())
            except Exception:
                pass
        else:
            ftp.cwd(Path(folder2uploadto,i_want_this.parent).as_posix())
            with open(filename,'rb') as f:
                ftp.storbinary(f'STOR {Path(i_want_this.name).as_posix()}',f)
        ftp.cwd(folder2uploadto)
    ftp.cwd(old_mem)


def is_ps4_title_id(input_str: str,/) -> bool: 
    return input_str.startswith('CUSA') and len(input_str) == 9 and input_str[-5:].isdigit()

def list_ps4_saves(folder_containing_saves: Path,/,delete_none_saves: bool = False) -> Generator[Tuple[Path,Path],None,None]:
    for filename in folder_containing_saves.rglob('*'):
        if is_ps4_title_id(filename.parent.name) and filename.suffix == '.bin' and filename.is_file() and Path(filename.with_suffix('').as_posix()).is_file():
            yield filename,Path(filename.with_suffix('').as_posix())
        elif delete_none_saves and filename.is_file() and not filename.with_suffix('.bin').is_file():
            os.remove(filename)


def resign_param_sfo(param_sfo: BytesIO,/,account_id: AccountID):
    param_sfo.seek(0x15c)
    param_sfo.write(account_id.to_bytes())
    param_sfo.seek(0)

async def upload_save_to_ps4(bin_file: Path, white_file: Path, ctx: interactions.SlashContext):
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...')
    await loop.run_in_executor(None,ftpupload,ftp,f'sdimg_{psd}',save_folder_ftp,white_file)
    await loop.run_in_executor(None,ftpupload,ftp,f'{psd}.bin',save_folder_ftp,bin_file)
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nDONE UPLOADING {white_file.name} to PS4',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDONE UPLOADING {white_file.name} to PS4')

async def download_save_from_ps4(bin_file: Path, white_file: Path, ctx: interactions.SlashContext):
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nDownloading the new resigned save {white_file.name} from PS4...',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDownloading the new resigned save {white_file.name} from PS4...')
    await loop.run_in_executor(None,ftpdownload,ftp,f'sdimg_{psd}',save_folder_ftp,white_file)
    await loop.run_in_executor(None,ftpdownload,ftp,f'{psd}.bin',save_folder_ftp,bin_file)
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nDONE DOWNLOADING {white_file.name} from PS4',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDONE DOWNLOADING {white_file.name} from PS4')


async def download_enc_save(file: Tuple[Path,str],file2: Tuple[Path,str], output_folder: Path,ctx: interactions.SlashContext):
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nDownloading the save_files, {file2[0]}') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDownloading the save_files, {file2[0]}')
    await loop.run_in_executor(None,download_google_drive_file,file2[1],Path(output_folder,file2[0].name))
    await loop.run_in_executor(None,download_google_drive_file,file[1],Path(output_folder,file[0].name))
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nDONE DOWNLOADING the save_files, {file2[0]}',) if istl() else await ctx.channel.send(content = f'{SUCCESS_MSG}\n\nDONE DOWNLOADING the save_files, {file2[1]}')

async def do_resign_one_save(bin_file: Path, white_file: Path,accountid: AccountID,ctx: interactions.SlashContext):
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...')
    await upload_save_to_ps4(bin_file,white_file,ctx)

    async with MountSave(ps4,mem,uid,psti,psd) as mp:
        if not mp:
            return mp
        await ctx.edit(content = f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}')
        try:
            param_sfo = BytesIO()
            ftp.retrbinary("RETR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo.write)
            resign_param_sfo(param_sfo,accountid)
            ftp.storbinary("STOR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo)
        except:
            pass
    await download_save_from_ps4(bin_file,white_file,ctx)
    return True

async def do_re_region_cheat(ftp: FTP, _,mounted_save_dir: str,/,*,gameid: str):
    param_sfo = BytesIO()
    ftp.retrbinary(f"RETR {mounted_save_dir}/sce_sys/param.sfo",param_sfo.write)
    
    param_sfo.seek(0x61C)
    param_sfo.write(gameid.encode('utf-8'))
    param_sfo.seek(0)

    param_sfo.seek(0x62C)
    param_sfo.write(gameid.encode('utf-8'))
    param_sfo.seek(0)

    param_sfo.seek(0xA9C)
    param_sfo.write(gameid.encode('utf-8'))
    param_sfo.seek(0)
    
    ftp.storbinary(f"STOR {mounted_save_dir}/sce_sys/param.sfo",param_sfo)

    
async def do_resign_one_save_plus_cheat(bin_file: Path, white_file: Path,accountid: AccountID,ctx: interactions.SlashContext, cheat_function: callable, **cheat_args):
    await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading {white_file.name} to PS4...')
    await upload_save_to_ps4(bin_file,white_file,ctx)

    async with MountSave(ps4,mem,uid,psti,psd) as mp:
        if not mp:
            return mp
        await ctx.edit(content = f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}')
        try:
            param_sfo = BytesIO()
            ftp.retrbinary("RETR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo.write)
            resign_param_sfo(param_sfo,accountid)
            ftp.storbinary("STOR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo)
        except:
            pass
        ftp.cwd('/')
        await ctx.edit(content = f'{SUCCESS_MSG}\n\nApplying cheats too {white_file.name}',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nApplying cheats too {white_file.name}')
        try:
            await cheat_function(ftp,loop,'/mnt/sandbox/NPXS20001_000/savedata0',**cheat_args)
        except:
            ftp.cwd('/')
            return format_exc()
        ftp.cwd('/')

    await download_save_from_ps4(bin_file,white_file,ctx)
    return True


def silentfolder(thesussydir): #deletes a folder, if it doesnt find the folder then it does nothing (no throwing error!)
    if os.path.exists(thesussydir) and os.path.isdir(thesussydir):   
        rmtree(thesussydir)

def silentremove(filetobedeleted): #not by me this function
    try:
        os.remove(filetobedeleted)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occurred

def clean_workspace():
    silentfolder(Path('workspace','resigned_saves'))
    silentfolder(Path('workspace','save_to_be_decrypted'))
    silentfolder(Path('workspace','decrypted_saves'))
    silentremove(Path('workspace','temp.zip'))
    silentremove(Path('workspace','temp2.zip'))
    silentfolder(Path('workspace','dump_the_dec_save'))
    silentfolder(Path('workspace','new_encrypted_save'))
    silentfolder(Path('workspace','save_to_apply_cheats'))


def isgoodzip(file: Path) -> bool:
    try: zp = zipfile.ZipFile(file)
    except zipfile.BadZipFile: return False
    a = zp.filelist
    size = sum([zinfo.file_size for zinfo in a])
    if size > FILE_SIZE_TOTAL_LIMIT: return False 
    if len(a) > ZIP_LOOSE_FILES_MAX_AMT: return False
    return True

def compress(files_location: Path,outputfile: Path = Path('Example.zip')):
    # create the zip file first parameter path/name, second mode
    zf = zipfile.ZipFile(outputfile, mode="w")

    for filename in files_location.rglob('*'):
        zf.write(filename,Path(*filename.parts[1:]),zipfile.ZIP_DEFLATED)

def uncompress(filepath,targetdir='mods'):
    with zipfile.ZipFile(filepath,"r") as zip_ref:
        zip_ref.extractall(targetdir)

def extract_drive_folder_id(link: str,/) -> str:
    return link.split('folders/')[-1].split('?')[0]

def extract_drive_id(link):
    # Regular expression pattern to match Google Drive IDs
    pattern = r"(?:https?:\/\/)?(?:www\.)?(?:drive\.google\.com)\/file\/d\/([a-zA-Z0-9_-]+)"
    
    # Search for the pattern in the link
    match = re.search(pattern, link)
    
    if match:
        return match.group(1)  # Return the matched Google Drive ID
    else:
        return ''  # Return empty string

def download_google_drive_file(google_drive_id: str,zip_path: Path):
    with open(zip_path,'wb') as f:
        downloader = MediaIoBaseDownload(f, drive_service.files().get_media(fileId=google_drive_id))
        done = False
        progresss = 0
        while done is False:
            progresss += 1
            status, done = downloader.next_chunk()
            if status is None:
                pass#await ctx.edit(content = f'{SUCCESS_MSG}\n\n progress download {progresss}')
            else:
                pass#await ctx.edit(content = f'{SUCCESS_MSG}\n\n progress download {progresss}')


def resign_saves_option_req(func):
    return interactions.slash_option(
    name="account_id",
    description="The account id to resign with, should be in format 16 hex characters, put 0 to use your account id",
    required=True,
    opt_type=interactions.OptionType.STRING
    )(func)


def cheats_base_save_files(func):
    return interactions.slash_option(
    name="save_files",
    description=f"google drive folder link containing the save files to apply the cheats too, max {MAX_RESIGNS_PER_ONCE} saves per command",
    required=True,
    opt_type=interactions.OptionType.STRING
    )(func)


@interactions.slash_command(name="ping",description=f"Test if the bot is responding")
async def ping_test(ctx: interactions.SlashContext):
    global is_bot_in_use
    if is_bot_in_use:
        await ctx.send(BOT_IN_USE_MSG,ephemeral=False)
        return
    await ps4.notify(f'{ctx.author_id} pinged the bot!')
    global bot
    await ctx.send(f'<@{ctx.author_id}> Pong! bot latency is {bot.latency * 1000:.2f}ms',ephemeral=False)


@interactions.slash_command(name="my_account_id",description="Get your Account ID from your psn name")
@interactions.slash_option(
    name="psn_name",
    description='your psn name',
    required=True,
    opt_type=interactions.OptionType.STRING
    )
async def my_account_id(ctx: interactions.SlashContext,psn_name: str):
    await ctx.defer(ephemeral=False)
    try:
        user = psnawp.user(online_id=psn_name)
    except PSNAWPNotFound as e:
        await ctx.send(f'Invalid psn name {psn_name}',ephemeral=False)
        return
    account_id_hex = hex(int(user.account_id)).replace('0x','').rjust(16,'0')
    add_user_account_id(ctx.author_id,account_id_hex)
    
    last_msg = await ctx.send('s',ephemeral = False)
    
    await ctx.send(f'<@{ctx.author_id}>  your account id for {psn_name} is {account_id_hex}, saved to database',ephemeral=False)
    await ctx.delete(last_msg)
    
@interactions.slash_command(name="resign",description=f"Resign a save file to an account id (max {MAX_RESIGNS_PER_ONCE} saves per command)")
@interactions.slash_option(
    name="save_files",
    description='a google drive folder link which contain your saves',
    required=True,
    opt_type=interactions.OptionType.STRING
    )
@resign_saves_option_req
async def resign_discord_command(ctx: interactions.SlashContext, save_files: str, account_id: str):
    global is_bot_in_use
    if is_bot_in_use:
        await ctx.send(BOT_IN_USE_MSG,ephemeral=False)
        return
    await ctx.defer()
    sgt()
    discord_file_name: str = datetime.now().strftime("%d_%m_%Y__%H_%M_%S")

    if account_id == '0':
        try:
            account_id = get_user_account_id(ctx.author_id)
        except KeyError:
            await ctx.send('You dont have any account id saved to the database!, try running the `/my_account_id` again',ephemeral=False) if istl() else await ctx.channel.send('You dont have any account id saved to the database!, try running the `/my_account_id` again')
            return
        
    try:
        leh_account_id = AccountID(account_id)
    except ValueError:
        await ctx.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command',ephemeral=False) if istl() else await ctx.channel.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command')
        return    

    google_drive_link_id = extract_drive_folder_id(save_files)
    
    try:
        folder_name = drive_service.files().get(fileId=google_drive_link_id, fields="name").execute().get('name')
        your_files = await loop.run_in_executor(None,list_files_in_folder,google_drive_link_id,folder_name)
    except:
        await ctx.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files),ephemeral=False) if istl() else await ctx.channel.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files))
        return
    
    valid_saves = [x for x in get_valid_saves_out_names_only(your_files)]



    if not valid_saves:
        await ctx.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder',ephemeral=False) if istl() else await ctx.channel.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder')
        return
    
    if len(valid_saves) > MAX_RESIGNS_PER_ONCE:
        await ctx.send(f'theres too many saves to resign, we can only do {MAX_RESIGNS_PER_ONCE} per resign command',ephemeral=False) if istl() else await ctx.channel.send(f'theres too many saves to resign, we can only do {MAX_RESIGNS_PER_ONCE} per resign command')
        return
    
    for file,file2 in valid_saves:
        file_metadata = drive_service.files().get(fileId=file[1],fields = 'size,name').execute()
        file_metadata2 = drive_service.files().get(fileId=file2[1],fields = 'size,name').execute()

        if int(file_metadata['size']) != 96:
            await ctx.send(f'Invalid save bin file {file_metadata["name"]}',ephemeral=False) if istl() else await ctx.channel.send(f'Invalid save bin file {file_metadata["name"]}')
            return
        
        if int(file_metadata2['size']) > FILE_SIZE_TOTAL_LIMIT:
            await ctx.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?',ephemeral=False) if istl() else await ctx.channel.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?')
            return
    
    await ctx.send(SUCCESS_MSG,ephemeral=False) if istl() else await ctx.channel.send(SUCCESS_MSG)
    
    clean_workspace()
    # lets go!
    is_bot_in_use = True
    try:
        for index, (file,file2) in enumerate(valid_saves):
            new_path_for_save = Path('workspace','resigned_saves',f'{make_folder_name_safe(str(file2[0]))}_{index}','PS4','SAVEDATA',f'{leh_account_id!s}',file[0].parts[-2])
            os.makedirs(new_path_for_save, exist_ok=True)
            await download_enc_save(file,file2,new_path_for_save,ctx)
            result = await do_resign_one_save(Path(new_path_for_save,file[0].name),Path(new_path_for_save,file2[0].name),leh_account_id,ctx)

            if not result:
                last_msg = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
                await ctx.send(content= f'<@{ctx.author_id}>. We couldnt mount your save, reason {result.error_code}',ephemeral = False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}>. We couldnt mount your save, reason {result.error_code}')
                await ctx.delete(last_msg) if istl() else None
                return
        new_file_name = Path('workspace','user_saves',f'{discord_file_name}.zip')
        last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nZipping up new resigned saves to {account_id} as {new_file_name.name}') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nZipping up new resigned saves to {account_id} as {new_file_name.name}')
        await loop.run_in_executor(None,compress,Path('workspace','resigned_saves'),new_file_name)
        if new_file_name.stat().st_size > ATTACHMENT_MAX_FILE_SIZE:
            last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading new resigned saves to {account_id} as {new_file_name.name} to gdrive') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading new resigned saves to {account_id} as {new_file_name.name} to gdrive')
            new_url = await loop.run_in_executor(None,google_drive_upload_file,new_file_name,folder_id,drive_service)
            new_url = new_url[1]
            os.remove(new_file_name)
            last_msg2 = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your resigned saves : {new_url}',ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your resigned save: {new_url}')
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
        else:
            olddir = os.getcwd()
            os.chdir(new_file_name.parent)
            last_msg2 = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your resigned saves : ',file=new_file_name.name,ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your resigned save: ',file=new_file_name.name)
            os.chdir(olddir)
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
            os.remove(new_file_name)
    finally:
        is_bot_in_use = False


async def _do_dec(ctx: interactions.SlashContext,save_files: str, extra_decrypt: callable):
    global is_bot_in_use
    if is_bot_in_use:
        await ctx.send(BOT_IN_USE_MSG,ephemeral=False)
        return
    await ctx.defer()
    sgt()
    discord_file_name: str = datetime.now().strftime("%d_%m_%Y__%H_%M_%S")

    google_drive_link_id = extract_drive_folder_id(save_files)
    
    try:
        folder_name = drive_service.files().get(fileId=google_drive_link_id, fields="name").execute().get('name')
        your_files = await loop.run_in_executor(None,list_files_in_folder,google_drive_link_id,folder_name)
    except:
        await ctx.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files),ephemeral=False) if istl() else await ctx.channel.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files))
        return
    
    valid_saves = [x for x in get_valid_saves_out_names_only(your_files)]

    if not valid_saves:
        await ctx.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder',ephemeral=False) if istl() else await ctx.channel.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder')
        return
    
    if len(valid_saves) > MAX_RESIGNS_PER_ONCE:
        await ctx.send(f'theres too many saves to decrypt, we can only do {MAX_RESIGNS_PER_ONCE} per decrypt command',ephemeral=False) if istl() else await ctx.channel.send(f'theres too many saves to decrypt, we can only do {MAX_RESIGNS_PER_ONCE} per decrypt command')
        return
    
    for file,file2 in valid_saves:
        file_metadata = drive_service.files().get(fileId=file[1],fields = 'size,name').execute()
        file_metadata2 = drive_service.files().get(fileId=file2[1],fields = 'size,name').execute()

        if int(file_metadata['size']) != 96:
            await ctx.send(f'Invalid save bin file {file_metadata["name"]}',ephemeral=False) if istl() else await ctx.channel.send(f'Invalid save bin file {file_metadata["name"]}')
            return
        
        if int(file_metadata2['size']) > FILE_SIZE_TOTAL_LIMIT:
            await ctx.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?',ephemeral=False) if istl() else await ctx.channel.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?')
            return
    
    await ctx.send(SUCCESS_MSG,ephemeral=False) if istl() else await ctx.channel.send(SUCCESS_MSG)
    
    

    clean_workspace()
    # lets go!
    is_bot_in_use = True
    try:
        for index, (file,file2) in enumerate(valid_saves):
            os.makedirs(Path('workspace','decrypted_saves',f'{make_folder_name_safe(str(file2[0]))}_{index}','savedata0'),exist_ok=True)
            new_path_for_save = Path('workspace','save_to_be_decrypted',f'{make_folder_name_safe(str(file2[0]))}_{index}')
            os.makedirs(new_path_for_save, exist_ok=True)
            await download_enc_save(file,file2,new_path_for_save,ctx)
            result = True
            await upload_save_to_ps4(Path(new_path_for_save,file[0].name),Path(new_path_for_save,file2[0].name),ctx)
            async with MountSave(ps4,mem,uid,psti,psd) as mp:
                if not mp:
                    result = mp
                    break
                await ctx.edit(content = f'{SUCCESS_MSG}\n\nDownloading decrpyted save from PS4...') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDownloading decrpyted save from PS4...')
                try:
                    await loop.run_in_executor(None,extra_decrypt,ftp,'/mnt/sandbox/NPXS20001_000/savedata0',Path('workspace','decrypted_saves',f'{make_folder_name_safe(str(file2[0]))}_{index}','savedata0'))
                except:
                    last_msg = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
                    await ctx.send(content= f'<@{ctx.author_id}>. We couldnt decrypt your save, reason\n\n {format_exc()}',ephemeral = False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}>. We couldnt decrypt your save, reason\n\n {format_exc()}')
                    await ctx.delete(last_msg) if istl() else None
                    return
        if not result:
            last_msg = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
            await ctx.send(content= f'<@{ctx.author_id}>. We couldnt decrypt your save, reason {result.error_code}',ephemeral = False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}>. We couldnt decrypt your save, reason {result.error_code}')
            await ctx.delete(last_msg) if istl() else None
            return
        new_file_name = Path('workspace','user_saves',f'{discord_file_name}.zip')
        last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nZipping up decrypted save folder savedata0 as {new_file_name.name}...') if istl() else await ctx.channel.send( f'{SUCCESS_MSG}\n\nZipping up decrypted save folder savedata0 as {new_file_name.name}...')
        await loop.run_in_executor(None,compress,Path('workspace','decrypted_saves'),new_file_name)
        if new_file_name.stat().st_size > ATTACHMENT_MAX_FILE_SIZE:
            last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading {new_file_name.name} to gdrive...') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading {new_file_name.name} to gdrive...')
            new_url = await loop.run_in_executor(None,google_drive_upload_file,new_file_name,folder_id,drive_service)
            new_url = new_url[1]
            os.remove(new_file_name)
            last_msg2 = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your decrypted save: {new_url}',ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your decrypted save: {new_url}')
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
        else:
            olddir = os.getcwd()
            os.chdir(new_file_name.parent)
            last_msg2 = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your decrypted save: ',file=new_file_name.name,ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your decrypted save: ',file=new_file_name.name)
            os.chdir(olddir)
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
            os.remove(new_file_name)
    finally:
        is_bot_in_use = False



def dec_enc_save_files(func):
    return interactions.slash_option(
    name="save_files",
    description="a google drive folder link containing your encrypted saves to be decrpyted",
    required=True,
    opt_type=interactions.OptionType.STRING
    )(func)


def sw_single_file_dec(func):
    return interactions.slash_option(
    name="sw_single_file_dec",
    description="The file you wanna import, NOT A ZIP, YOU SHOULD GET THIS FROM SAVEWIZARD OR advanced_mode_export",
    required=True,
    opt_type=interactions.OptionType.ATTACHMENT
    )(func)

@interactions.slash_command(name="decrypt",description=f"Decrypt your save files! (max {MAX_RESIGNS_PER_ONCE} save per command)")
@dec_enc_save_files
async def do_dec(ctx: interactions.SlashContext,save_files: str,):
    await _do_dec(ctx,save_files,download_ftp_folder)

advanced_mode_export = interactions.SlashCommand(name="advanced_mode_export", description="Commands to do any extra decryptions or file management for certain saves")
##########################################
red_dead_redemption_2_export = advanced_mode_export.group(name="red_dead_redemption_2", description="Export decrypted saves from encrypted Red Dead Redemption 2 saves")

@red_dead_redemption_2_export.subcommand(sub_cmd_name="export", sub_cmd_description="Export decrypted saves from encrypted Red Dead Redemption 2 saves")
@dec_enc_save_files
async def rdr2_export(ctx: interactions.SlashContext,save_files: str,):
    await _do_dec(ctx,save_files,red_dead_redemption_2.decrypt_save)
##########################################

advanced_mode_import = interactions.SlashCommand(name="advanced_mode_import", description="Commands to import singular files, usually from savewizard")
##########################################
any_game_export = advanced_mode_export.group(name="any_game", description="Export decrypted save from any game, if it doesnt work, please ask to add your game")
def any_game_decrypt_save(ftp: FTP, mounted_save_dir: str,download_loc: Path,/):
    my_save_dir, = {x[0] for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir) if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]}

    with open(Path(download_loc,my_save_dir.split('/')[-1]),'wb') as f:
        ftp.retrbinary(f'RETR {my_save_dir}',f.write)

@any_game_export.subcommand(sub_cmd_name="export", sub_cmd_description="Export decrypted save from any game, if it doesnt work, please ask to add your game")
@dec_enc_save_files
async def any_game_export_func(ctx: interactions.SlashContext,save_files: str,):
    await _do_dec(ctx,save_files,any_game_decrypt_save)

any_game_import = advanced_mode_import.group(name="any_game", description="Import dec saves for any game, maybe from SW advanced mode export, if dont work ask to add your game")
async def any_game_encrypt_save(ftp: FTP, loop, mounted_save_dir: str,/,*,sw_single_file_dec: Path):
    my_save_dir, = {x[0] for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir) if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]}

    with open(sw_single_file_dec,'rb') as f:
        await loop.run_in_executor(None,ftp.storbinary,f'STOR {my_save_dir}',f)

@any_game_import.subcommand(sub_cmd_name="import", sub_cmd_description="Import dec saves for any game, maybe from SW advanced mode export, if dont work ask to add your game")
@cheats_base_save_files
@resign_saves_option_req
@sw_single_file_dec
async def any_game_import_func(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    await _do_the_cheats(ctx,save_files,account_id,any_game_encrypt_save,**cheats_args)
##########################################
red_dead_redemption_2_import = advanced_mode_import.group(name="red_dead_redemption_2", description="Import decrypted saves for Red Dead Redemption 2, maybe from savewizard advanced mode export")

@red_dead_redemption_2_import.subcommand(sub_cmd_name="import", sub_cmd_description="Import decrypted saves for Red Dead Redemption 2, maybe from savewizard advanced mode export")
@cheats_base_save_files
@resign_saves_option_req
@sw_single_file_dec
async def rdr2_import(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    await _do_the_cheats(ctx,save_files,account_id,red_dead_redemption_2.encrypt_save,**cheats_args)
##########################################


@interactions.slash_command(name="encrypt",description=f"Encrypt your save files! (max 1 save per command), only jb ps4 decrypted saves!")
@interactions.slash_option(
    name="decrypted_save_file",
    description="a google drive folder link containing the savedata0 decrypted save folder",
    required=True,
    opt_type=interactions.OptionType.STRING
)
@interactions.slash_option(
    name="encrypted_save_file",
    description="a google drive folder link containing an encrypted save file of the same save type, as a container",
    required=True,
    opt_type=interactions.OptionType.STRING
)
@resign_saves_option_req
@interactions.slash_option(
    name="clean_encrypted_file",
    description="If True, deletes all in encrypted file; only use when decrypted folder has all files. Default: False",
    required=False,
    opt_type=interactions.OptionType.BOOLEAN
)
async def do_enc(ctx: interactions.SlashContext,decrypted_save_file: str ,encrypted_save_file: str ,account_id: str, clean_encrypted_file: bool = False):
    global is_bot_in_use
    if is_bot_in_use:
        await ctx.send(BOT_IN_USE_MSG,ephemeral=False)
        return
    await ctx.defer()
    sgt()
    discord_file_name: str = datetime.now().strftime("%d_%m_%Y__%H_%M_%S")

    if account_id == '0':
        try:
            account_id = get_user_account_id(ctx.author_id)
        except KeyError:
            await ctx.send('You dont have any account id saved to the database!, try running the `/my_account_id` again',ephemeral=False) if istl() else await ctx.channel.send('You dont have any account id saved to the database!, try running the `/my_account_id` again')
            return

    try:
        leh_account_id = AccountID(account_id)
    except ValueError:
        await ctx.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command',ephemeral=False) if istl() else await ctx.channel.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command')
        return    

    enc_google_drive_link_id = extract_drive_folder_id(encrypted_save_file)
    
    try:
        folder_name = drive_service.files().get(fileId=enc_google_drive_link_id, fields="name").execute().get('name')
        your_files = await loop.run_in_executor(None,list_files_in_folder,enc_google_drive_link_id,folder_name)
    except:
        await ctx.send(INVALID_GDRIVE_URl_TEMPLATE.format(encrypted_save_file),ephemeral=False) if istl() else await ctx.channel.send(INVALID_GDRIVE_URl_TEMPLATE.format(encrypted_save_file))
        return
    
    valid_saves = [x for x in get_valid_saves_out_names_only(your_files)]

    if not valid_saves:
        await ctx.send(f'the folder {enc_google_drive_link_id}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder',ephemeral=False) if istl() else await ctx.channel.send(f'the folder {enc_google_drive_link_id}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder')
        return
    
    if len(valid_saves) > 1:
        await ctx.send(f'theres too many saves to encrypt, we can only do {1} per encrypt command',ephemeral=False) if istl else await ctx.channel.send(f'theres too many saves to encrypt, we can only do {1} per encrypt command')
        return

    dec_google_drive_link_id = extract_drive_folder_id(decrypted_save_file)

    try:        
        folder_name = drive_service.files().get(fileId=dec_google_drive_link_id, fields="name").execute().get('name')
        your_files_dec = await loop.run_in_executor(None,list_files_in_folder,dec_google_drive_link_id,folder_name)
    except:
        await ctx.send(INVALID_GDRIVE_URl_TEMPLATE.format(dec_google_drive_link_id),ephemeral=False) if istl() else await ctx.channel.send(INVALID_GDRIVE_URl_TEMPLATE.format(dec_google_drive_link_id))
        return
    


    temp_your_files_dec: list[tuple[Path,str]] = []
    seen_folder_ids = set()
    for savedata0_folder in your_files_dec:
        if (savedata0_folder[0].name == 'savedata0' or (savedata0_folder[0].parent == Path('savedata0')) or savedata0_folder[0].parent == Path('/savedata0')) and savedata0_folder[1] not in seen_folder_ids:
            seen_folder_ids.add(savedata0_folder[1]); temp_your_files_dec.append(savedata0_folder)
    your_files_dec = temp_your_files_dec
    

    for savedata0_folder in your_files_dec:
        file_mime_type = drive_service.files().get(fileId=savedata0_folder[1], fields="mimeType").execute().get('mimeType') 
        if not 'application/vnd.google-apps.folder' in file_mime_type:
            your_files_dec.remove(savedata0_folder)

    if not your_files_dec:
        await ctx.send(f'the folder {decrypted_save_file} did not have any decrypted saves in it, did you get them from a ps4? it needs to be in a savedata0 folder!',ephemeral=False) if istl() else await ctx.channel.send(f'the folder {decrypted_save_file} did not have any decrypted saves in it, did you get them from a ps4? it needs to be in a savedata0 folder!')
        return
    
    if len(your_files_dec) > 1:
        await ctx.send(f'Theres too many decrypted saves to encrypt, we can only do {1} per encrypt command',ephemeral=False) if istl() else ctx.channel.send(f'Theres too many decrypted saves to encrypt, we can only do {1} per encrypt command')
        return

    for file,file2 in valid_saves:
        file_metadata = drive_service.files().get(fileId=file[1],fields = 'size,name').execute()
        file_metadata2 = drive_service.files().get(fileId=file2[1],fields = 'size,name').execute()

        if int(file_metadata['size']) != 96:
            await ctx.send(f'Invalid save bin file {file_metadata["name"]}',ephemeral=False) if istl() else await ctx.channel.send(f'Invalid save bin file {file_metadata["name"]}')
            return
        
        if int(file_metadata2['size']) > FILE_SIZE_TOTAL_LIMIT:
            await ctx.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?',ephemeral=False) if istl() else await ctx.channel.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?')
            return
    

    
    await ctx.send(SUCCESS_MSG,ephemeral=False) if istl() else await ctx.channel.send(SUCCESS_MSG)
    
    clean_workspace()
    # lets go!
    is_bot_in_use = True
    try:
        result = True
        for index, (file,file2) in enumerate(valid_saves):

            resultt = await loop.run_in_executor(None,get_folder_size,your_files_dec[index][1],drive_service)

            if resultt > FILE_SIZE_TOTAL_LIMIT:
                last_msg = await ctx.send('s',ephemeral = False)
                await ctx.edit(content = f'<@{ctx.author_id}>. the decrypted saves files {decrypted_save_file} is too big') if istl() else ctx.channel.send(f'<@{ctx.author_id}>. the decrypted saves files {decrypted_save_file} is too big')
                await ctx.delete(last_msg) if istl() else None
                return


            new_path_for_save = Path('workspace','new_encrypted_save',f'{make_folder_name_safe(str(file2[0]))}_{index}','PS4','SAVEDATA',f'{leh_account_id!s}',file[0].parts[-2])
            os.makedirs(new_path_for_save,exist_ok=True)

            white_file = Path(new_path_for_save,file2[0].name)
            bin_file = Path(new_path_for_save,file[0].name)
            await download_enc_save(file,file2,new_path_for_save,ctx)
            await upload_save_to_ps4(bin_file,white_file,ctx)

            await ctx.edit(content = f'{SUCCESS_MSG}\n\nDownloading the decrypted save files from gdrive...') if istl() else ctx.channel.send(content = f'{SUCCESS_MSG}\n\nDownloading the decrypted save files from gdrive...')

            await loop.run_in_executor(None,download_folder,your_files_dec[index][1],Path('workspace','dump_the_dec_save',f'{make_folder_name_safe(str(file2[0]))}_{index}'),drive_service)
            ftp.cwd('/')
            async with MountSave(ps4,mem,uid,psti,psd) as mp:
                if not mp:
                    result = mp
                    break
                if clean_encrypted_file:
                    delete_folder_contents(ftp,'/mnt/sandbox/NPXS20001_000/savedata0')
                await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading the decrypted save files to {white_file.name}') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading the decrypted save files to {white_file.name}')
                await loop.run_in_executor(None,upload_folder_contents,ftp,'/mnt/sandbox/NPXS20001_000/savedata0',Path('workspace','dump_the_dec_save',f'{make_folder_name_safe(str(file2[0]))}_{index}'))
                await ctx.edit(content = f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}',) if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nDoing the resign for {white_file.name}')
                try:
                    param_sfo = BytesIO()
                    ftp.retrbinary("RETR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo.write)
                    resign_param_sfo(param_sfo,leh_account_id)
                    ftp.storbinary("STOR mnt/sandbox/NPXS20001_000/savedata0/sce_sys/param.sfo",param_sfo)
                except:
                    pass
            
            ftp.cwd('/')
            try:
                ftp.cwd('/mnt/sandbox/NPXS20001_000/savedata0')
                ftp.cwd('/')
                unmount_error = await unmount_save(ps4,mem,mp)
                delete_folder_contents(ftp,'/mnt/sandbox/NPXS20001_000/savedata0',dont_delete_sce_sys=False)
                await loop.run_in_executor(None,upload_folder_contents,ftp,'/mnt/sandbox/NPXS20001_000/savedata0',resource_path(Path('savemount_py','backup_dec_save')))
                a = await unmount_save(ps4,mem,mp)
                result = TempThingIdk(unmount_error)
                if a:
                    await ctx.channel.send('WARNING, THE HOST NEEDS TO REBOOT THE BOT')
                    breakpoint()
                
            except Exception:
                pass
            
            if result:
                await download_save_from_ps4(bin_file,white_file,ctx)

        if not result:
            msg = 'mount the encrypted save'
            if isinstance(result,TempThingIdk):
                msg = 'use your decrypted save'
            last_msg = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
            await ctx.send(content= f'<@{ctx.author_id}>. We couldnt {msg}, reason {result.error_code}',) if istl() else await ctx.channel.send(f'<@{ctx.author_id}>. We couldnt mount the encrypted save, reason {result.error_code}')
            await ctx.delete(last_msg) if istl() else None
            return

        new_file_name = Path('workspace','user_saves',f'{discord_file_name}.zip')
        last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nZipping new encrypted save as {new_file_name.name}') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nZipping new encrypted save as {new_file_name.name}')
        await loop.run_in_executor(None,compress,Path('workspace','new_encrypted_save'),new_file_name)
        if new_file_name.stat().st_size > ATTACHMENT_MAX_FILE_SIZE:
            last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading new encrypted save {new_file_name.name} to gdrive') if istl() else await ctx.channel.send(f'{SUCCESS_MSG}\n\nUploading new encrypted save {new_file_name.name} to gdrive')
            
            new_url = await loop.run_in_executor(None,google_drive_upload_file,new_file_name,folder_id,drive_service)
            new_url = new_url[1]
            os.remove(new_file_name)
            last_msg2 = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your encrypted save: {new_url}',ephemeral=False) if istl() else  await ctx.channel.send(f'<@{ctx.author_id}> here is your encrypted save: {new_url}')
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
        else:
            olddir = os.getcwd()
            os.chdir(new_file_name.parent)
            last_msg2 = await ctx.send('s',ephemeral = False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your encrypted save: ',file=new_file_name.name,ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your encrypted save: ',file=new_file_name.name)
            os.chdir(olddir)
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
            os.remove(new_file_name)
    finally:
        is_bot_in_use = False

@interactions.listen()
async def ready():
    await ps4.notify('eZwizard2 connected!')
    print('bot is ready!')


def google_drive_upload_file(file2upload: Path, gfolder_id, leh_drive_service) -> Tuple[str,str]:
    with open(file2upload,'rb') as f:
        media = MediaIoBaseUpload(f,'application/zip',chunksize=DEFAULT_CHUNK_SIZE,resumable=True)
        result = leh_drive_service.files().create(body={'name':file2upload.name,"parents":[gfolder_id]},
                                    media_body = media,
                                    fields = 'id, webContentLink')
        progresss = 0
        response = None
        while response is None:
            progresss += 1
            status, response = result.next_chunk()
            if status is None:  
                pass#await ctx.edit(content= f'{SUCCESS_MSG}\n\nUploading new encrypted save {file2upload.name} to gdrive, {progresss}')
            else:
                pass#await ctx.edit(content= f'{SUCCESS_MSG}\n\nUploading new encrypted save {file2upload.name} to gdrive, {progresss}')
    leh_drive_service.permissions().create(fileId=response.get('id'), body={'type':'anyone','role':'reader'}).execute()
    return response.get('id'),response.get('webContentLink')

def _get_drive_stuff(gfolder_id: str, leh_drive_service: cred_type_hint):
    return leh_drive_service.files().list(q=f"'{gfolder_id}' in parents",
                                        spaces='drive',
                                        supportsAllDrives=True,
                                        includeItemsFromAllDrives=True,
                                        fields='files(mimeType, id, name, size)').execute()['files']


def get_folder_size(folder_id: str,drive_service: cred_type_hint):
    total_size = 0
    results = drive_service.files().list(q=f"'{folder_id}' in parents and trashed=false",
                                         fields="files(id, size)").execute()
    
    if 'files' in results:
        for file in results['files']:
            total_size += int(file.get('size', 0))
    
    return total_size

def download_folder(folder_id, dest_path,drive_service: cred_type_hint):
    results = drive_service.files().list(q=f"'{folder_id}' in parents and trashed=false",
                                         fields="files(id, name, mimeType)").execute()

    if len(results['files']) > ZIP_LOOSE_FILES_MAX_AMT:
        return False

    if not results.get('files', []):
        pass#print('No files found.')
    else:
        for file in results['files']:
            file_name = file['name']
            file_id = file['id']
            file_mime_type = file['mimeType']

            file_path = os.path.join(dest_path, file_name)

            if file_mime_type == 'application/vnd.google-apps.folder':
                os.makedirs(file_path, exist_ok=True)
                download_folder(file_id, file_path,drive_service)
            else:
                request = drive_service.files().get_media(fileId=file_id)
                os.makedirs(Path(file_path).parent,exist_ok=True)
                fh = FileIO(file_path, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    #print(f"Downloading {file_name}: {int(status.progress() * 100)}%")
    return True

def list_ps4_saves(folder_containing_saves: Path,/) -> Generator[Tuple[Path,Path],None,None]:
    for filename in folder_containing_saves.rglob('*'):
        if is_ps4_title_id(filename.parent.name) and filename.suffix == '.bin' and filename.is_file() and Path(filename.with_suffix('').as_posix()).is_file():
            yield filename,Path(filename.with_suffix('').as_posix())

async def _do_the_cheats(ctx: interactions.SlashContext,save_files: str,account_id: str,custom_cheat_function: callable,**cheat_agurments):
    global is_bot_in_use
    if is_bot_in_use:
        await ctx.send(BOT_IN_USE_MSG,ephemeral=False)
        return
    await ctx.defer()
    sgt()
    discord_file_name: str = datetime.now().strftime("%d_%m_%Y__%H_%M_%S")
    
    if account_id == '0':
        try:
            account_id = get_user_account_id(ctx.author_id)
        except KeyError:
            await ctx.send('You dont have any account id saved to the database!, try running the `/my_account_id` again',ephemeral=False) if istl() else await ctx.channel.send('You dont have any account id saved to the database!, try running the `/my_account_id` again')
            return
    
    try:
        leh_account_id = AccountID(account_id)
    except ValueError:
        await ctx.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command',ephemeral=False) if istl() else await ctx.channel.send(f'{account_id} is not a valid account id, it should be the one in your SAVEDATA folder! Or get it from the `/my_account_id` command')
        return    

    google_drive_link_id = extract_drive_folder_id(save_files)
    
    try:
        folder_name = drive_service.files().get(fileId=google_drive_link_id, fields="name").execute().get('name')
        your_files = await loop.run_in_executor(None,list_files_in_folder,google_drive_link_id,folder_name)
    except:
        await ctx.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files),ephemeral=False) if istl() else await ctx.channel.send(INVALID_GDRIVE_URl_TEMPLATE.format(save_files))
        return
    
    valid_saves = [x for x in get_valid_saves_out_names_only(your_files)]

    if not valid_saves:
        await ctx.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder',ephemeral=False) if istl() else await ctx.channel.send(f'the folder {save_files}. did not have any valid save files in it!, make sure to upload the whole CUSAXXXXX folder')
        return
    
    if len(valid_saves) > MAX_RESIGNS_PER_ONCE:
        await ctx.send(f'theres too many saves to apply cheats too we can only do {MAX_RESIGNS_PER_ONCE} per cheat command',ephemeral=False) if istl() else await ctx.channel.send(f'theres too many saves to apply cheats too we can only do {MAX_RESIGNS_PER_ONCE} per cheat command')
        return
    
    for file,file2 in valid_saves:
        file_metadata = drive_service.files().get(fileId=file[1],fields = 'size,name').execute()
        file_metadata2 = drive_service.files().get(fileId=file2[1],fields = 'size,name').execute()

        if int(file_metadata['size']) != 96:
            await ctx.send(f'Invalid save bin file {file_metadata["name"]}',ephemeral=False) if istl() else await ctx.channel.send(f'Invalid save bin file {file_metadata["name"]}')
            return
        
        if int(file_metadata2['size']) > FILE_SIZE_TOTAL_LIMIT:
            await ctx.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?',ephemeral=False) if istl() else await ctx.channel.send(f'{file_metadata2} is too big! {file_metadata2["size"]} bytes, you sure its the right save?')
            return
    
    await ctx.send(SUCCESS_MSG,ephemeral=False) if istl() else await ctx.channel.send(SUCCESS_MSG)
    
    clean_workspace()
    # lets go!
    is_bot_in_use = True
    try:
        for variable_name, variable in cheat_agurments.items():
            if isinstance(variable,interactions.Attachment):
                await ctx.edit(content = f'{SUCCESS_MSG}\n\nDownloading custom cheat file {variable_name}...') if istl() else await ctx.channel.send(content = f'Downloading custom cheat file {variable_name}...')
                await download_file(variable.url,Path('workspace',variable_name))
                cheat_agurments[variable_name] = Path('workspace',variable_name)    
        
        for index, (file,file2) in enumerate(valid_saves):
            try:
                gameid_for_path = cheat_agurments['gameid']
            except KeyError:
                gameid_for_path = file[0].parts[-2]
            new_path_for_save = Path('workspace','save_to_apply_cheats',f'{make_folder_name_safe(str(file2[0]))}_{index}','PS4','SAVEDATA',f'{leh_account_id!s}',gameid_for_path)
            os.makedirs(new_path_for_save, exist_ok=True)
            await download_enc_save(file,file2,new_path_for_save,ctx)            
            result = await do_resign_one_save_plus_cheat(Path(new_path_for_save,file[0].name),Path(new_path_for_save,file2[0].name),leh_account_id,ctx,custom_cheat_function,**cheat_agurments)

            if isinstance(result,str):
                last_msg = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
                await ctx.send(content= f'<@{ctx.author_id}>. We couldnt apply the cheats to your save, reason:\n\n{result}',ephemeral = False) if istl() else await ctx.channel.send(content= f'<@{ctx.author_id}>. We couldnt apply the cheats to your save, reason:\n\n{result}')
                await ctx.delete(last_msg) if istl() else None
                return                

            if not result:
                last_msg = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
                await ctx.send(content= f'<@{ctx.author_id}>. We couldnt mount your save, reason {result.error_code}',ephemeral = False) if istl() else await ctx.channel.send(content= f'<@{ctx.author_id}>. We couldnt mount your save, reason {result.error_code}')
                await ctx.delete(last_msg) if istl() else None
                return

        for _, variable in cheat_agurments.items():
            if isinstance(variable,Path):
                os.remove(variable)

        new_file_name = Path('workspace','user_saves',f'{discord_file_name}.zip')
        last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nZipping up new saves to with cheats and resigned to {account_id} as {new_file_name.name}') if istl() else await ctx.channel.send( f'{SUCCESS_MSG}\n\nZipping up new saves to with cheats and resigned to {account_id} as {new_file_name.name}')
        await loop.run_in_executor(None,compress,Path('workspace','save_to_apply_cheats'),new_file_name)
        if new_file_name.stat().st_size > ATTACHMENT_MAX_FILE_SIZE:
            last_msg = await ctx.edit(content = f'{SUCCESS_MSG}\n\nUploading new saves to with cheats and resigned to {account_id} as {new_file_name.name} to gdrive') if istl() else await ctx.channel.send( f'{SUCCESS_MSG}\n\nUploading new saves to with cheats and resigned to {account_id} as {new_file_name.name} to gdrive')
            new_url = await loop.run_in_executor(None,google_drive_upload_file,new_file_name,folder_id,drive_service)
            new_url = new_url[1]
            os.remove(new_file_name)
            last_msg2 = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here is your save with cheats: {new_url}',ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here is your save with cheats: {new_url}')
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
        else:
            olddir = os.getcwd()
            os.chdir(new_file_name.parent)
            last_msg2 = await ctx.send('s',ephemeral=False) if istl() else await ctx.channel.send('s')
            await ctx.send(f'<@{ctx.author_id}> here your save with cheats: ',file=new_file_name.name,ephemeral=False) if istl() else await ctx.channel.send(f'<@{ctx.author_id}> here your save with cheats: ',file=new_file_name.name)
            os.chdir(olddir)
            await ctx.delete(last_msg) if istl() else None
            await ctx.delete(last_msg2) if istl() else None
            os.remove(new_file_name)
    finally:
        is_bot_in_use = False


cheats_base_command = interactions.SlashCommand(name="cheats", description="Commands for custom cheats for some games")


# lets define the custom cheats now!

@interactions.slash_command(name="re_region",description=f"Change the region of your save! (max {MAX_RESIGNS_PER_ONCE} save per command)")
@cheats_base_save_files
@resign_saves_option_req
@interactions.slash_option(
    name="gameid",
    description="the gameid of the region you want, in format CUSAXXXXX",
    required=True,
    opt_type=interactions.OptionType.STRING
    )
async def re_region(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    cheats_args['gameid'] = cheats_args['gameid'].upper()
    if not is_ps4_title_id(cheats_args['gameid']):
        await ctx.send(f'Invalid gameid {cheats_args["gameid"]}')
        return
    await _do_the_cheats(ctx,save_files,account_id,do_re_region_cheat,**cheats_args)


shantae_curse = cheats_base_command.group(name="shantae_curse", description="Cheats for Shantae and the Pirate's Curse")
@shantae_curse.subcommand(sub_cmd_name="set_gems", sub_cmd_description="Change your gems!")
@cheats_base_save_files
@resign_saves_option_req
@interactions.slash_option(
    name="gems",
    description="the amount of gems you want, normal max is 999 real max is 0xFFFFFFFF",
    required=True,
    opt_type=interactions.OptionType.INTEGER
    )
@interactions.slash_option(
    name="file_number",
    description="the file you want to change the gems on",
    required=True,
    opt_type=interactions.OptionType.INTEGER,
    choices=[
        interactions.SlashCommandChoice(name="File 1", value=1),
        interactions.SlashCommandChoice(name="File 2", value=2),
        interactions.SlashCommandChoice(name="File 3", value=3)
    ]
    )
async def scurse_set_gems(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    await _do_the_cheats(ctx,save_files,account_id,shantae_pirate_curse_cheats.set_gems,**cheats_args)


bo_cold_war = cheats_base_command.group(name="black_ops_cold_war", description="Cheats for Call of Duty: Black Ops Cold War")
@bo_cold_war.subcommand(sub_cmd_name="set_wonder_weapon", sub_cmd_description="Change your weapon!")
@cheats_base_save_files
@resign_saves_option_req
@interactions.slash_option(
    name="weapon_slot",
    description="the weapon slot to add the wonder weapon too",
    required=True,
    opt_type=interactions.OptionType.INTEGER,
    choices=[
        interactions.SlashCommandChoice(name="Weapon slot 1", value=7344),
        interactions.SlashCommandChoice(name="Weapon slot 2", value=7856),
        interactions.SlashCommandChoice(name="Weapon slot 3", value=7600)
    ]
    )
@interactions.slash_option(
    name="wonder_weapon",
    description="The wonder weapon you want",
    required=True,
    opt_type=interactions.OptionType.STRING,
    choices=[
        interactions.SlashCommandChoice(name="Raygun", value='3C01'),
        interactions.SlashCommandChoice(name="D.I.E. Shockwave", value='4A01'),
        interactions.SlashCommandChoice(name="Rai k3", value='4C01'),
        interactions.SlashCommandChoice(name="Axe Chrysalax Savager", value='FB00'),
        interactions.SlashCommandChoice(name="Axe Chrysalax Storm", value='FC00'),
        interactions.SlashCommandChoice(name="CRBR-S", value='F800'),
        interactions.SlashCommandChoice(name="CRBR-S Diffuser", value='F900'),
        interactions.SlashCommandChoice(name="CRBR-S Swarm", value='FA00'),
        interactions.SlashCommandChoice(name="RPG-7", value='2601'),
        interactions.SlashCommandChoice(name="CARV.2 (BO1)", value='3601'),
        interactions.SlashCommandChoice(name="Cymbal Monkey", value='8B00'),
        interactions.SlashCommandChoice(name="EM2", value='9900'),
        interactions.SlashCommandChoice(name="TEC-9", value='9A00'),
        interactions.SlashCommandChoice(name="Marshal", value='9B00'),
        interactions.SlashCommandChoice(name="MG 82", value='9F00'),
        interactions.SlashCommandChoice(name="C58", value='A700'),
    ]
    )
async def cold_war_set_wonder_weapon(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    cheats_args['wonder_weapon'] = bytes.fromhex(cheats_args['wonder_weapon'])
    await _do_the_cheats(ctx,save_files,account_id,black_ops_cold_war.set_wonder_weapon,**cheats_args)

rdr2 = cheats_base_command.group(name="red_dead_redemption_2", description="Cheats for Red Dead Redemption 2")
@rdr2.subcommand(sub_cmd_name="change_money", sub_cmd_description="Change your main money!")
@cheats_base_save_files
@resign_saves_option_req
@interactions.slash_option(
    name = 'money',
    description='the amount of money you want, this includes the decmial point (1000 would be 10.00)',
    required=True,
    opt_type=interactions.OptionType.INTEGER
)
async def change_money(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    await _do_the_cheats(ctx,save_files,account_id,red_dead_redemption_2.set_main_money,**cheats_args)


lbp3_ps4 = cheats_base_command.group(name="littlebigplanet_3", description="Cheats for LittleBigPlanet 3")
@lbp3_ps4.subcommand(sub_cmd_name="install_mods", sub_cmd_description="Install .mod files to a level backup or LBPxSAVE (bigfart)")
@cheats_base_save_files
@resign_saves_option_req
@interactions.slash_option(
    name = 'ignore_plans',
    description='Do you want to ignore .plan files in the mods? default is False',
    required=False,
    opt_type=interactions.OptionType.BOOLEAN
)
@interactions.slash_option(
    name = 'mod_file1',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file2',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file3',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file4',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file5',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file6',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file7',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file8',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file9',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
@interactions.slash_option(
    name = 'mod_file10',
    description='A mod file to install to a level backup or LBPxSAVE (bigfart), from toolkit/workbench',
    required=False,
    opt_type=interactions.OptionType.ATTACHMENT
)
async def lbp3_install_mod(ctx: interactions.SlashContext,save_files: str,account_id: str, **cheats_args):
    await _do_the_cheats(ctx,save_files,account_id,littlebigplanet_3.installmod2l0lbpxsave,**cheats_args)

def resource_path(relative_path) -> Path:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return Path(os.path.join(base_path, relative_path))

async def main(ps4ip: str, user_id: int, placeholder_save_titleid: str, placeholder_save_dir: str):
    global psnawp
    with open('ssocookie.txt') as f: # get your key from https://ca.account.sony.com/api/v1/ssocookie
        psnawp = PSNAWP(f.read())
    
    global is_bot_in_use
    is_bot_in_use = False
    global drive_service
    try:
        drive_service = load_creds()[1]
    except:
        os.remove('token.json')
        drive_service = load_creds()[1]
    global folder_id
    with open('discord_token.txt','r') as f:
        DISCORD_TOKEN = f.read()
    
    response = drive_service.files().list(
        q = "name='ezwizardtwo_saves' and mimeType='application/vnd.google-apps.folder'",
        spaces = 'drive'
    ).execute()

    if not response['files']:
        folder_id = drive_service.files().create(
            body = {
                'name':'ezwizardtwo_saves',
                'mimeType':'application/vnd.google-apps.folder'
            },
            fields = 'id'
        ).execute().get('id')
    else:
        folder_id = response['files'][0]['id']


    
    if not os.path.isdir('workspace'):
        os.makedirs('workspace')
    if not os.path.isdir(Path('workspace','user_saves')):
        os.makedirs(Path('workspace','user_saves'))
    
    
    initialise_database()
    
    global ftp
    ftp = ftp_login_and_connect(ps4ip,2121)
    
    global uid,psti,psd
    uid,psti,psd = user_id,placeholder_save_titleid,placeholder_save_dir


    await PS4Debug.send_ps4debug(ps4ip,port=9090,file_path=resource_path(Path('savemount_py','ps4debug.bin'))); time.sleep(1)
    global ps4
    ps4 = PS4Debug(ps4ip)


    activity = interactions.Activity.create(
        name="with interactions.py",
        type=interactions.ActivityType.PLAYING
    )
    global bot
    bot = interactions.Client(token=DISCORD_TOKEN,
                              #status=interactions.Status.DO_NOT_DISTURB,
                              #activity=activity,
                            )

    # await bot.change_presence(activity=activity,status=interactions.Status.DO_NOT_DISTURB)

    global save_folder_ftp
    save_folder_ftp = f'/user/home/{hex(user_id).replace("0x","")}/savedata/{psti}'
    
    ftp.cwd(save_folder_ftp)
    ftp.retrbinary(f'RETR {psd}.bin' ,BytesIO().write)
    ftp.cwd('/')
    
    global mem
    async with PatchMemoryPS4900(ps4) as mem:
        print('HELLO?')
        
        await bot.astart()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main(*load_config()))
