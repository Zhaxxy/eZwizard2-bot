import asyncio
from ftplib import FTP
import struct
import os
import zipfile
from pathlib import Path
import json

from ps4debug import PS4Debug


ERROR_CODE_LONG_NAMES = {int(key):value for key,value in  json.loads(Path(Path(__file__).parent / 'error_codes.json').read_text()).items()}

try:
    from save_mount_unmount import PatchMemoryPS4900, MountSave, MemoryIsPatched
except ModuleNotFoundError:
    from savemount_py.save_mount_unmount import PatchMemoryPS4900, MountSave, MemoryIsPatched

class AccountID:
    def __init__(self, account_id_str: str) -> None:
        if len(account_id_str) != 16:
            raise ValueError(f'{account_id_str} is not a valid account id')
        self.account_id = bytes.fromhex(account_id_str)

    def __str__(self) -> str:
        return self.account_id.hex().replace('0x','').lower().rjust(16,'0')

    def __repr__(self) -> str:
        return f'{type(self).__name__}({str(self)!r})'

    def to_bytes(self) -> bytes:
        return self.account_id[::-1]

def resign_save(ps4: PS4Debug, mem: MemoryIsPatched,user_id: int,ftp: FTP,save_zip_dir: Path, new_account_id: AccountID):
    raise NotImplementedError

