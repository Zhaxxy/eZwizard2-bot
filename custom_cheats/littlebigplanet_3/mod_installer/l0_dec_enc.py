import xxtea
import struct

LBP_PS4_L0_KEY = b"\xbd\x0c\xb7\x01\xd6\x07\x96\x14\xd5M\xf9\x07\xa0\x8c\xdb\x10"


def _crypt_ps4_l0(L0_bytes: bytes, /, *, has_footer: bool = True, do_crypt: callable, do_padding: bool = False,) -> bytes:
    if (not L0_bytes.endswith(b"FAR4")) and has_footer:
        raise ValueError("Invalid L0 file")
    data = L0_bytes[:-4] if has_footer else L0_bytes

    format_string = "<" + ("I" * (len(data) // 4))
    unformat_string = ">" + ("I" * (len(data) // 4))

    new_data = do_crypt(
        struct.pack(unformat_string, *struct.unpack(format_string, data)),
        key=LBP_PS4_L0_KEY,
        padding=do_padding,
    )

    format_string = "<" + ("I" * (len(new_data) // 4))
    unformat_string = ">" + ("I" * (len(new_data) // 4))

    return (
        struct.pack(unformat_string, *struct.unpack(format_string, new_data)) + b"FAR4"
        if has_footer
        else struct.pack(unformat_string, *struct.unpack(format_string, new_data))
    )


def decrypt_ps4_l0(L0_bytes: bytes, /, *, has_footer: bool = True) -> bytes:
    return _crypt_ps4_l0(L0_bytes, has_footer=has_footer, do_crypt=xxtea.decrypt)


def encrypt_ps4_l0(L0_bytes: bytes, /, *, has_footer: bool = True) -> bytes:
    return _crypt_ps4_l0(L0_bytes, has_footer=has_footer, do_crypt=xxtea.encrypt)


if __name__ == '__main__':
    with open("L0", "rb") as f:
        dec_data = decrypt_PS4_L0(f.read())
    
    with open('L0.farc','wb') as f:
        f.write(dec_data)
