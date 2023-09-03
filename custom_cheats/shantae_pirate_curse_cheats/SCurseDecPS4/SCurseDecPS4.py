import struct
import zlib

def uint32(value: int, /):
    return value & 0xFFFFFFFF


def some_hash_function(raw_data: bytes, /):
    """
    thx to https://github.com/algmyr/ alot for helping making this function
    if you can recongise the hash aloghorthim and have a better python implemention let me know!, 
    its likley to be part of jenkins hash functions https://en.wikipedia.org/wiki/Jenkins_hash_function
    """
    byte_length = uint32(len(raw_data))

    golden_ratio1 = uint32(0x9E3779B9)
    uVar4 = uint32(0x9E3779B9)
    uVar6 = uint32(0)
    uVar7 = uint32(byte_length)

    if byte_length >= 12:
        while uVar7 > 11:
            uVar7 -= 12  # 12 byte chunks

            i0 = uint32(struct.unpack("<I", raw_data[:4])[0])
            i1 = uint32(struct.unpack("<I", raw_data[4:8])[0])
            i2 = uint32(struct.unpack("<I", raw_data[8:12])[0])

            raw_data = raw_data[12:]

            uVar6 = uint32(i2 + uVar6)

            uVar4 = uint32(uVar6 >> 13 ^ ((i0 + uVar4) - (i1 + golden_ratio1)) - uVar6)
            golden_ratio1 = uint32(uVar4 << 8 ^ ((i1 + golden_ratio1) - uVar6) - uVar4)
            uVar5 = uint32(golden_ratio1 >> 13 ^ (uVar6 - uVar4) - golden_ratio1)
            uVar4 = uint32(uVar5 >> 12 ^ (uVar4 - golden_ratio1) - uVar5)
            uVar6 = uint32(uVar4 << 16 ^ (golden_ratio1 - uVar5) - uVar4)
            uVar5 = uint32(uVar6 >> 5 ^ (uVar5 - uVar4) - uVar6)
            uVar4 = uint32(uVar5 >> 3 ^ (uVar4 - uVar6) - uVar5)
            golden_ratio1 = uint32(uVar4 << 10 ^ (uVar6 - uVar5) - uVar4)
            uVar6 = uint32(golden_ratio1 >> 15 ^ (uVar5 - uVar4) - golden_ratio1)

        uVar7 = uint32((byte_length - 12) % 12)

    uVar6 = uint32(byte_length + uVar6)

    if uVar7 == 11:
        uVar6 = uint32(raw_data[10] * 0x1000000 + uVar6)
    if uVar7 >= 10:
        uVar6 = uint32(raw_data[9] * 0x10000 + uVar6)
    if uVar7 >= 9:
        uVar6 = uint32(raw_data[8] * 0x100 + uVar6)
    if uVar7 >= 8:
        golden_ratio1 = uint32(golden_ratio1 + raw_data[7] * 0x1000000)
    if uVar7 >= 7:
        golden_ratio1 = uint32(golden_ratio1 + raw_data[6] * 0x10000)
    if uVar7 >= 6:
        golden_ratio1 = uint32(golden_ratio1 + raw_data[5] * 0x100)
    if uVar7 >= 5:
        golden_ratio1 = uint32(golden_ratio1 + raw_data[4])
    if uVar7 >= 4:
        uVar4 = uint32(uVar4 + raw_data[3] * 0x1000000)
    if uVar7 >= 3:
        uVar4 = uint32(uVar4 + raw_data[2] * 0x10000)
    if uVar7 >= 2:
        uVar4 = uint32(uVar4 + raw_data[1] * 0x100)
    if uVar7 >= 1:
        uVar4 = uint32(uVar4 + raw_data[0])

    uVar4 = uint32(uVar6 >> 13 ^ (uVar4 - golden_ratio1) - uVar6)
    golden_ratio1 = uint32(uVar4 << 8 ^ (golden_ratio1 - uVar6) - uVar4)
    uVar6 = uint32((golden_ratio1) >> 13 ^ ((uVar6) - (uVar4)) - (golden_ratio1))
    uVar5 = uint32(uVar6 >> 12 ^ (uVar4 - golden_ratio1) - uVar6)
    golden_ratio1 = uint32(uVar5 << 16 ^ (golden_ratio1 - uVar6) - uVar5)
    uVar4 = uint32(golden_ratio1 >> 5 ^ (uVar6 - uVar5) - golden_ratio1)
    uVar6 = uint32(uVar4 >> 3 ^ (uVar5 - golden_ratio1) - uVar4)
    golden_ratio1 = uint32(uVar6 << 10 ^ (golden_ratio1 - uVar4) - uVar6)

    result = uint32(golden_ratio1 >> 15 ^ (uVar4 - uVar6) - golden_ratio1)
    return result


def check_save(save_bytes: bytes, /):
    SOMEMAGICVALUE = 1224793212
    og_hash = struct.unpack("<I", save_bytes[:4])[0]

    return uint32(some_hash_function(save_bytes[4:]) + SOMEMAGICVALUE) == og_hash


def decode_save(save_bytes: bytes, /, check_the_save: bool = True) -> bytes:
    WBITS = -15
    if (not check_save(save_bytes)) and check_the_save:
        raise ValueError('Hash mismatch')
        
    return zlib.decompress(save_bytes[4:],wbits=WBITS)


def encode_save(decompressed_save_bytes: bytes, /):
    WBITS = -15
    SOMEMAGICVALUE = 1224793212
    
    
    
    if len(decompressed_save_bytes) < 500:
        raise ValueError(f'Does not seem to be a decompressed save {len(decompressed_save_bytes)} bytes is too small')
    
    new_save = zlib.compress(decompressed_save_bytes,wbits=WBITS)
    
    new_hash = struct.pack("<I",uint32(some_hash_function(new_save) + SOMEMAGICVALUE))
    return new_hash + new_save
    
    

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
                    prog='SCurseDecPS4',
                    description='Decompress and compress saves for Shantae and the Pirate\'s Curse, along side generating the correct hash',
                    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d','-decompress',help='Decompress a compressed save, the hash is checked',action='store_true')
    group.add_argument('-c','-compress',help='Compress a decompressed save, the correct hash is also generated',action='store_true')
    


    parser.add_argument('-i', '--input', help='Input save file',required=True)
    parser.add_argument('-o', '--output', help='output save file',required=True)
        
    args = parser.parse_args()
    
    with open(args.input,'rb') as f:
        input_data = f.read()
    
    output_data = decode_save(input_data) if args.d else encode_save(input_data)
    
    with open(args.output,'wb') as f:
        f.write(output_data)
    
    if args.d:
        print(f'Decompressed {args.input} succesfully! Decompressed save is in {args.output}')
    elif args.c:
        print(f'Compressed {args.input} succesfully! Compressed save is in {args.output}')
    
    """
    from io import BytesIO
    gems_offset = 0x138C
    
    with open('savegame','rb') as f:
        save = BytesIO(decode_save(f.read()))
    
    save.seek(gems_offset)
    
    mygems = struct.unpack("<I",save.read(4))[0]
    save.seek(0)
    
    print(mygems)
    
    save.seek(gems_offset)
    
    save.write(struct.pack("<I",786))
    save.seek(0)
    
    with open('savegame.bin','wb') as f:
        f.write(encode_save(save.getvalue()))
    """