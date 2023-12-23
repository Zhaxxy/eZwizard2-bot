from ftplib import FTP
from io import BytesIO
from pathlib import Path

from custom_cheats.dragon_ball_xenoverse_2.xenoverse2_ps4_decrypt import decrypt_xenoverse2_ps4, encrypt_xenoverse2_ps4

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

def decrypt_save(ftp: FTP, mounted_save_dir: str,download_loc: Path,/):
    # raise NotImplementedError('need to figure out internal save key offset')
    my_save_dir, = {x[0] for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir) if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]}
    
    my_save = BytesIO()
    ftp.retrbinary(f'RETR {my_save_dir}',my_save.write)
    my_save.seek(0)
    decrypted_save = BytesIO()
    
    with open(Path(download_loc,my_save_dir.split('/')[-1]),'wb') as f:
        decrypt_xenoverse2_ps4(my_save,decrypted_save)
        f.write(decrypted_save.getvalue())


async def encrypt_save(ftp: FTP, loop, mounted_save_dir: str,/,*,sw_single_file_dec: Path):
    # raise NotImplementedError('need to figure out internal save key offset')
    my_save_dir, = {x[0] for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir) if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]}
    
    my_save = BytesIO()
    encrypt_xenoverse2_ps4(BytesIO(sw_single_file_dec.read_bytes()),my_save)
    my_save.seek(0)
    await loop.run_in_executor(None,ftp.storbinary,f'STOR {my_save_dir}',my_save)
