
import argparse
import math
import os
import sys
import time
from datetime import datetime


def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "Trezer",
        description="Takes a MIDI file as input and prints its functions"
    )

    parser.add_argument("midi",help="The path to the MIDI file to translate")
    parser.add_argument("output",help="The path to the SMD file to write")
    parser.add_argument("--check",help="checks if the format of the MIDI file is correct",action="store_true")
    return parser.parse_args()

def parse_bytes(fd,bytes_count):
    """ reads from the file descriptor an amount of bytes
    Arguments:
        fd(BufferedReader): the file descriptor
        bytes_count(int): the amount of bytes to read

    Returns:
        int: the int value read in big endian

    """
    something = fd.read(bytes_count)
#print(something)
#if something is b'':
#    raise Exception
    return int.from_bytes(something,byteorder="big",signed=False)


def generate_header_chunk(file_descriptor,midi_source):
    file_descriptor.write(b'\x73\x6D\x64\x6C') #smdl
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #file length
    file_descriptor.write(b'\x15\x04') 
    file_descriptor.write(b'\x00\x00') #unknowns
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    now = datetime.now()
    #array = [(now.year & 0xFF),((now.year & 0xFF00) >> 8),now.month,now.day,now.hour,now.minute,now.second]
    #date = bytearray(array)
    #file_descriptor.write(date)
    file_descriptor.write(now.year.to_bytes(2,'little'))
    file_descriptor.write(now.month.to_bytes(1,'little'))
    file_descriptor.write(now.day.to_bytes(1,'little'))
    file_descriptor.write(now.hour.to_bytes(1,'little'))
    file_descriptor.write(now.minute.to_bytes(1,'little'))
    file_descriptor.write(now.second.to_bytes(1,'little'))
    file_descriptor.write(b'\x00')
    file_descriptor.write(b'\x00\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA\xAA')
    file_descriptor.write(b'\x01\x00\x00\x00')
    file_descriptor.write(b'\x01\x00\x00\x00')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF')

def parse_header(file_descriptor):
    """ reads the header chunk in a MIDI file.
        Currently can only read format 0 MIDI files
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int: the division value of the track (in beats per quarter note)
    
    """
    first_line= file_descriptor.readline() #ntrks x
    nb_tracks = int(first_line [6:].strip())
    second_line = file_descriptor.readline()
    tpqn = int(second_line [5:].strip())
    return nb_tracks,tpqn



