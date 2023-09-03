# SCurseDecPS4
Simple command line tool to decompress and recompress savegame for Shantae and the Pirate's Curse on the PS4, along side generating the correct hash

# Usage
```
usage: SCurseDecPS4 [-h] (-d | -c) -i INPUT -o OUTPUT

Decompress and compress saves for Shantae and the Pirate's Curse, along side generating the correct hash

options:
  -h, --help            show this help message and exit
  -d, -decompress       Decompress a compressed save, the hash is checked
  -c, -compress         Compress a decompressed save, the correct hash is also generated
  -i INPUT, --input INPUT
                        Input save file
  -o OUTPUT, --output OUTPUT
                        output save file
```
## example
Dccompress the save
```
python SCurseDecPS4.py -d -i savegame -o output.bin
```
Recompress the save
```
python SCurseDecPS4.py -c -i output.bin -o savegame
```
