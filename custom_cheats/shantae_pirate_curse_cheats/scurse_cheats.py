from ftplib import FTP
from io import BytesIO


from typing import NamedTuple
import struct

from custom_cheats.shantae_pirate_curse_cheats.SCurseDecPS4.SCurseDecPS4 import encode_save, decode_save

class offset_thing(NamedTuple):
    offset: int
    struct_format_str: str
    number_size: int



#ftp.storbinary('STOR ', open(REAL_NAME, 'rb'))

offsets = (
    None,
    offset_thing(0x138C,'<I',4),
    offset_thing(0x2FB4,'<I',4),
    offset_thing(0x4BDC,'<I',4),
)

async def set_gems(ftp: FTP,loop,mounted_save_dir: str, /,*,gems: int, file_number: int):
    if gems < 0:
        gems = 0
    if gems > 999 and gems != 0xFFFFFFFF:
        gems = 999
    
    my_save = BytesIO()
    ftp.cwd(mounted_save_dir)
    
    # theres no need to download the files to disk
    await loop.run_in_executor(None,ftp.retrbinary,'RETR savegame' ,my_save.write)
    
    dec_save = BytesIO(decode_save(my_save.getvalue()))
    
    offset_thing = offsets[file_number]
    
    dec_save.seek(offset_thing.offset)
    dec_save.write(struct.pack(offset_thing.struct_format_str,gems))
    
    new_save = BytesIO(encode_save(dec_save.getvalue()))
    
    await loop.run_in_executor(None,ftp.storbinary,'STOR savegame', new_save)