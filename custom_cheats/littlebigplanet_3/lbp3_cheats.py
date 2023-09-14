from os import remove
from pathlib import Path
from ftplib import FTP
from tempfile import TemporaryFile

from .mod_installer import install_mods_to_bigfart

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

async def installmod2l0lbpxsave(ftp: FTP, loop, mounted_save_dir: str,/,*,ignore_plans = False, **mod_files: Path):
    mods = (value for _, value in mod_files.items())
    
    my_save_dir, = {x[0] for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir) if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]}
    
    if my_save_dir.split('/')[-1].startswith('bigfart'):
        is_l0 = False
    elif my_save_dir.split('/')[-1] == 'L0':
        is_l0 = True
    else:
        raise ValueError(f'Invalid bigfart or level backup file {my_save_dir}')
    
    with open('bbbbbbbbbbbbbbbbbbbbbbigfart','wb') as bigfart:
        await loop.run_in_executor(None,ftp.retrbinary,f'RETR {my_save_dir}',bigfart.write)
    
    def x(): install_mods_to_bigfart(Path('bbbbbbbbbbbbbbbbbbbbbbigfart'),mods,install_plans = not ignore_plans, is_ps4_level_backup = is_l0)
    
    await loop.run_in_executor(None,x)
    
    
    with open('bbbbbbbbbbbbbbbbbbbbbbigfart','rb') as bigfart:
        await loop.run_in_executor(None,ftp.storbinary,f'STOR {my_save_dir}',bigfart)
    remove('bbbbbbbbbbbbbbbbbbbbbbigfart')