import argparse
import json
import math
import os
import sys
from datetime import datetime


def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "SWDsupergen",
        description="Generates a parsable SWD file."
    )

    parser.add_argument("SWD",help="The path to the SWD file to generate")
    parser.add_argument("conf",help="the path to the configurations (i.e the presets to store)")
    parser.add_argument("--check",help="checks if the format of the SMD file is correct",action="store_true")
    return parser.parse_args()


class Preset:

    def __init__(self,data,len):
        self.data = data
        self.len = len +1



class KeygroupEntry:

    def __init__(self):
        self.id = None
        self.poly = None
        self.priority = None
        self.vclow = None
        self.vchigh = None
        self.unk50 = None
        self.unk51 = None
    
    def add_general_infos(self,id,poly,priority,vclow,vchigh,unk50,unk51):
        self.id = id 
        self.poly = poly
        self.priority = priority
        self.vclow = vclow
        self.vchigh = vchigh
        self.unk50 = unk50
        self.unk51 = unk51



def parse_bytes(fd,bytes_count):
    """ reads from the file descriptor an amount of bytes
    Arguments:
        fd(BufferedReader): the file descriptor
        bytes_count(int): the amount of bytes to read

    Returns:
        int: the int value read in big endian

    """
    something = fd.read(bytes_count)

def generate_header_chunk(file_descriptor,max_wavi,link_byte):
    first_byte = int(link_byte[:2],base=16)
    second_byte = int(link_byte[2:],base=16)
    file_descriptor.write(b'\x73\x77\x64\x6C') #swdl
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #file length
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(first_byte.to_bytes(1,'little'))
    file_descriptor.write(second_byte.to_bytes(1,'little'))
    # file_descriptor.write(b'\x00') #unknowns
    # file_descriptor.write(b'\x78') #necessary for some reason
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    now = datetime.now()
    file_descriptor.write(now.year.to_bytes(2,'little'))
    file_descriptor.write(now.month.to_bytes(1,'little'))
    file_descriptor.write(now.day.to_bytes(1,'little'))
    file_descriptor.write(now.hour.to_bytes(1,'little'))
    file_descriptor.write(now.minute.to_bytes(1,'little'))
    file_descriptor.write(now.second.to_bytes(1,'little'))
    file_descriptor.write(b'\x00')
    file_descriptor.write(b'\x00\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA')
    file_descriptor.write(b'\x00\xAA\xAA\xAA')
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\xAA\xAA')# the pcmd is in another file
    file_descriptor.write(b'\x00\x00') #zeros
    nb_wavislots = max_wavi +1
    nb_prgislots= 128
    file_descriptor.write(nb_wavislots.to_bytes(2,'little'))
    file_descriptor.write(nb_prgislots.to_bytes(2,'little'))
    file_descriptor.write(b'\x07\x02')#unknown and maybe unstable
    file_descriptor.write(b'\x00\x00\x00\x00')#wavi chunk len
    return 80 #chunk length

def generate_wavi_chunk(file_descriptor,wavi_list,max_wavi):
    file_descriptor.write(b'\x77\x61\x76\x69') #wavi
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')#chunk length
    chk_len = 1# offset of 1 for length
    max_wavi += 1
    padding = ((16 -(2*max_wavi % 16))%16)#?
    print(max_wavi)
    print(padding)
    print('###')
    start_adress = ((2*max_wavi) + padding)
    for i in range(max_wavi):
        if i in wavi_list:
            pointer = start_adress
            file_descriptor.write(int.to_bytes(pointer,2,'little'))
            start_adress += 64
        else:
            file_descriptor.write(b'\x00\x00')

    chk_len += (padding + 2*(max_wavi))
    for _ in range(padding):
        file_descriptor.write(b'\xAA')
    smplpos = 0# sample position in memory (starts at 0)
    chk_len += (64 * len(wavi_list))
    for j in range(len(wavi_list)):
        with open(f"SAMPLES/{wavi_list[j]}.bin","rb") as wavi:
            datas = wavi.read()
        loopbeg = int.from_bytes(datas[40:44],byteorder='little')
        looplen = int.from_bytes(datas[44:48],byteorder='little')
        print(datas[40:44])
        print(datas[44:48])
        incr = ((loopbeg+looplen)*4)# "length" of the sample
        
        file_descriptor.write(datas[:36])
        file_descriptor.write(smplpos.to_bytes(4,'little'))
        file_descriptor.write(datas[40:64])
        smplpos += incr # updated position in memory for the next sample.
    return 15 + chk_len #wavi chunk length (chk_len, with its +1 offset plus 15 bytes written prior, actually 16)

