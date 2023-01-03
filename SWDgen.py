import argparse
import json
import os
import sys
from datetime import datetime

from utils import get_padding,parse_bytes

def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "SWDgen",
        description="Generates a parsable SWD file."
    )

    parser.add_argument("SWD",help="The name of the SMD file that needs an SWD")
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


def generate_header_chunk(file_descriptor,max_wavi,link_byte):
    """ Writes the header chunk of the SWD file.
        Most of the header is actually static,
        The date of creation being an exception.
        A link byte (at hex 0xE and 0xF) is needed
        to link the SWD file to it's SMD.
        (an SMD and SWD of different link byte will produce no sound)
        Although the link bytes in the SMD can be incorrect (for some reason)
        It is not the case for SWD files.
        To be precise, the link byte of the SWD file must match the bytes used by
        the 0xA9 and 0xAA events in the SMD.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        max_wavi(int): the highest ID among the samples used.
        link_byte(str): the value of the link bytes

    """
    first_byte = int(link_byte[:2],base=16)
    second_byte = int(link_byte[2:],base=16)
    file_descriptor.write(b'\x73\x77\x64\x6C') #swdl
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #file length
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(first_byte.to_bytes(1,'little')) # link_byte
    file_descriptor.write(second_byte.to_bytes(1,'little'))
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
    """ Writes the wavi chunk of the SWD file.
        the chunk is mostly composed of a pointers table
        and a list of samples. The size of the table varies 
        depending on the ID's of the samples used.
        Each sample holds an ID, the size of the table is equals to the
        highest ID among the samples used.
        (A list using only sample 620 will have 620 entries anyway)
        An entry either have:
        -an adress if the entry matches an ID used
        -0x0000 otherwise.

        The list of samples hold the ones used for a song. Samples by definition 
        are "fixed" which allows us to just rip samples datas from original
        SWD files and re-use them here.
        The only exception here is their place in memory (smplpos).
        the first declared sample adress is 0 and the size of the samples can 
        be guessed from their datas. an address value is calculated
        by adding the previous address with the "length" of the previous sample.

        The function declares the address tables, the list of samples with (hopefully)
        the correct offsets for each of them.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        wavi_list(list): the list of samples to declare
        max_wavi(int): the highest ID among the samples used.

    """
    file_descriptor.write(b'\x77\x61\x76\x69') #wavi
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')#chunk length
    chk_len = 1# offset of 1 for length
    max_wavi += 1
    padding = get_padding(2*max_wavi,16)
    start_address = ((2*max_wavi) + padding)
    for i in range(max_wavi):
        if i in wavi_list:
            pointer = start_address
            file_descriptor.write(int.to_bytes(pointer,2,'little'))
            start_address += 64 # all(?) samples declarations are 64 bytes long
        else:
            file_descriptor.write(b'\x00\x00') # sample ID unused

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
        incr = ((loopbeg+looplen)*4)# "length" of the sample
        
        file_descriptor.write(datas[:36])
        file_descriptor.write(smplpos.to_bytes(4,'little'))
        file_descriptor.write(datas[40:64])
        smplpos += incr # updated position in memory for the next sample.
    return 15 + chk_len #wavi chunk length (chk_len, with its +1 offset plus 15 bytes written prior, actually 16)

def generate_prgi_chunk(file_descriptor,prgi_list):
    """ Writes the prgi chunk of the SWD file.
        the chunk is mostly composed of a pointers table
        and a list of presets. The size of the table is fixed here.
        Each presets holds an ID, although the same preset may have different ID's 
        in two different SWD files. Here, an arbitrary choice was made 
        to give ID 0 to n for the used samples. I do not know if an ID have influence over a preset.
        An entry either have:
        -an adress if the entry matches an ID used
        -0x0000 otherwise.

        The list of preset holds the ones used for a song. Presets by definition are
        "fixed" which allows us to just rip samples datas from
        original SWD files and reuse them here.
        The only exception here is their ID (the first byte)
        the adresses starts from 256 and the size of the presets can 
        be guessed from their data length. an address value is calculated
        by adding the previous address with the "length" of the previous preset.

        The function declares the adress tables, the list of presets with (hopefully)
        the correct samples for each of them.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        prgi_list(list): the list of presets to declare

    """
    file_descriptor.write(b'\x70\x72\x67\x69') #prgi
    file_descriptor.write(b'\x00\x00') #zeros
    file_descriptor.write(b'\x15\x04')
    file_descriptor.write(b'\x10\x00\x00\x00')
    file_descriptor.write(b'\x00\x00\x00\x00')#chunk length
    chk_len = 1# offset of 1 for length
    prgi_slots = 128 # fixed for PMD soundfont apparently
    start_address = 256 # same
    for i in range(prgi_slots):
        if i < len(prgi_list):# Presets have ID's from 0 to n, for n Presets (no idea if it have influence)
            pointer = start_address
            file_descriptor.write(int.to_bytes(pointer,2,'little'))
            start_address += prgi_list[i].len
        else:
            file_descriptor.write(b'\x00\x00')
    #No padding since prgi_slots is 128 (already aligned with 16)
    chk_len += 256

    for k in range(len(prgi_list)):
        file_descriptor.write(k.to_bytes(1,'little')) # preset ID
        file_descriptor.write(prgi_list[k].data) # preset data
        chk_len += prgi_list[k].len

    return 15 + chk_len #wavi chunk length (chk_len, with its +1 offset plus 15 bytes written prior, actually 16)

