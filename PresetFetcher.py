import argparse
import os
import sys


def parse_args():

    parser = argparse.ArgumentParser(
        prog = 'PresetFetcher',
        description = 'Takes the BGM directory and fetches the presets used in it.'
    )

    parser.add_argument("SWD",help = "The path to the BGM directory")
    return parser.parse_args()

def parse_bytes(fd,bytes_count):
    something = fd.read(bytes_count)
    return int.from_bytes(something,byteorder='little',signed=False)

def parse_header(file_descriptor):
    magic =file_descriptor.read(4)# magic swdl
    if magic != b'swdl':
        print('parse error: The magic number read indicates the file is not of .swd format')
        sys.exit(1)
    parse_bytes(file_descriptor,4)# 4 bytes of zeroes
    length = parse_bytes(file_descriptor,4)# file length in bytes
    parse_bytes(file_descriptor,2)# version:(0x1504)
    parse_bytes(file_descriptor,2)# unknowns
    parse_bytes(file_descriptor,8)# 4 bytes of zeroes
    parse_bytes(file_descriptor,2)# last modified (year)
    parse_bytes(file_descriptor,1)# last modified (month)
    parse_bytes(file_descriptor,1)# last modified (day)
    parse_bytes(file_descriptor,1)# last modified (hour)
    parse_bytes(file_descriptor,1)# last modified (minute)
    parse_bytes(file_descriptor,1)# last modified (second)
    parse_bytes(file_descriptor,1)# last modified (centisecond)??
    parse_bytes(file_descriptor,16)# file name (ASCII null-terminated string. Extra space after the 0 on the total 16 bytes is padded with 0xAA)??
    parse_bytes(file_descriptor,4)# (0x00AAAAAA)
    parse_bytes(file_descriptor,4)# 4 bytes of zeroes
    parse_bytes(file_descriptor,4)# 4 bytes of zeroes
    parse_bytes(file_descriptor,4)# 0x10?
    pcmdlen = parse_bytes(file_descriptor,4)
    parse_bytes(file_descriptor,2)# 2 bytes of zeroes??? (four in the docs but incorrect?)
    nb_wavi_slots =parse_bytes(file_descriptor,2)
    nb_prgi_slots =parse_bytes(file_descriptor,2)
    parse_bytes(file_descriptor,2)# unknown
    wavilen = file_descriptor.read(4)#parse_bytes(file_descriptor,4)
    return length,pcmdlen,nb_wavi_slots,nb_prgi_slots,wavilen

def parse_wavi_chunk(fd,wavi_slots,sample_list):
    magic =fd.read(4)# magic wavi
    if magic != b'wavi':
        print('parse error: The wavi chunk starts with a wrong magic number')
        print(magic)
        sys.exit(1)
    parse_bytes(fd,8)# "useless"
    chunklen = parse_bytes(fd,4)# chunk length
    entries = []
    cpt = 0
    for i in range(wavi_slots):
        entry = parse_bytes(fd,2)
        if entry != 0:
            cpt += 1
        entries.append(entry)
    padding = (16 -((wavi_slots * 2) % 16))%16
    parse_bytes(fd,padding)
    for j in range(cpt):
        data = fd.read(64)
        sample_id = int.from_bytes(data[2:4],byteorder='little')
        iter = (sample_id,data)
        sample_list.add(iter)
    return sample_list