def generate_prgi_chunk(file_descriptor,prgi_list):
    file_descriptor.write(b'\x70\x72\x67\x69') #prgi
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')#chunk length
    chk_len = 1# offset of 1 for length
    prgi_slots = 128
    start_adress = 256
    for i in range(prgi_slots):
        # found = False
        # for j in range(len(prgi_list)):
        #     if i == prgi_list[j].preset_hex:
        #         found = True
        #         to_write = j
        #         break
        #     if i >=j :
        #         break
        if i < len(prgi_list):
            pointer = start_adress
            file_descriptor.write(int.to_bytes(pointer,2,'little'))
            start_adress += prgi_list[i].len
        else:
            file_descriptor.write(b'\x00\x00')
    #No padding since prgi_slots is 128
    chk_len += 256

    for k in range(len(prgi_list)):
        file_descriptor.write(k.to_bytes(1,'little'))
        file_descriptor.write(prgi_list[k].data)
        chk_len += prgi_list[k].len

    return 15 + chk_len #wavi chunk length (chk_len, with its +1 offset plus 15 bytes written prior, actually 16)

def generate_kgrp_chunk(file_descriptor,kgrp_list):
    file_descriptor.write(b'\x6B\x67\x72\x70') #kgrp
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')#chunk length
    chk_len = 0 #no offset added yet, padding necessary
    for i in kgrp_list:
        file_descriptor.write(i.id)# Actually have no idea how this works
        file_descriptor.write(i.poly)# Actually have no idea how this works
        file_descriptor.write(i.priority)# Actually have no idea how this works
        file_descriptor.write(i.vclow)# Actually have no idea how this works
        file_descriptor.write(i.vchigh)# Actually have no idea how this works
        file_descriptor.write(i.unk50)# Actually have no idea how this works
        file_descriptor.write(i.unk51)# Actually have no idea how this works
    chk_len += 8* len(kgrp_list)
    padding = (16 -(chk_len % 16))%16
    for _ in range(padding):
        file_descriptor.write(b'\xFF')# the actual values might be garbage, or not (we don't know?)
    #chk_len += padding
    chk_len += 1 #offset that was not added prior
    return 15 + chk_len,padding#wavi chunk length (chk_len, with its +1 offset plus 15 bytes written prior, actually 16)
def generate_pcmd_chunk():
    print('pcmd chunks are not present in swd files of EoS. This function is therefore unimplemented')
    # From what I understand, sample datas are stored in a main bank (bgm.swd??) 
    # exempting other soundtracks swd files of having a pcmd chunk
    sys.exit(1)

def generate_eod_chunk(file_descriptor):
    file_descriptor.write(b'\x65\x6F\x64\x20') #eod
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')# *actual* chunk length
    return 16