def generate_kgrp_chunk(file_descriptor,kgrp_list):
    """ Writes the kgrp chunk of the SMD file.
    Keygroups... Yeah that.

    From what I get, this is what holds "priority" over instruments and notes.
    Presets belong to a keygroup. I guess if two instruments want to use the same channel(?)
    at the same time, one needs priority.
    That's keygroup (I am way out of my league here.)
    This functions naively rips a keygroup found on a SWD file.
    It is therefore static here.
    Do all original SWD files have the same kgrp chunk? No idea.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        kgrp_list(list): the list of keygroups to declare

    """
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
    padding = get_padding(chk_len,16)
    for _ in range(padding):
        file_descriptor.write(b'\xFF')# the actual values varies between files and might be garbage, or not (we don't know?)
    chk_len += 1 #offset that was not added prior
    return 15 + chk_len,padding

def generate_pcmd_chunk():
    print('pcmd chunks are not present in .swd files of EoS. This function is therefore unimplemented')
    # From what I understand, sample datas are stored in a main bank (bgm.swd??) 
    # exempting other soundtracks swd files of having a pcmd chunk
    # This is not true for all files actually, only the ones stored in the BGM repo.
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
    dir_path = f"SMDS/{args.SWD}"
    json_path = dir_path + '/preset_output.json'
    if not os.path.exists(json_path):
        print(f"Configuration file {json_path} is not found")
        sys.exit(1)

    with open(json_path,'r') as data:
        configs = json.load(data)
    link_byte = configs['link_byte']
    if len(link_byte) != 4:
        print("config error: link byte is not of length 4")
        sys.exit(1)
    try:
        link_byte = str.encode(link_byte)
    except Exception as e:
        print("hex function failure")
        print(e)
        sys.exit(1)
    preset_list = []
    for preset in configs['presets']:
        preset_name = preset['name']
        preset_list.append(preset_name)
    prgi_list = [] 
    wavi_list = []
    print('Processing...')
    for elem in preset_list:
        file_path = f'PRESETS/{elem}.bin'
        try:
            with open(file_path,"rb") as preset:
                preset.read(1) # removing preset ID
                datas = preset.read() # reading datas
                data_len = len(datas)
                iter = Preset(datas,data_len)
                prgi_list.append(iter)
                fetcher = 113 # the ID of samples can be found starting from here.
                if data_len < 143: # all preset should be at least 144 (-1 here, we removed the ID)
                    print(f"Preset error: for some reason, preset {elem} is under 144 bytes long.")
                    sys.exit(1)
                data_len -= 143 # After reading the first sample, 143 bytes will be read
                while True:
                    sample = int.from_bytes(datas[fetcher:(fetcher+2)],'little') # reading a sample
                    wavi_list.append(sample) if sample not in wavi_list else wavi_list # adding it to the list if not already in it
                    if data_len == 0: # reached the end of the preset
                        break
                    if data_len < 0: # Samples used by the presets all are 48 bytes long. It should be impossible to reach a negative length here
                        print(f"Preset error: for some reason, preset {elem} does not hold a correct format:")
                        print("a sample declaration has a size different of 48 bytes.")
                        sys.exit(1)
                    else:
                        data_len -= 48 # after reading the sample ID, the next one is 48 bytes afterwards
                        fetcher += 48 # we change the fetcher right on the next sample ID
        except FileNotFoundError:
            print(f'Preset error: The preset {elem} was not found in the PRESETS directory.')
            print('It is very likely that this preset is currently unavailable.')
            print('If you know the preset should exist, try and run PresetFetcher with a clean BGM directory.')
            print('')

    if len(prgi_list) != len(preset_list):
        print('One or multiple presets were not successfully read.')
        print('Terminating.')
        sys.exit(1)

    # ugly static keygroups
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
    # ugly static list of keygroup
    kgrp_list = []
    kgrp_list.append(first_kgrp)
    kgrp_list.append(second_kgrp)
    kgrp_list.append(third_kgrp)
    kgrp_list.append(fourth_kgrp)
    kgrp_list.append(fifth_kgrp)
    kgrp_list.append(sixth_kgrp)
    kgrp_list.append(seventh_kgrp)

    max_wavi = max(wavi_list) # getting highest sample ID
    wavi_list = sorted(wavi_list) # the samples must be declared in ascending order
    swd = dir_path + f'/{args.SWD}.swd'
    with open(swd,"wb") as file:
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
    with open(swd,"rb+") as fix_length:
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

    print(f'file {swd} was generated successfully.')

if __name__ == "__main__":
    main()
