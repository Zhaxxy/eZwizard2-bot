from typing import Annotated,NamedTuple
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from collections import defaultdict
import hashlib
import hmac
import struct

FAR4_SAVE_KEY_LENGTH = 0x84
FAR4_TABLE_ENTRY_LENGTH = 0x1c

LBP_FILE_EXTENSIONS = defaultdict(lambda: '',{b'BPRb':'.bpr',b'PLNb':'.plan',b'GMTb':'.gmat',b'LVLb':'.bin',b'SLTb':'.slt'})

@dataclass(slots=True)
class FAR4TableEntry:
    filename: Path
    sha1: Annotated[bytes,0x14]
    offset: int
    length: int
    
    def __bytes__(self):
        return self.sha1 + struct.pack('>I',self.offset) + struct.pack('>I',self.length)

class FAR4TableOffset(NamedTuple):
    table_offset: int
    file_count: int


def get_sha1(data) -> Annotated[bytes,0x14]:
    m = hashlib.sha1()
    m.update(data)
    return m.digest()


def _get_far4_table_offset(file_archive: BytesIO) -> FAR4TableOffset:
    file_archive.seek(-4,2)
    farc_revision = file_archive.read(4)

    if farc_revision != b'FAR4':
        raise ValueError('Invalid far4 archive passed')
    
    file_archive.seek(0)
    file_archive.seek(-8,2)
    farc_file_count = struct.unpack('>i',file_archive.read(4))[0]
    file_archive.seek(0,2)
    farc_size = file_archive.tell()
    file_archive.seek(0)
    
    return FAR4TableOffset(table_offset = farc_size - FAR4_TABLE_ENTRY_LENGTH - farc_file_count * FAR4_TABLE_ENTRY_LENGTH, file_count = farc_file_count)


class SaveKey():
    __slots__ = ('_save_key_bytes')
    def __repr__(self) -> str:
        return f'{type(self).__name__}.from_string({str(self)!r})'
    
    def __str__(self) -> str:
        return self._save_key_bytes.hex()
    
    def __bytes__(self) -> bytes:
        return bytes(self._save_key_bytes)
    
    @classmethod
    def from_string(cls,save_key_hex_string: str):
        my_instance = cls.__new__(cls)
        new_save_key = bytearray.fromhex(save_key_hex_string)
        
        if not len(new_save_key) == FAR4_SAVE_KEY_LENGTH:
            raise ValueError('Invalid key passed')
        
        my_instance._save_key_bytes = new_save_key
        return my_instance
        
    def __init__(self, file_archive: BytesIO):   
        table_offset = _get_far4_table_offset(file_archive).table_offset
        file_archive.seek(table_offset-FAR4_SAVE_KEY_LENGTH)
        
        self._save_key_bytes = bytearray(file_archive.read(FAR4_SAVE_KEY_LENGTH))
    
    @property
    def root_resource_hash(self) -> Annotated[bytes,0x14]:
        return self._save_key_bytes[0x48: 0x48 + 0x14]
    @root_resource_hash.setter
    def root_resource_hash(self, value: Annotated[bytes,0x14]):
        if not len(value) == 0x14:
            raise ValueError('Invalid sha1 hash passed')
        self._save_key_bytes[0x48: 0x48 + 0x14] = value
    
    
    def swap_endianness(self):
        self._save_key_bytes[0:4] = struct.pack('>i',*struct.unpack('<i',self._save_key_bytes[0:4]))
        self._save_key_bytes[4:4+4] = struct.pack('>i',*struct.unpack('<i',self._save_key_bytes[4:4+4]))
        self._save_key_bytes[0x34:0x34+4] = struct.pack('>i',*struct.unpack('<i',self._save_key_bytes[0x34:0x34+4]))
        self._save_key_bytes[0x38:0x38+4] = struct.pack('>i',*struct.unpack('<i',self._save_key_bytes[0x38:0x38+4]))
    
    @property
    def is_ps4_endian(self) -> bool:
        return bool(self._save_key_bytes[0x38])
    
    def set_to_ps3_endianness(self):
        if self.is_ps4_endian:
            self.swap_endianness()

    def set_to_ps4_endianness(self):
        if not self.is_ps4_endian:
            self.swap_endianness()
    
    @is_ps4_endian.setter
    def is_ps4_endian(self,value: bool):
        if value:
            self.set_to_ps4_endianness()
        else:
            self.set_to_ps3_endianness()

    @property
    def is_lbp3_revision(self) -> bool:
        return self._save_key_bytes[:4] == b'\xF9\x03\x18\x02' or self._save_key_bytes[:4] == b'\x02\x18\x03\xF9'


def extract_far4(file_archive: Path, output_folder: Path) -> SaveKey:
    with open(file_archive,'rb') as f:
        table_offset,file_count = _get_far4_table_offset(f)

        f.seek(table_offset)
        for _ in range(file_count):
            entry_sha1 = f.read(0x14)
            entry_offset = struct.unpack('>i',f.read(4))[0]
            entry_length = struct.unpack('>i',f.read(4))[0]
            next_pointer = f.tell()
            f.seek(entry_offset,0)
            header: str = LBP_FILE_EXTENSIONS[f.read(4)]
            f.seek(-4,1)
            with open(Path(output_folder,entry_sha1.hex() + header),'wb') as output_file:
                output_file.write(f.read(entry_length))
            f.seek(next_pointer)
        return SaveKey(f)


def pack_far4(input_files: Path, output_file_archive: Path, save_key: SaveKey, key_file_resource_hash: Annotated[bytes,0x14]):
    new_hash = hmac.new(b'*\xfd\xa3\xca\x86\x02\x19\xb3\xe6\x8a\xff\xcc\x82\xc7k\x8a\xfe\n\xd8\x13_`G[\xdf]7\xbcW\x1c\xb5\xe7\x96u\xd5(\xa2\xfa\x90\xed\xdf\xa3E\xb4\x1f\xf9\x1f%\xe7BE;+\xb5>\x16\xc9X\x19{\xe7\x18\xc0\x80',b'',hashlib.sha1)
    save_key.root_resource_hash = key_file_resource_hash
    open(output_file_archive,'wb').close()
    
    farc_tables = []


    for file_count, filename in enumerate((x for x in Path(input_files).rglob('*') if x.is_file())):
        with open(filename,'rb') as input_file:
            data = input_file.read()
            data_length = input_file.tell()
            data_sha1 = get_sha1(data)
        table_entry = FAR4TableEntry(filename = filename,sha1 = data_sha1, offset = 0xFFFFFFFF + 2, length = data_length)
        farc_tables.append(table_entry)
    file_count += 1

    with open(output_file_archive,'ab') as f:
        farc_tables.sort(key = lambda e: e.sha1.hex())

        for index, farc_table in enumerate(farc_tables):
            farc_tables[index].offset = f.tell()
            f.write(farc_table.filename.read_bytes()) # yeah i read the file twice, so what?

        if pad_amnt := f.tell() % 4:
            f.write(b'\x00' * (4 - pad_amnt))
        f.write(bytes(save_key))

        for farc_table in farc_tables:
            f.write(bytes(farc_table))

        f.write(b'\x00' * 0x14 + struct.pack('>I',file_count) + b'FAR4')


    with open(output_file_archive,'rb') as f:
        while True:
            data = f.read(4096)
            if not data:
                break
            new_hash.update(data)
    
    with open(output_file_archive,'rb+') as f:
        f.seek(-(0x14 + 4 + 4),2)
        f.write(new_hash.digest())


def main():
    e = extract_far4('bigfart8','d')


if __name__ == '__main__':
    main()