def generate_song_chunk(file_descriptor,midi_descriptor,nb_channel):
        file_descriptor.write(b'\x73\x6F\x6E\x67') #song
        file_descriptor.write(b'\x00\x00\x00\x01')
        file_descriptor.write(b'\x10\xFF\x00\x00')
        file_descriptor.write(b'\xB0\xFF\xFF\xFF')
        file_descriptor.write(b'\x01\x00')
        nbtrks,tpqn = parse_header(midi_descriptor)
        file_descriptor.write(tpqn.to_bytes(2,'little')) # ticks per quarter note ????
        file_descriptor.write(b'\x01\xFF')
        file_descriptor.write(nbtrks.to_bytes(1,'little'))
        # print(nb_channel)
        file_descriptor.write(nb_channel.to_bytes(1,'little'))
        file_descriptor.write(b'\x00\x00\x00\x0F')
        file_descriptor.write(b'\xFF\xFF\xFF\xFF')
        file_descriptor.write(b'\x00\x00\x00\x40')
        file_descriptor.write(b'\x00\x40\x40\x00')
        file_descriptor.write(b'\x00\x02')
        file_descriptor.write(b'\x00\x08')
        file_descriptor.write(b'\x00\xFF\xFF\xFF')
        file_descriptor.write(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
        return nbtrks,tpqn

def add_wait_time(file,length,factor,last_pause,position):
    value = length
    if value == 0: # No pause
        return position,0
    elif last_pause == value: # Try RepeatLastPause
        file.write(b'\x90') # repeatLastPause
        position += 1
        return position,last_pause
    value = math.floor(value / factor) # Convert MIDI ticks to SMD?
    match value: # Try fixed Duration Pause
        case 96: # 0x80
            file.write(b'\x80')
            position += 1
            return position,96
        case 72: # 0x81
            file.write(b'\x81')
            position += 1
            return position,72
        case 64: # 0x82
            file.write(b'\x82')
            position += 1
            return position,64
        case 48: # 0x83
            file.write(b'\x83')
            position += 1
            return position,48
        case 36: # 0x84
            file.write(b'\x84')
            position += 1
            return position,36
        case 32: # 0x85
            file.write(b'\x85')
            position += 1
            return position,32
        case 24: # 0x86
            file.write(b'\x86')
            position += 1
            return position,24
        case 18: # 0x87
            file.write(b'\x87')
            position += 1
            return position,18
        case 16: # 0x88
            file.write(b'\x88')
            position += 1
            return position,16
        case 12: # 0x89
            file.write(b'\x89')
            position += 1
            return position,12
        case 9: # 0x8A
            file.write(b'\x8A')
            position += 1
            return position,9
        case 8: # 0x8B
            file.write(b'\x8B')
            position += 1
            return position,8
        case 6: # 0x8C
            file.write(b'\x8C')
            position += 1
            return position,6
        case 4: # 0x8D
            file.write(b'\x8D')
            position += 1
            return position,4
        case 3: # 0x8E
            file.write(b'\x8E')
            position += 1
            return position,3
        case 2: # 0x8F
            file.write(b'\x8F')
            position += 1
            return position,2
        case _:
            new_value = value - last_pause
            if new_value > 0 and new_value <= 255 and last_pause != -1: # Try AddToLastPause (if last_pause != -1, i.e a pause happened prior)
                file.write(b'\x91')
                file.write(new_value.to_bytes(1,'little'))
                position += 2
                return position,value
            elif value <= 255: # Try Pause8Bits
                file.write(b'\x92')
                file.write(value.to_bytes(1,'little'))
                position += 2
                return position,value
            elif value <= 65535: #Try Pause16Bits
                file.write(b'\x93')
                file.write(value.to_bytes(2,'little'))# little?
                position += 3
                return position,value
            elif value <= 16777215: #Try Pause24Bits
                file.write(b'\x94')
                file.write(value.to_bytes(3,'little')) # little?
                position += 4
                return position,value
            else: #Too big for 24Bits 
                file.write(b'\x94')
                cap = 16777215
                part_value = value - cap
                file.write(cap.to_bytes(3,'little')) # little?
                position += 4
                add_wait_time(file,part_value,factor,cap,position)

def calculate_bpm(micro_per_quartick): #MIDI uses microseconds per quarter tick
                                        # Formula? -> micro/ 1 000 000 -> seconds per quarter tick?
                                        # 60 / seconds -> BPM???
    secs = micro_per_quartick /1000000
    bpm = 60/secs
    return int(bpm)


NOTES = {
    0:[0x0,-1], 1:[0x1,-1], 2:[0x2,-1], 3:[0x3,-1], 4:[0x4,-1], 5:[0x5,-1], 6:[0x6,-1], 7:[0x7,-1], 8:[0x8,-1], 9:[0x9,-1], 10:[0xA,-1], 11:[0xB,-1],
    12 :[0x0,0], 13:[0x1,0], 14:[0x2,0], 15:[0x3,0], 16:[0x4,0], 17:[0x5,0], 18:[0x6,0], 19:[0x7,0], 20:[0x8,0], 21:[0x9,0], 22:[0xA,0], 23:[0xB,0],
    24 :[0x0,1], 25:[0x1,1], 26:[0x2,1], 27:[0x3,1], 28:[0x4,1], 29:[0x5,1], 30:[0x6,1], 31:[0x7,1], 32:[0x8,1], 33:[0x9,1], 34:[0xA,1], 35:[0xB,1],
    36 :[0x0,2], 37:[0x1,2], 38:[0x2,2], 39:[0x3,2], 40:[0x4,2], 41:[0x5,2], 42:[0x6,2], 43:[0x7,2], 44:[0x8,2], 45:[0x9,2], 46:[0xA,2], 47:[0xB,2],
    48 :[0x0,3], 49:[0x1,3], 50:[0x2,3], 51:[0x3,3], 52:[0x4,3], 53:[0x5,3], 54:[0x6,3], 55:[0x7,3], 56:[0x8,3], 57:[0x9,3], 58:[0xA,3], 59:[0xB,3],
    60 :[0x0,4], 61:[0x1,4], 62:[0x2,4], 63:[0x3,4], 64:[0x4,4], 65:[0x5,4], 66:[0x6,4], 67:[0x7,4], 68:[0x8,4], 69:[0x9,4], 70:[0xA,4], 71:[0xB,4],
    72 :[0x0,5], 73:[0x1,5], 74:[0x2,5], 75:[0x3,5], 76:[0x4,5], 77:[0x5,5], 78:[0x6,5], 79:[0x7,5], 80:[0x8,5], 81:[0x9,5], 82:[0xA,5], 83:[0xB,5],
    84 :[0x0,6], 85:[0x1,6], 86:[0x2,6], 87:[0x3,6], 88:[0x4,6], 89:[0x5,6], 90:[0x6,6], 91:[0x7,6], 92:[0x8,6], 93:[0x9,6], 94:[0xA,6], 95:[0xB,6],
    96 :[0x0,7], 97:[0x1,7], 98:[0x2,7], 99:[0x3,7], 100:[0x4,7], 101:[0x5,7], 102:[0x6,7], 103:[0x7,7], 104:[0x8,7], 105:[0x9,7], 106:[0xA,7], 107:[0xB,7],
    108 :[0x0,8], 109:[0x1,8], 110:[0x2,8], 111:[0x3,8], 112:[0x4,8], 113:[0x5,8], 114:[0x6,8], 115:[0x7,8], 116:[0x8,8], 117:[0x9,8], 118:[0xA,8], 119:[0xB,8],
    120 :[0x0,9], 121:[0x1,9], 122:[0x2,9], 123:[0x3,9], 124:[0x4,9], 125:[0x5,9], 126:[0x6,9], 127:[0x7,9] 

}


def change_octave(file,octave):
    file.write(b'\xA0')#Set Track Octave
    file.write(octave.to_bytes(1,'little'))

def convert_note(file,midi_note,current_octave,position):
    note,octave = NOTES.get(midi_note)
    if octave == -1:
        octave = 0
    if current_octave == -2:# No Notes yet, octave is yet unknown
        change_octave(file,octave)
        position += 2
    if octave == current_octave:
        return position,note,2
    if octave > current_octave:
        if octave - current_octave == 1:
            return position,note,3
        else:
            change_octave(file,octave)
            position +=2
            return position,note,2
    elif current_octave - octave == 1:
        return position,note,1
    elif current_octave - octave == 2:
        return position,note,0
    else:
        change_octave(file,octave)
        position += 2
        return position,note,2

def generate_first_track(smb_descriptor,midi_descriptor,cpt,tpqn):
    smb_descriptor.write(b'\x74\x72\x6B\x20') # trk
    smb_descriptor.write(b'\x00\x00\x00\x01')
    smb_descriptor.write(b'\x04\xFF\x00\x00')
    smb_descriptor.write(b'\x00\x00\x00\x00') # length of chunk

    smb_descriptor.write(cpt.to_bytes(1,'little')) # trk
    trk = cpt -1
    if trk <0:
        trk = 0
    if trk == 14:
        trk = 15
    smb_descriptor.write(trk.to_bytes(1,'little'))
    smb_descriptor.write(b'\x00\x00')

    position =20
    test = 0
    factor = tpqn/48 # Really not sure: tpqn -> MIDI ticks per quarter note
                     # 48 -> Ticks per quarter note of SMD.
                     # divide MIDI delta-time by factor for ticks in SMD
    last_pause = -1
    current_octave = -2

    # midi_descriptor.readline()
    # midi_descriptor.readline()
    line = midi_descriptor.readline()# \n
    master_clock = 0
    while(True):
        test += 1
        line = midi_descriptor.readline()
        if len(line) == 0 or line == '\n':
            break;
        # if line == "\n":
        #     midi_descriptor.readline()
        #     midi_descriptor.readline()
        #     midi_descriptor.readline()
        #     break;
        #print("###")
        #print(line)
        #print("###")
        parts = line.rsplit(', ')
        #print(parts[0])

        starttime = int(parts[0][10:])
        length = abs(starttime - master_clock)
        master_clock = starttime
        position,last_pause = add_wait_time(smb_descriptor,length,factor,last_pause,position)
        instruction = parts[1]
        match instruction:
            case "MetaMessage":
                match parts[2][5:]: # type
                    # case 1:
                    #     continue
                    # case 3:
                    #     continue
                    case 'Time Signature': # time signature???
                        continue # dunno what to do
                    case 'Set Tempo': # Tempo
                        bpm = calculate_bpm(int(parts[3][5:]))# SetTempo
                        smb_descriptor.write(b'\xA4')
                        smb_descriptor.write(bpm.to_bytes(1,'little'))
                        position += 2
                    case _:
                        continue
            case "Sysex event":
                continue # skip?
            case "ControlChange":
                match int(parts[2][9:]):
                    case 7: # Channel Volume??
                        smb_descriptor.write(b'\xE0') #SetTrackVolume
                        value = int(parts[3][9:])
                        smb_descriptor.write(value.to_bytes(1,'little'))
                        position += 2
                    case 10:# Pan
                        smb_descriptor.write(b'\xE8') #SetTrackPan
                        value = int(parts[3][9:])
                        smb_descriptor.write(value.to_bytes(1,'little'))
                        position += 2
                    case 11:# Expression Controller
                        smb_descriptor.write(b'\xE3') #SetTrackExpression (I dunno)
                        value = int(parts[3][9:])
                        smb_descriptor.write(value.to_bytes(1,'little'))
                        position += 2
            case "ProgramChange":
                continue #Technically SWD???
                # controller_number
            case "PitchBend":
                least_bytes = int(parts[2][12:])
                most_bytes = int(parts[3][11:])
                smb_descriptor.write(b'\xD7') # PitchBend
                smb_descriptor.write(least_bytes.to_bytes(1,'little')) # Legit no Idea of the order
                smb_descriptor.write(most_bytes.to_bytes(1,'little')) # too tired to find the order
                position += 3
                # least_bytes most_bytes
            case "PlayNote":
                velocity = int(parts[3][9:])
                midi_note = int(parts[2][9:])
                position,note,octave = convert_note(smb_descriptor,midi_note,current_octave,position)
                octave_shift = octave -2
                current_octave = octave if current_octave == -2 else current_octave + octave_shift
                print(current_octave)
                if(current_octave > 9 or current_octave <-1):
                    print("The octave value went out of bounds")
                    sys.exit(1)
                #/!\current octave is never changed#


                key_down = int(int(parts[4][9:])/factor)
                if len(hex(key_down))> 8: # That's a problem (> 0xyyyyyy)
                    print("Problematic: the key_hold duration is above what the .smd standard can muster.(?)")
                    sys.exit(1)
                elif len(hex(key_down)) > 6: # > 0xyyyy
                    key_duration = key_down.to_bytes(3,'little')
                    nb_param = 0x03
                elif len(hex(key_down)) > 4:# > 0xyy
                    key_duration = key_down.to_bytes(2,'little')
                    nb_param = 0x02
                elif key_down != 0:
                    key_duration = key_down.to_bytes(1,'little')
                    nb_param = 0x01
                else:
                    key_duration = 0
                    nb_param = 0x00

                
                note_data = (note | (octave << 4) | (nb_param << 6))
                #print(note_data)
                smb_descriptor.write(velocity.to_bytes(1,'little'))
                smb_descriptor.write(note_data.to_bytes(1,'little'))
                position += 2
                if key_duration != 0:
                    smb_descriptor.write(key_duration)
                    position += nb_param
                # key note velocity
            case _:
                print(f"parse error: {instruction} instruction not recognised")
    #print(test)
    smb_descriptor.write(b'\x98')
    position += 1
    padding = (4 - (position % 4))% 4
    for i in range(padding):
        smb_descriptor.write(b'\x98')
    print("done.")

def generate_eoc_chunk(file):
    file.write(b'\x65\x6F\x63\x20') # trk
    file.write(b'\x00\x00\x00\x01')
    file.write(b'\x04\xFF\x00\x00')
    file.write(b'\x00\x00\x00\x00') # length of chunk

def main():
    args = parse_args()
    with open(args.output,"wb") as file:
        
        with open(args.midi,"r") as midi:
            data = midi.read()
            nb_channel = data.count("channel")
        with open(args.midi,"r") as midi:
            generate_header_chunk(file,midi)
            nbrtrk,tpqn =generate_song_chunk(file,midi,nb_channel)
            for i in range(17):
                generate_first_track(file,midi,i,tpqn) # tempo???
            generate_eoc_chunk(file)
    with open(args.output, 'rb') as patch:
        length = 0
        length_list = []
        parse_bytes(patch,128)
        length += 128
        track = parse_bytes(patch,4)
        print(track.to_bytes(4,'big'))
        length += 4
        while(track == 0x74726b20):
            parse_bytes(patch,12)
            length += 12
            track_length = 0
            byte = parse_bytes(patch,1)
            track_length += 1
            while(byte != 0x98):
                byte = parse_bytes(patch,1)
                track_length+=1
            length_list.append(track_length)
            length += track_length
            padding = (4 - (length % 4))% 4
            parse_bytes(patch,padding)
            length += padding
            track = parse_bytes(patch,4)
            length += 4
    print(length)
    print(length_list)
    length +=12 # 12 byte for eoc chunk (without magic already read.)
    with open(args.output, 'rb+') as fix_length:
        parse_bytes(fix_length,8)
        fix_length.write(length.to_bytes(4,'little'))
        parse_bytes(fix_length,64) # ?
        parse_bytes(fix_length,64)
        pos = 140
        for i in length_list:
            fix_length.write(i.to_bytes(4,'little'))
            pos += 4
            parse_bytes(fix_length,i+12)
            pos += (i+12)
            padding = (4 - (pos % 4))% 4
            parse_bytes(fix_length,padding)
            pos += padding
if __name__ == "__main__":
    main()