PMD_SOUNDFONT = {
    (164,0x4): "Piano", (49,0x3): "Piano Bass", (3,0x1):"Electric Piano", (41,0x3): "Tine E-Piano", (86,0x3):"FM E-Piano", 
    (3,0xE): "Harpsichord 1", (-1,0):"Harpsichord 2", (16,0x61): "Celeste", (3,0x7):"Glockenspiel 1", (6,0x4): "Glockenspiel 2", (12,0xA):"Music Box", (22,0x6): "Vibraphone", (23,0x5):"Marimba", 
    (39,0xC): "Tubular Bells", (50,0xF):"Fantasia 1", (74,0x3): "Fantasia 2", (74,0x1):"Synth Mallet", (81,0x2C): "Percussive Organ", (64,0x8):"Synth Organ", (71,0x3): "Melodica", (136,0x1B):"Finger Bass", 
    (47,0x1C): "Pick Bass", (85,0x8):"J-Bass", (160,0x1D): "Slap Bass", (-1,0):"Bass Harmonics", (5,0x19): "Synth Bass 1", (10,0x1A):"Synth Bass 2", (-1,0): "Synth Bass 3", (3,0x14):"Nylon Guitar", 
    (9,0x17): "Steel Guitar", (84,0xA):"Mandolin", (99,0x16): "Overdriven Guitar", (178,0x16):"Distorted Guitar", (-1,0): "Guitar Harmonics", (23,0x54):"Sitar", (56,0x8): "Banjo",
     (58,0xB):"Harp", 
    (142,0x49): "Cello", (16,0x4A):"Bass Section", (16,0x48): "Violin 1", (-1,0):"Violin 2", (85,0x48): "Violins", (69,0x48):"Viola", (9,0x2E): "Viola Section",
     (10,0x1F):"String Section", 
    (12,0x4B): "Pizzicato Strings", (69,0x20):"Synth Strings 1", (74,0xD): "Synth Strings 2", (-1,0):"Orchestral Hit", (14,0x23): "Choir Aahs",
     (21,0x3):"Solo Voice", (69,0x24): "Voice Tenor", (193,0x0):"Voice Oohs", 
    (16,0x44): "Trumpet Section", (56,0x10):"Solo Trumpet 1", (-1,0): "Solo Trumpet 2", (-1,0):"Muted Trumpet", 
    (1,0x3E): "Trombone", (1,0x3F):"Tuba", (173,0x42): "Saxophone", (175,0x44):"Brass Section", 
    (1,0x3B): "Brass 1", (13,0x3D):"Brass 2", (22,0x52): "Brass 3", (90,0x42):"Brass 4", (123,0x40): "Horn Section", 
    (140,0x40):"French Horn", (17,0x43): "French Horns 1", (156,0x42):"French Horns 2", 
    (69,0x34): "English Horn", (-1,0):"Horns", (167,0x41): "Bass & Horn", (1,0x36):"Bassoon 1", (-1,0): "Bassoon 2", 
    (1,0x33):"Flute 1", (85,0x33): "Flute 2", (135,0x34):"Oboe 1", 
    (-1,0): "Oboe 2", (1,0x35):"Clarinet", (-1,0): "Hard Clarinet", (4,0x51):"Pan Flute", (10,0x51): "Recorder", (25,0x2A):"Bagpipe", 
    (16,0x5E): "Ocarina", (24,0x62):"Synth Sine", 
    (178,0x63): "Synth Triangle 1", (-1,0):"Synth Triangle 2", (3,0x61): "Synth Saw", (12,0x60):"Synth Square", 
    (58,0x5C): "Synth Saw-Triangle", (161,0x5D):"Synth Distorted", (162,0x5C): "Synth 1", (-1,0):"Synth 2", 
    (15,0x5E): "Synth 3", (138,0x52):"Synth 4", (-1,0): "Unused Synth", (1,0x79):"Timpani 1", (-1,0): "Timpani 2", 
    (5,0x53):"Steel Drum", (107,0x10): "Wood Block", (64,0x10):"Drop Echo", 
    (9,0x7B): "Pitched Drum", (99,0x7E):"Pitched Crash Cym", (123,0x3): "Pitched Cymbal", (136,0x7C):"Pitched Tamburine", (141,0x11): "Pitched Shaker", 
    (136,0x7B):"Pitched Claves", (29,0xD): "FoggyForest Perc", (139,0x6A):"BoulderQuarryPerc", 
    (26,0x41): "B&H Horn", (170,0x41):"B&H Bass", (51,0x10): "Fantasia(bgm051)", (108,0x11):"Fantasia(bgm108)", (-1,0):"OrigPercPitch1", (-1,0): "OrigPercPitch2",
    (8,0x7F): "Drumkit(Guild)", (-1,0):"Drumkit", (-1,0): "Drumkit Panned"
}


