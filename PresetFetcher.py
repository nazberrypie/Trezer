import argparse
import os
import sys

from utils import FETCH_SOUNDFONT,FETCH_SOUNDFONT4,parse_bytes,get_padding

def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = 'PresetFetcher',
        description = 'Reads the BGM directory content and fetches the presets and samples used in it.'
    )

    parser.add_argument("BGM",help = "The path to the BGM directory.")
    return parser.parse_args()

def get_header_slots(file_descriptor):
    """ Reads the header chunk in a SWD file and fetches 
    the prgi and wavi amount in said file.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int: The amount of wavi slots in the file
        int: The amount of prgi slots in the file
    """
    magic=file_descriptor.read(4) # magic swdl
    if magic != b'swdl':
        print(f'parse error: The magic number read indicates the file is not of .swd format.\n Found:{magic}')
        sys.exit(1)
    parse_bytes(file_descriptor,66) # unimportant here
    nb_wavi_slots =parse_bytes(file_descriptor,2)
    nb_prgi_slots =parse_bytes(file_descriptor,2)
    parse_bytes(file_descriptor,6) # unimportant as well
    return nb_wavi_slots,nb_prgi_slots

def parse_wavi_chunk(fd,wavi_slots,sample_list):
    """ Reads the wavi chunk in a SWD file and fetches 
    the samples used in said file.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        wavi_slots(int): the amount of samples pointers in the WavTable
        sample_list(set): the list of samples fetched prior
    Returns:
        set: The updated sample list
    """
    magic =fd.read(4) # magic wavi
    if magic != b'wavi':
        print(f'parse error: The wavi chunk starts with a wrong magic number.\n Found:{magic}')
        sys.exit(1)
    parse_bytes(fd,12)# "useless" here
    cpt = 0
    for _ in range(wavi_slots):
        entry = parse_bytes(fd,2)
        if entry != 0:
            cpt += 1
    padding = get_padding(wavi_slots *2,16)
    parse_bytes(fd,padding)
    for _ in range(cpt):
        data = fd.read(64)
        sample_id = int.from_bytes(data[2:4],byteorder='little')
        iter = (sample_id,data)
        sample_list.add(iter)
    return sample_list

def parse_prgi_chunk(fd,prgi_slots,preset_list,file_number):
    """ Reads the prgi chunk in a SWD file and fetches 
    the presets used in said file.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        file_number(int): the number in file (bgmXXXX.swd)
        preset_list(list): the list of presets fetched prior
        
    Returns:
        list: The updated preset list
    """
    magic =fd.read(4)# magic prgi
    if magic != b'prgi':
        print('parse error: The prgi chunk starts with a wrong magic number')
        print(magic)
        sys.exit(1)
    parse_bytes(fd,12)# "useless" here
    entries = []
    cpt = 0
    #programPtrTbl
    for i in range(prgi_slots):
        entry = parse_bytes(fd,2)
        if entry != 0:
            cpt += 1
        entries.append(entry)
    padding = get_padding(prgi_slots *2,16)
    parse_bytes(fd,padding)
    #ProramInfoTbl
    for _ in range(cpt):
        program_id = fd.read(2)
        splits = fd.read(2)
        nb_splits = int.from_bytes(splits,byteorder='little',signed=False)
        prg_volume = fd.read(1)
        prg_pan = fd.read(1)
        unknowns = fd.read(5)
        lfos = fd.read(1)
        nb_lfos = int.from_bytes(lfos,byteorder='little',signed=False)
        pad_byte = fd.read(1)
        something_else = fd.read(3)
        first_part = program_id + splits + prg_volume + prg_pan + unknowns + lfos + pad_byte + something_else
        lfos_values = b''
        splits_values = b''
        for _ in range(nb_lfos):
            lfos_values += fd.read(16)

        padding = fd.read(16)# padding bytes (same as pad_byte apparently)
        for _ in range(nb_splits):
            splits_values += fd.read(48)

        preset = first_part + lfos_values + padding + splits_values
        preset_id = int.from_bytes(program_id,byteorder='little',signed=False)
        key = (file_number,preset_id)
        instr_name = FETCH_SOUNDFONT.get(key)
        if instr_name is None:
            instr_name = FETCH_SOUNDFONT4.get(key)
        if instr_name is not None:
            iter = (instr_name,preset)
            preset_list.append(iter)
    return preset_list

def main():
    args = parse_args()
    if not os.path.exists(args.BGM):
        print(f'Directory {args.BGM} is not found')
        sys.exit(1)
    if not os.path.isdir(args.BGM):
        print(f'{args.BGM} is not a directory')
        sys.exit(1)
    sample_list = set()
    preset_list = []
    # pick_list: bgm file numbers needed for fetching
    pick_list = set()
    for key in FETCH_SOUNDFONT.keys():
        filenum  = key[0]
        if filenum >=0:
            pick_list.add(filenum)
    for key in FETCH_SOUNDFONT4.keys():
        filenum = key[0]
        if filenum >=0:
            pick_list.add(filenum)

    print('Processing...')
    for i in pick_list:
        file_number ='0'
        if i < 100:
            file_number += '0'
        if i < 10:
            file_number += '0'
        file_number += str(i)
        file_name = f'{args.BGM}/bgm{file_number}.swd'
        try:
            with open(file_name, 'rb') as file:
                nb_wavi_slots,nb_prgi_slots = get_header_slots(file)
                sample_list = parse_wavi_chunk(file,nb_wavi_slots,sample_list)
                preset_list = parse_prgi_chunk(file,nb_prgi_slots,preset_list,i)
        except FileNotFoundError:
            print(f'Error: File {file_name} was not found in the directory.')
            print('A clean version of the BGM directory is recommended.')
            sys.exit(1)
    for i in preset_list:
        instr_name,data = i
        file_name = f"PRESETS/{instr_name}.bin"
        with open(file_name,'wb') as output:
            output.write(data)
    for j in sample_list:
        sample_id,data = j
        file_name = f'SAMPLES/{sample_id}.bin'
        with open(file_name,'wb') as output:
            output.write(data)

if __name__ == "__main__":
    main()