import argparse
from typing import Callable
from pathlib import Path

import struct
from io import BytesIO
import hashlib

from Crypto.Cipher import AES


XENOVERSE_2_PS4_SAVE_HEADER_KEY = b'PR]-<Q9*WxHsV8rcW!JuH7k_ug:T5ApX'
XENOVERSE_2_PS4_SAVE_HEADER_INITIAL_VALUE = b'_Y7]mD1ziyH#Ar=0'
XENOVERSE_2_PS4_SAVE_MAGIC_HEADER = b'H\x89\x01L'
INTERNAL_KEY_OFFSETS = (0x1c,0x4c)

class Xenoverse2Ps4Error(Exception):
    """
    Raise if a bad save
    """

def decrypt_xenoverse2_ps4(enc_save: BytesIO,dec_save_output: BytesIO,*,check_hash: bool = True):
    if enc_save.read(4) != XENOVERSE_2_PS4_SAVE_MAGIC_HEADER:
        raise Xenoverse2Ps4Error('Save does not have correct header, most likley wrong save passed')
    enc_save.seek(0x10)
    og_hash = enc_save.read(0x10)
    
    if check_hash:
        md5_hash = hashlib.md5()
        md5_hash.update(enc_save.read())
        if md5_hash.digest() != og_hash:
            raise Xenoverse2Ps4Error('md5 hash missmatch')
        enc_save.seek(0x20)
    
    
    dec_header = AES.new(XENOVERSE_2_PS4_SAVE_HEADER_KEY,AES.MODE_CTR,initial_value=XENOVERSE_2_PS4_SAVE_HEADER_INITIAL_VALUE,nonce=b'').decrypt(enc_save.read(0x80))
    enc_data_test = enc_save.read(16)
    for key_offset in INTERNAL_KEY_OFFSETS:
        key = dec_header[key_offset:key_offset + 0x20]
        initial_value = dec_header[key_offset + 0x20:key_offset + (0x20 + 0x10)]
        new_key = AES.new(key,AES.MODE_CTR,initial_value=initial_value,nonce=b'')
        test_data = new_key.decrypt(enc_data_test)
        if test_data.startswith(b'#SAV'):
            break
    else: # no break
        raise Xenoverse2Ps4Error('Could not find internal save encryption key')
    
    enc_save.seek(0x20 + 0x80)
    new_key = AES.new(key,AES.MODE_CTR,initial_value=initial_value,nonce=b'')
    decrypted_save = bytearray(new_key.decrypt(enc_save.read()))
    
    decrypted_save[-1] = key_offset
    
    dec_save_output.write(dec_header)
    dec_save_output.write(decrypted_save)
    

def encrypt_xenoverse2_ps4(dec_save: BytesIO, enc_save_output: BytesIO):
    dec_save.seek(-1,2)
    dec_save_file_size_minus_one = dec_save.tell() - 0x80
    
    key_offset = dec_save.read(1)[0] # index 0 as convient way to convert byte to int
    if key_offset not in INTERNAL_KEY_OFFSETS:
        raise Xenoverse2Ps4Error('Could not find my sneaky key offset, did you decrypt this using another tool?')
    dec_save.seek(key_offset)

    key = dec_save.read(0x20)
    initial_value = dec_save.read(0x10)
    new_key = AES.new(key,AES.MODE_CTR,initial_value=initial_value,nonce=b'')
    dec_save.seek(0)
    
    enc_header = AES.new(XENOVERSE_2_PS4_SAVE_HEADER_KEY,AES.MODE_CTR,initial_value=XENOVERSE_2_PS4_SAVE_HEADER_INITIAL_VALUE,nonce=b'').decrypt(dec_save.read(0x80))
    enc_save = new_key.encrypt(dec_save.read(dec_save_file_size_minus_one) + b'\x00')

    
    
    md5_hash = hashlib.md5()
    md5_hash.update(enc_header)
    md5_hash.update(enc_save)


    enc_save_output.write(XENOVERSE_2_PS4_SAVE_MAGIC_HEADER)
    enc_save_output.write(struct.pack('<i',len(enc_save) + len(enc_header) + 0x20))
    enc_save_output.write(struct.pack('<i',len(enc_save) + len(enc_header)))
    enc_save_output.write(b'\x00\x00\x00\x00')
    enc_save_output.write(md5_hash.digest())
    enc_save_output.write(enc_header)
    enc_save_output.write(enc_save)
    



def main(args=None):
    tool_desc: str = 'Tool to encode and decode files'
    input_file_desc: str = 'Input file path to encode/decode'
    output_file_desc: str = 'Output file path of decoded/encoded file'
    encode_desc: str = 'Encode the input_file, otherwise decode it'
    encode_function: Callable[(BytesIO,BytesIO),None] = encrypt_xenoverse2_ps4
    decode_function: Callable[(BytesIO,BytesIO),None] = decrypt_xenoverse2_ps4
    in_memory: bool = True
    
    tool_desc = 'Tool to decrypt and encrypt DRAGON BALL XENOVERSE 2 saves from the PS4 (mounted save)'
    input_file_desc = 'XENOVERSE 2 save (eg SDATA000.DAT) to decrypt/encrypt'
    output_file_desc: str = 'Output file path of encrypted/decrypted save (eg SDATA000.DAT.dec)'
    encode_desc: str = 'Encrypt the save, otherwise decrypt it'
    
    parser = argparse.ArgumentParser(description=tool_desc)
    
    parser.add_argument('input_file',help=input_file_desc)
    parser.add_argument('output_file',help=output_file_desc)
    
    parser.add_argument('-e','--encode',help=encode_desc,action='store_true')
    
    args = parser.parse_args()
    
    do_func = encode_function if args.encode else decode_function
    if in_memory:
        empty_file = BytesIO()
        my_file = BytesIO(Path(args.input_file).read_bytes())
        
        with open(args.output_file,'wb') as f:
            do_func(my_file,empty_file)
            f.write(empty_file.getvalue())
    else:
        raise NotImplementedError('All files fully loaded into memory')


if __name__ == '__main__':
    main()
