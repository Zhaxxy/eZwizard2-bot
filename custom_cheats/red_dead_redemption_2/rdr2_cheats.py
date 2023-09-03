from ftplib import FTP
from io import BytesIO
from struct import pack

from custom_cheats.red_dead_redemption_2.rdr2_dec_enc import auto_encrypt_decrypt

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

async def set_main_money(ftp: FTP, loop, mounted_save_dir: str,/,*, money: int):
    for x in list_all_files_in_folder_ftp(ftp,mounted_save_dir):
        if (not x[0].startswith('/mnt/sandbox/NPXS20001_000/savedata0/sce_sys')) and x[1]:
            my_save_dir = x[0]
    
    my_save = BytesIO()
    
    await loop.run_in_executor(None,ftp.retrbinary,f'RETR {my_save_dir}',my_save.write)

    dec_save = auto_encrypt_decrypt(my_save)

    money_offset = dec_save.index(b'\xCE\x54\x8C\xF5')  + 0x10

    print(hex(money_offset))

    dec_save = BytesIO(dec_save)

    dec_save.seek(money_offset)

    dec_save.write(pack('>I',money))

    dec_save = BytesIO(auto_encrypt_decrypt(dec_save))

    await loop.run_in_executor(None,ftp.storbinary,f'STOR {my_save_dir}',dec_save)