def main():
    args = parse_args()
    if not os.path.exists(args.conf):
        print(f"Configuration file {args.conf} is not found")
        sys.exit(1)

    with open(args.conf,'r') as data:
        configs = json.load(data)
    link_byte = configs['link_byte']
    if len(link_byte) != 4:
        print("config error: link byte is not of length 4")
        sys.exit(1)
    try:
        link_byte = str.encode(link_byte)
        print(link_byte)
    except Exception as e:
        print("hex function failure")
        print(e)
        sys.exit(1)
    preset_list = []
    for preset in configs['presets']:
        preset_name = preset['name']
        preset_list.append(preset_name)
    # for preset in configs['presets']:
    #     preset_value = preset['number']
    #     preset_track = preset['track']
    #     iter = (preset_value,preset_track)
    #     preset_list.append(iter)
    prgi_list = [] 
    wavi_list = []
    for elem in preset_list:
        file_path = f'PRESETS/{elem}.bin'
        # track,value = elem
        # file_path = f'PRESETS/track_{value}_preset_{track}.bin'
        with open(file_path,"rb") as preset:
            preset.read(1)
            datas = preset.read()
            data_len = len(datas)
            iter = Preset(datas,data_len)
            prgi_list.append(iter)
            fetcher = 113
            if data_len < 143:
                print("preset error: for some reason, one preset is under 144 bytes long.")
                sys.exit(1)
            data_len -= 143
            while True:
                sample = int.from_bytes(datas[fetcher:(fetcher+2)],'little')
                wavi_list.append(sample) if sample not in wavi_list else wavi_list
                if data_len == 0:
                    break
                if data_len < 0:
                    print("preset error: for some reason, one preset does not hold a correct format:")
                    print("a sample declaration has a size different of 48 bytes.")
                else:
                    data_len -= 48
                    fetcher += 48
    #     print(iter)

    # for i in wavi_list:
    #     print(i)
    # prgi_list = sorted(prgi_list, key = lambda preset: preset.preset_hex)
    first_kgrp = KeygroupEntry()
    first_kgrp.add_general_infos(id=b'\x00\x00',poly=b'\xFF',priority=b'\x08',vclow=b'\x00',vchigh=b'\xFF',unk50=b'\x00',unk51=b'\x00')
    second_kgrp = KeygroupEntry()
    second_kgrp.add_general_infos(id=b'\x01\x00',poly=b'\x02',priority=b'\x08',vclow=b'\x00',vchigh=b'\x0F',unk50=b'\x00',unk51=b'\x00')
    third_kgrp = KeygroupEntry()
    third_kgrp.add_general_infos(id=b'\x02\x00',poly=b'\x01',priority=b'\x08',vclow=b'\x00',vchigh=b'\x0F',unk50=b'\x00',unk51=b'\x00')
    fourth_kgrp = KeygroupEntry()
    fourth_kgrp.add_general_infos(id=b'\x03\x00',poly=b'\x01',priority=b'\x08',vclow=b'\x00',vchigh=b'\x0F',unk50=b'\x00',unk51=b'\x00')
    fifth_kgrp = KeygroupEntry()
    fifth_kgrp.add_general_infos(id=b'\x04\x00',poly=b'\x01',priority=b'\x08',vclow=b'\x00',vchigh=b'\x0F',unk50=b'\x00',unk51=b'\x00')
    sixth_kgrp = KeygroupEntry()
    sixth_kgrp.add_general_infos(id=b'\x05\x00',poly=b'\xFF',priority=b'\x07',vclow=b'\x00',vchigh=b'\x0F',unk50=b'\x00',unk51=b'\x00')
    seventh_kgrp = KeygroupEntry()
    seventh_kgrp.add_general_infos(id=b'\x06\x00',poly=b'\xFF',priority=b'\x0F',vclow=b'\x00',vchigh=b'\x08',unk50=b'\x00',unk51=b'\x00')
    kgrp_list = []
    kgrp_list.append(first_kgrp)
    kgrp_list.append(second_kgrp)
    kgrp_list.append(third_kgrp)
    kgrp_list.append(fourth_kgrp)
    kgrp_list.append(fifth_kgrp)
    kgrp_list.append(sixth_kgrp)
    kgrp_list.append(seventh_kgrp)

    max_wavi = max(wavi_list)
    wavi_list = sorted(wavi_list)
    print(max_wavi)
    with open(args.SWD,"wb") as file:
        header_chunk_length = generate_header_chunk(file,max_wavi,link_byte)
        wavi_chunk_length = generate_wavi_chunk(file,wavi_list,max_wavi)
        wavi_len_towrite = wavi_chunk_length - 16# The chunk length value to edit in the file
        prgi_chunk_length = generate_prgi_chunk(file,prgi_list)
        prgi_len_towrite = prgi_chunk_length - 16# The chunk length value to edit in the file
        kgrp_chunk_length,padding = generate_kgrp_chunk(file,kgrp_list)
        kgrp_len_towrite = kgrp_chunk_length -16 # The chunk length value to edit in the file
        kgrp_chunk_length = kgrp_chunk_length + padding
        eod_chunk_length = generate_eod_chunk(file)
        file_size = ( header_chunk_length
                        + wavi_chunk_length
                        + prgi_chunk_length
                        + kgrp_chunk_length
                        + eod_chunk_length)
        print(header_chunk_length)
        print(wavi_chunk_length)
        print(prgi_chunk_length)
        print(kgrp_chunk_length)
        print(eod_chunk_length)
    with open(args.SWD,"rb+") as fix_length:
        parse_bytes(fix_length,8)
        fix_length.write(file_size.to_bytes(4,'little'))
        parse_bytes(fix_length,64) #goto wavi chunklen (the first)
        fix_length.write(wavi_len_towrite.to_bytes(4,'little'))
        parse_bytes(fix_length,12) #goto wavi chunklen (the second)
        fix_length.write(wavi_len_towrite.to_bytes(4,'little'))
        parse_bytes(fix_length,wavi_len_towrite)# goto prgi chunk
        parse_bytes(fix_length,12) #goto prgi chunklen
        fix_length.write(prgi_len_towrite.to_bytes(4,'little'))
        parse_bytes(fix_length,prgi_len_towrite)# goto prgi chunk
        parse_bytes(fix_length,12) #goto kgrp chunklen
        fix_length.write(kgrp_len_towrite.to_bytes(4,'little'))

if __name__ == "__main__":
    main()
