from ftplib import FTP
from io import BytesIO

async def set_wonder_weapon(ftp: FTP,loop,weapon_slot: int,mounted_save_dir: str ,/,*, wonder_weapon: bytes):
    ftp.cwd(mounted_save_dir)
    
    if not weapon_slot > 3:
        raise AssertionError('possible an old command')
    
    my_save = BytesIO()
    await loop.run_in_executor(None,ftp.retrbinary,'RETR zm_loadouts_offline' ,my_save.write)
    my_save.seek(weapon_slot)
    
    my_save.write(wonder_weapon)
    
    await loop.run_in_executor(None,ftp.storbinary,'STOR zm_loadouts_offline', my_save)