PMD_SOUNDFONT4 = {
    (106,0x0): "SFX Bubble 1", (106,0x1): "SFX Bubble 2", (179,0x0):"SFX Bubble 3", (107,0x12): "SFX Clock", (191,0x0):"SFX Crack 1", 
    (191,0x1): "SFX Crack 2", (3,0x3):"SFX Dojo", (127,0x0): "SFX DrkFtrChrd", (183,0x1):"SFX Droplet 1", (183,0x3): "SFX Droplet 2", (126,0x3):"SFX Eating", 
    (112,0x1): "SFX Electro 1", (114,0x1):"SFX Electro 2", 
    (114,0x2): "SFX Electro 3", (81,0x74):"SFX Electro 4", (115,0x2): "SFX Fire 1", (116,0x1):"SFX Fire 2", (115,0x1): "SFX Fire Pop", 
    (-1,0):"SFX Harpsichord", (188,0x2): "SFX Hiss", (112,0x0):"SFX Magic 1", 
    (117,0x1): "SFX Magic 2", (117,0x0):"SFX Magic 3", (118,0x0): "SFX Magic 4", (190,0x2):"SFX Rustling", (14,0x65): "SFX Wind Gust", 
    (179,0x1):"SFX Splash", (113,0x2): "SFX Swoosh", (101,0x0):"SFX Thunder", 
    (103,0x0): "SFX Tremor 1", (103,0x1):"SFX Tremor 2", (105,0x0): "SFX Tremor 3", (105,0x1):"SFX Tremor 4", (104,0x0): "SFX Tremor 5", 
    (0,0x33):"SFX WaterR 1", (186,0x1): "SFX WaterR 2", (186,0x2):"SFX WaterR 3", 
    (190,0x1): "SFX WaterR 4", (190,0x0):"SFX WaterR 5", (0,0x3B): "SFX WaterRSW 1", (100,0x1):"SFX WaterS 1", (185,0x2): "SFX WaterS 2", 
    (-1,0):"SFX WaterS 3", (128, 0x0): "SFX WaterSR 1", (125,0x4):"SFX WaterSW 1", 
    (125,0x3): "SFX WaterW 1", (100,0x0):"SFX Wave or Wind 1", (100,0x2): "SFX Wave or Wind 2", (113,0x0):"SFX Wave or Wind 3", 
    (181,0x1): "SFX Wave or Wind 4", (189,0x0):"SFX Wind 1", (182,0x2): "SFX Wind 2", (183,0x0):"SFX Wind 3", 
    (107,0x3C): "SFX WindH 1", (107,0x3B):"SFX WindH 2", (101,0x2): "SFX WindH 3", (-1,0):"SFX WindH 4", (107,0x3E): "SFX WindH 5", 
    (18,0x3):"SFX WNoise 1", (96,0x6C): "SFX WNoise 2", (-1,0):"SFX Crack 3", 
    (-1,0): "SFX Electro 5", (-1,0):"SFX Electro 6", (-1,0): "SFX Explosion", (-1,0):"SFX Magic 5", 
    (-1,0): "SFX Magic 6", (-1,0):"SFX Ringing Noise", (-1,0): "SFX Thunder Far", (104,0x0):"SFX Tremor 5", 
    (-1,0): "SFX Tremor 6", (-1,0):"SFX TremOrFire 1", (-1,0): "SFX TremOrFire 2", (-1,0):"SFX unkn", 
    (-1,0): "SFX WaterRW 1", (-1,0):"SFX WaterSR 2", (-1,0): "SFX WaterSW 2", (-1,0):"SFX WindH 1", 
    (-1,0): "SFX WindH 1-1", (-1,0):"SFX WNoise 3", (-1,0): "SFX WNoise 4", (-1,0):"SFX Brass5th"
}

def parse_prgi_chunk(fd,prgi_slots,preset_list,file_number):
    magic =fd.read(4)# magic prgi
    if magic != b'prgi':
        print('parse error: The prgi chunk starts with a wrong magic number')
        print(magic)
        sys.exit(1)
    parse_bytes(fd,8)# "useless"
    chunklen = parse_bytes(fd,4)# chunk length
    entries = []
    cpt = 0
    #programPtrTbl
    for i in range(prgi_slots):
        entry = parse_bytes(fd,2)
        if entry != 0:
            cpt += 1
        entries.append(entry)
    padding = (16 -((prgi_slots * 2) % 16))%16
    parse_bytes(fd,padding)
    #ProramInfoTbl
    for j in range(cpt):
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
        for k in range(nb_lfos):
            lfos_values += fd.read(16)


        padding = fd.read(16)#padding bytes (same as pad_byte apparently)
        for l in range(nb_splits):
            splits_values += fd.read(48)

        preset = first_part + lfos_values + padding + splits_values
        preset_id = int.from_bytes(program_id,byteorder='little',signed=False)
        key = (file_number,preset_id)
        print(key)
        instr_name = PMD_SOUNDFONT.get(key)
        if instr_name is None:
            instr_name = PMD_SOUNDFONT4.get(key)
        if instr_name is not None:
            iter = (instr_name,preset)
            preset_list.append(iter)
    return preset_list

def main():
    args = parse_args()
    if not os.path.exists(args.SWD):
        print(f'Directory {args.SWD} is not found')
        sys.exit(1)
    if not os.path.isdir(args.SWD):
        print(f'{args.SWD} is not a directory')
        sys.exit(1)
    sample_list = set()
    preset_list = []
    ban_list = [109,194,195,196,197,198]
    for i in range(201):
        if i in ban_list :
            continue
        file_number ='0'
        if i < 100:
            file_number += '0'
        if i < 10:
            file_number += '0'
        file_number += str(i)
        file_name = f'{args.SWD}/bgm{file_number}.swd'
        with open(file_name, 'rb') as file:
            length,pcmdlen,nb_wavi_slots,nb_prgi_slots,wavilen = parse_header(file)
            sample_list = parse_wavi_chunk(file,nb_wavi_slots,sample_list)
            preset_list = parse_prgi_chunk(file,nb_prgi_slots,preset_list,i)

    for i in preset_list:
        instr_name,data = i
        file_name = f"PRESETS/{instr_name}.bin"
        with open(file_name,'wb') as output:
            output.write(data)
    for j in sample_list:
        sample_id,data = j
        print(sample_id)
        file_name = f'SAMPLES/{sample_id}.bin'
        with open(file_name,'wb') as output:
            output.write(data)

if __name__ == "__main__":
    main()