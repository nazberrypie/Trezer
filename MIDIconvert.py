
import argparse
import os
import math
import sys
import json
from datetime import datetime

from utils import midi_parse_bytes,get_padding,GM_SOUNDFONT,PMD_SOUNDFONT,PMD_SOUNDFONT2,PMD_SOUNDFONT3,PMD_SOUNDFONT4,PMD_SOUNDFONT5

def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "MIDIconvert",
        description="Takes a file made by MIDIparse as input and creates an SMD file in the SMDS directory"
    )

    parser.add_argument("input",help="The name of the instructions file to translate, located in the MIDI_TXT directory.")
    parser.add_argument("output",help="The name of the SMD file to write")
    parser.add_argument("--linkbyte",help="value (in hex) of the 2 bytes that handles the SMD/SWD connection. Defaults to 0000 if unspecified",type=str, default= '0000')
    parser.add_argument("--pmd-soundfont",help="Maps the preset used to the PMD soundfont. Maps to the GM soundfont otherwise.",action="store_true")
    return parser.parse_args()

def generate_header_chunk(file_descriptor,link_byte):
    """ Writes the header chunk of the SMD file.
        Most of the header is actually static,
        The date of creation being an exception.
        A link byte (at hex 0xE and 0xF) is needed
        to link the SMD file to it's SWD.
        (an SMD and SWD of different link byte will produce no sound)
        Although the link bytes in the SMD can be incorrect (for some reason)
        It is set here anyway.
        (the value in the header does not matter. The value used by the events
        0xA9 and 0xAA must be correct however.)
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
        link_byte(str): the value of the link bytes

    """
    file_descriptor.write(b'\x73\x6D\x64\x6C') #smdl
    file_descriptor.write(b'\x00\x00\x00\x00') #zeros
    file_descriptor.write(b'\x00\x00\x00\x00') #file length
    file_descriptor.write(b'\x15\x04')
    link_byte = int(link_byte,base=16) 
    file_descriptor.write(link_byte.to_bytes(2,'big')) #link byte
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
    file_descriptor.write(b'\x01\x00\x00\x00')
    file_descriptor.write(b'\x01\x00\x00\x00')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF')

def parse_header(file_descriptor):
    """ reads the header chunk in the instruction file.
        the 3 first lines are read, holding the amount of
        tracks, the tick per quarter note amount (~=BPM)
        and the song duration in ticks.
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int,int,int: the amount of track, the tick per quarter not amount
        and the song duration.
    
    """
    first_line= file_descriptor.readline() #ntrks x
    nb_tracks = int(first_line [6:].strip())
    second_line = file_descriptor.readline()
    tpqn = int(second_line [5:].strip())
    third_line = file_descriptor.readline()
    song_duration = int(third_line [14:].strip())
    file_descriptor.readline() # \n?
    return nb_tracks,tpqn,song_duration



def generate_song_chunk(file_descriptor,midi_descriptor,nb_channel):
    """ Writes the song chunk of the SMD file.
        Again, most of the chunk is static,
        The interesting value here being ticks per quarter notes.
        "Vanilla" SMD's uses a fixed 48 ticks per quarter note for most (all?) songs.
        Generated ones changes this value according to MIDI instructions.
        The amount of tracks and channels is also changed here.

    Arguments:
        file_descriptor(BufferedReader): the SMD file descriptor
        midi_descriptor(BufferedReader): the MIDI instructions file descriptor
        nb_channel(int): the amount of channels (fixed at 16 here)
    Returns:
        int,int,int: the amount of track, the tick per quarter not amount
        and the song duration.
    """
    file_descriptor.write(b'\x73\x6F\x6E\x67') #song
    file_descriptor.write(b'\x00\x00\x00\x01')
    file_descriptor.write(b'\x10\xFF\x00\x00')
    file_descriptor.write(b'\xB0\xFF\xFF\xFF')
    file_descriptor.write(b'\x01\x00')
    nbtrks,tpqn,song_duration = parse_header(midi_descriptor)
    file_descriptor.write(tpqn.to_bytes(2,'little')) # ticks per quarter note ????
    file_descriptor.write(b'\x01\xFF')
    file_descriptor.write(nbtrks.to_bytes(1,'little'))
    file_descriptor.write(nb_channel.to_bytes(1,'little'))
    file_descriptor.write(b'\x00\x00\x00\x0F')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF')
    file_descriptor.write(b'\x00\x00\x00\x40')
    file_descriptor.write(b'\x00\x40\x40\x00')
    file_descriptor.write(b'\x00\x02')
    file_descriptor.write(b'\x00\x08')
    file_descriptor.write(b'\x00\xFF\xFF\xFF')
    file_descriptor.write(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
    return nbtrks,tpqn,song_duration

def add_wait_time(file,length,last_pause,position):
    """ Writes in the SMD file a wait event
        of the appropriate value.
        Wait events stops for a duration the song reading.
        It is used for example as a delta-time between two notes,
        so they can be played one after the other.
        The function here is severely unoptimal: some events that
        holds specific stop time are unused 
        even though they would take less space upon writing.
        The current method is functional but uses a high amount of bytes,
        ignoring more optimal events.
    Arguments:
        file(BufferedReader): the SMD file descriptor
        length(int): the amount of time to wait in ticks
        last_pause(int): the value of the last pause made
        position(int): a position counter, used to count the length of the chunk.
    """
    value = length
    if value == 0: # No pause
        return position,0
    elif last_pause == value: # Try RepeatLastPause
        file.write(b'\x90') # repeatLastPause
        position += 1
        return position,last_pause
    match value: # Try fixed Duration Pause
        # case 96: # 0x80
        #     file.write(b'\x80')
        #     position += 1
        #     return position,96
        # case 72: # 0x81
        #     file.write(b'\x81')
        #     position += 1
        #     return position,72
        # case 64: # 0x82
        #     file.write(b'\x82')
        #     position += 1
        #     return position,64
        # case 48: # 0x83
        #     file.write(b'\x83')
        #     position += 1
        #     return position,48
        # case 36: # 0x84
        #     file.write(b'\x84')
        #     position += 1
        #     return position,36
        # case 32: # 0x85
        #     file.write(b'\x85')
        #     position += 1
        #     return position,32
        # case 24: # 0x86
        #     file.write(b'\x86')
        #     position += 1
        #     return position,24
        # case 18: # 0x87
        #     file.write(b'\x87')
        #     position += 1
        #     return position,18
        # case 16: # 0x88
        #     file.write(b'\x88')
        #     position += 1
        #     return position,16
        # case 12: # 0x89
        #     file.write(b'\x89')
        #     position += 1
        #     return position,12
        # case 9: # 0x8A
        #     file.write(b'\x8A')
        #     position += 1
        #     return position,9
        # case 8: # 0x8B
        #     file.write(b'\x8B')
        #     position += 1
        #     return position,8
        # case 6: # 0x8C
        #     file.write(b'\x8C')
        #     position += 1
        #     return position,6
        # case 4: # 0x8D
        #     file.write(b'\x8D')
        #     position += 1
        #     return position,4
        # case 3: # 0x8E
        #     file.write(b'\x8E')
        #     position += 1
        #     return position,3
        # case 2: # 0x8F
        #     file.write(b'\x8F')
        #     position += 1
        #     return position,2
        case _:
            # new_value = value - last_pause
            # if new_value > 0 and new_value <= 255 and last_pause != -1: # Try AddToLastPause (if last_pause != -1, i.e a pause happened prior)
            #     file.write(b'\x91')
            #     file.write(new_value.to_bytes(1,'little'))
            #     position += 2
            #     return position,value
            if value <= 255: # Try Pause8Bits
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
                add_wait_time(file,part_value,cap,position)

def calculate_bpm(micro_per_quartick):
    """ calculates the BPM of the track based on the
        microseconds per quarter ticks value.
        The following is just speculation:
        MIDI uses microseconds per quarter tick.
        One can calculate the BPM with the formula:
        - divide by 1 000 000 the microseconds per quarter tick value.
        - divide 60 by the value obtained above.
        Surprisingly, the SetTempo instruction is 1 byte long,
        preventing a BPM above 255. I have no idea of the impact
        this may have.
    Arguments:
        micro_per_quartick(int): the microseconds per quarter tick value.
    Returns:
        int: the BPM calculated. May be above 255.
    """
    secs = micro_per_quartick /1000000
    bpm = 60/secs
    return int(bpm)

# SOUNDFONT = {
#     0:0x1f, 1:-1, 2:-1, 3:-1, 4:-1, 5:-1, 6:0x0B, 7:-1, 8:-1, 9:-1, 10:-1, 11:-1,
#     12 :0, 13:0, 14:0, 15:0x0F, 16:0, 17:-1, 18:0, 19:0x1f, 20:0, 21:0, 22:0, 23:0x17,
#     24 :1, 25:-1, 26:1, 27:1, 28:1, 29:-1, 30:1, 31:0x1F, 32:-1, 33:-1, 34:1, 35:0x23,
#     36 :2, 37:-1, 38:2, 39:2, 40:2, 41:2, 42:2, 43:0x1F, 44:2, 45:2, 46:2, 47:0x0B,
#     48 :0x64, 49:3, 50:0x1c, 51:3, 52:-1, 53:3, 54:3, 55:3, 56:3, 57:3, 58:0x1c, 59:3,
#     60 :4, 61:-1, 62:4, 63:4, 64:4, 65:4, 66:4, 67:4, 68:0x44, 69:4, 70:4, 71:4,
#     72 :0x5F, 73:-1, 74:0x4A, 75:0x4B, 76:5, 77:5, 78:5, 79:5, 80:-1, 81:5, 82:-1, 83:5,
#     84 :6, 85:-1, 86:6, 87:6, 88:6, 89:6, 90:6, 91:6, 92:6, 93:6, 94:0x5E, 95:0x5F,
#     96 :0x60, 97:7, 98:7, 99:0x63, 100:7, 101:7, 102:7, 103:7, 104:7, 105:7, 106:7, 107:7,
#     108 :8, 109:8, 110:8, 111:8, 112:8, 113:8, 114:8, 115:8, 116:8, 117:8, 118:8, 119:8,
#     120 :9, 121:9, 122:9, 123:9, 124:9, 125:9, 126:9, 127:0x7F 

# }

# OLD_SOUNDFONT = {
#     0:0x1f, 1:-1, 2:-1, 3:-1, 4:-1, 5:-1, 6:0x0B, 7:-1, 8:-1, 9:-1, 10:-1, 11:-1,
#     12 :0, 13:0, 14:0, 15:0x0F, 16:0, 17:-1, 18:0, 19:0x1f, 20:0, 21:0, 22:0, 23:0x17,
#     24 :1, 25:-1, 26:1, 27:1, 28:1, 29:-1, 30:1, 31:0x1F, 32:-1, 33:-1, 34:1, 35:0x23,
#     36 :2, 37:-1, 38:2, 39:2, 40:2, 41:2, 42:2, 43:0x1F, 44:2, 45:2, 46:2, 47:0x0B,
#     48 :0x64, 49:3, 50:0x1c, 51:3, 52:-1, 53:3, 54:3, 55:3, 56:3, 57:3, 58:0x1c, 59:3,
#     60 :4, 61:-1, 62:4, 63:4, 64:4, 65:4, 66:4, 67:4, 68:0x44, 69:4, 70:4, 71:4,
#     72 :0x5F, 73:-1, 74:0x4A, 75:0x4B, 76:5, 77:5, 78:5, 79:5, 80:-1, 81:5, 82:-1, 83:5,
#     84 :6, 85:-1, 86:6, 87:6, 88:6, 89:6, 90:6, 91:6, 92:6, 93:6, 94:0x5E, 95:0x5F,
#     96 :0x60, 97:7, 98:7, 99:0x63, 100:7, 101:7, 102:7, 103:7, 104:7, 105:7, 106:7, 107:7,
#     108 :8, 109:8, 110:8, 111:8, 112:8, 113:8, 114:8, 115:8, 116:8, 117:8, 118:8, 119:8,
#     120 :9, 121:9, 122:9, 123:9, 124:9, 125:9, 126:9, 127:0x7F 

# }

# a dictionnary matching a midi note with the corresponding octave and note for an SMD
NOTES = {
    0:[0x0,0], 1:[0x1,0], 2:[0x2,0], 3:[0x3,0], 4:[0x4,0], 5:[0x5,0], 6:[0x6,0], 7:[0x7,0], 8:[0x8,0], 9:[0x9,0], 10:[0xA,0], 11:[0xB,0],
    12 :[0x0,1], 13:[0x1,1], 14:[0x2,1], 15:[0x3,1], 16:[0x4,1], 17:[0x5,1], 18:[0x6,1], 19:[0x7,1], 20:[0x8,1], 21:[0x9,1], 22:[0xA,1], 23:[0xB,1],
    24 :[0x0,2], 25:[0x1,2], 26:[0x2,2], 27:[0x3,2], 28:[0x4,2], 29:[0x5,2], 30:[0x6,2], 31:[0x7,2], 32:[0x8,2], 33:[0x9,2], 34:[0xA,2], 35:[0xB,2],
    36 :[0x0,3], 37:[0x1,3], 38:[0x2,3], 39:[0x3,3], 40:[0x4,3], 41:[0x5,3], 42:[0x6,3], 43:[0x7,3], 44:[0x8,3], 45:[0x9,3], 46:[0xA,3], 47:[0xB,3],
    48 :[0x0,4], 49:[0x1,4], 50:[0x2,4], 51:[0x3,4], 52:[0x4,4], 53:[0x5,4], 54:[0x6,4], 55:[0x7,4], 56:[0x8,4], 57:[0x9,4], 58:[0xA,4], 59:[0xB,4],
    60 :[0x0,5], 61:[0x1,5], 62:[0x2,5], 63:[0x3,5], 64:[0x4,5], 65:[0x5,5], 66:[0x6,5], 67:[0x7,5], 68:[0x8,5], 69:[0x9,5], 70:[0xA,5], 71:[0xB,5],
    72 :[0x0,6], 73:[0x1,6], 74:[0x2,6], 75:[0x3,6], 76:[0x4,6], 77:[0x5,6], 78:[0x6,6], 79:[0x7,6], 80:[0x8,6], 81:[0x9,6], 82:[0xA,6], 83:[0xB,6],
    84 :[0x0,7], 85:[0x1,7], 86:[0x2,7], 87:[0x3,7], 88:[0x4,7], 89:[0x5,7], 90:[0x6,7], 91:[0x7,7], 92:[0x8,7], 93:[0x9,7], 94:[0xA,7], 95:[0xB,7],
    96 :[0x0,8], 97:[0x1,8], 98:[0x2,8], 99:[0x3,8], 100:[0x4,8], 101:[0x5,8], 102:[0x6,8], 103:[0x7,8], 104:[0x8,8], 105:[0x9,8], 106:[0xA,8], 107:[0xB,8],
    108 :[0x0,9], 109:[0x1,9], 110:[0x2,9], 111:[0x3,9], 112:[0x4,9], 113:[0x5,9], 114:[0x6,9], 115:[0x7,9], 116:[0x8,9], 117:[0x9,9], 118:[0xA,9], 119:[0xB,9],
    120 :[0x0,10], 121:[0x1,10], 122:[0x2,10], 123:[0x3,10], 124:[0x4,10], 125:[0x5,10], 126:[0x6,10], 127:[0x7,10] 

}

# a dictionnary giving the amount of parameters (following bytes) an event have.
EVENTS = {  0x90: 0, 0x91: 1, 0x92 : 1, 0x93: 2,
            0x94: 3, 0x95 : 1, 0x98: 0, 0x99: 0,
            0xA0 : 1, 0xA1: 1, 0xA4: 1, 0xA5 : 1,# SetTempo is intentionnaly put twice here
            0xAB: 0, 0xAC: 1, 0xCB : 0, 0xD7: 2,
            0xE0: 1, 0xE3: 1,0xE8 : 1, 0xF8: 0,
    # Unknown but used
            0x9C: 1, 0x9D: 1, 0x9E: 1, 0xA8: 2,
            0xA9: 1, 0xAA: 1, 0xAF: 3, 0xB0: 0,
            0xB1: 1, 0xB2: 1, 0xB3: 1, 0xB4: 2,
            0xB5: 1, 0xB6: 1, 0xBC: 1, 0xBE: 2,
            0xBF: 1, 0xC0: 1, 0xC3: 1, 0xD0: 2,
            0xD1: 1, 0xD2: 1, 0xD3: 2, 0xD4: 3,
            0xD5: 2, 0xD6: 2, 0xD8: 2, 0xDB: 1,
            0xDC: 5, 0xDD: 4, 0xDF: 1, 0xE1: 1,
            0xE2: 3, 0xE4: 5, 0xE5: 4, 0xE7: 1,
            0xE9: 1, 0xEA: 3, 0xEC: 5, 0xED: 4,
            0xEF: 1, 0xF0: 5, 0xF1: 4, 0xF2: 2,
            0xF3: 3, 0xF6: 1,
    # Any other 0x (0x90 -> 0xFF) are considered INVALID
            0x96: 0, 0x97: 0, 0x9A: 0, 0x9B: 0,
            0x9F: 0, 0xA2: 0, 0xA3: 0, 0xA6: 0,
            0xA7: 0, 0xAD: 0, 0xAE: 0, 0xB7: 0,
            0xB8: 0, 0xB9: 0, 0xBA: 0, 0xBB: 0,
            0xBD: 0, 0xC1: 0, 0xC2: 0, 0xC4: 0,
            0xC5: 0, 0xC6: 0, 0xC7: 0, 0xC8: 0,
            0xC9: 0, 0xCA: 0, 0xCC: 0, 0xCD: 0,
            0xCE: 0, 0xCF: 0, 0xD9: 0, 0xDA: 0,
            0xDE: 0, 0xE6: 0, 0xEB: 0, 0xEE: 0,
            0xF4: 0, 0xF5: 0, 0xF7: 0, 0xF9: 0,
            0xFA: 0, 0xFB: 0, 0xFC: 0, 0xFD: 0,
            0xFE: 0, 0xFF: 0
}


def change_octave(file,octave):
    """ writes a change octave in the SMD file,
    in case the octave shift between two notes is higher than 2.
    Arguments:
        file(BufferedReader): the file descriptor.
        octave(int): the new octave to set.
    Returns:
        int: the BPM calculated. May be above 255.
    """
    file.write(b'\xA0')#Set Track Octave
    file.write(octave.to_bytes(1,'little'))

def convert_note(file,midi_note,current_octave,position):
    """ retrieves and convert a MIDI note to a note compatible with SMD.
        MIDI notes have a value of 0 to 127.
        The value in question defines both the note and the octave.
        SMD file notes works fairly differently:
        a "Note Event" in SMD cannot define an octave,
        it just shifts the current octave (from -2 octave to +1)
        We check if the shift from the current octave is too big
        and use instead a "Set Octave Event".
        Another problem arise in octave being the difference of octave
        between MIDI and SMD.
        MIDI goes from -1 to 9
        SMD goes from 0 to 9
        This might imply that an octave is missing in the SMD format,
        or that the octave mechanic was misunderstood.
        As of now, notes with Octave 9 of MIDI raises
        a warning and are written as is (stopping the program).
        The bahaviour in these case are unknown.
    Arguments:
        file(BufferedReader): the file descriptor.
        midi_note(int): the value of the midi note (0-127).
        current_octave(int): the octave at which the song is currently.
        position(int): a position counter, used to count the length of the chunk.
    Returns:
        int: the updated position.
        int: the corresponding hex for the note.
        int: the octave shift value. 
            (the value gets substracted by 2 afterwards during execution. The value, possibly negative, is added to the track octave)
        int: the new track octave.
    """
    note,octave = NOTES.get(midi_note)
    if octave == 10:
        print("warning: an octave of 10 (9 in MIDI) has been found. SMD files is said to not support these.")
    if current_octave == -2:# No Notes yet, octave is yet unknown
        change_octave(file,octave)
        position += 2
        return position,note,2,octave
    if octave == current_octave:
        return position,note,2,current_octave
    if octave > current_octave:
        if octave - current_octave == 1:
            return position,note,3,octave
        else:
            change_octave(file,octave)
            position +=2
            return position,note,2,octave
    elif current_octave - octave == 1:
        return position,note,1,octave
    elif current_octave - octave == 2:
        return position,note,0,octave
    else:
        change_octave(file,octave)
        position += 2
        return position,note,2,octave

def generate_track(smb_descriptor,midi_descriptor,cpt,link_byte,programs_list,pmd_flag,song_duration):
    """ Generates an SMD track by converting the MIDI instruction given.
    One track in the SMD represents one channel in the MIDI instructions.
    A set of instruction is read and translated until an empty line is reached
    (indicating the end of the MIDI channel instructions)
    Arguments:
        file(BufferedReader): the file descriptor.
        midi_note(int): the value of the midi note (0-127).
        current_octave(int): the octave at which the song is currently.
        position(int): a position counter, used to count the length of the chunk.
    Returns:
        int: the updated position.
        int: the corresponding hex for the note.
        int: the octave shift value. 
            (the value gets substracted by 2 afterwards during execution. The value, possibly negative, is added to the track octave)
        int: the new track octave.
    """
    print(f"writing track {cpt}...")
    current_bank = 0
    smb_descriptor.write(b'\x74\x72\x6B\x20') # trk
    smb_descriptor.write(b'\x00\x00\x00\x01')
    smb_descriptor.write(b'\x04\xFF\x00\x00')
    smb_descriptor.write(b'\x00\x00\x00\x00') # length of chunk
    # This is the track ID. goes from 0 to 17.
    smb_descriptor.write(cpt.to_bytes(1,'little')) # trk
    # calculate channel ID used
    trk = cpt -1
    # Track ID 0 and 1 both uses channel 0
    if trk <0:
        trk = 0
    # Track Id goes from 0 to 17, but channels goes from 0 to 15?
    # Track 0 and 1 shares the same channel
    # When arriving at Track 17, there is no channel left.
    # Although it shouldn't happen (MIDI instruction file is capped at 17 tracks by construction)
    
    # if trk == 14:
    #     trk = 15

    #Writing the Channel ID of the track
    smb_descriptor.write(trk.to_bytes(1,'little'))
    smb_descriptor.write(b'\x00\x00')

    position =20
    test = 0

    # factor = 1#tpqn/48 # Really not sure: tpqn -> MIDI ticks per quarter note
    #                  # 48 -> Ticks per quarter note of SMD.
    #                  # divide MIDI delta-time by factor for ticks in SMD

    last_pause = -1
    current_octave = -2
    master_clock = 0
    while(True):
        line = midi_descriptor.readline()
        if len(line) == 0 or line == '\n':
            break
        parts = line.rsplit(', ')

        starttime = int(parts[0][10:])
        length = abs(starttime - master_clock)
        master_clock = starttime
        position,last_pause = add_wait_time(smb_descriptor,length,last_pause,position)
        instruction = parts[1]
        match instruction:
            case "LoopPoint":
                smb_descriptor.write(b'\x99')
                position += 1
            case "MetaMessage":
                match parts[2][5:]: # type
                    case 'Time Signature': # time signature???
                        continue # dunno what to do
                    case 'Set Tempo': # Tempo
                        bpm = calculate_bpm(int(parts[3][5:]))# SetTempo
                        smb_descriptor.write(b'\xA4')
                        cpt = 0
                        while bpm >= 256:
                            bpm = math.floor(bpm /2)
                            cpt += 1
                        smb_descriptor.write(bpm.to_bytes(1,'little'))
                        position += 2
                    case _:
                        continue
            case "Sysex event":
                continue # skip?
            case "ControlChange":
                match int(parts[2][9:]):
                    case 7: # Channel Volume
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
            case "BankSelect":
                current_bank = int(parts[2][5:])
            case "InstrChange":
                # Upon Changing preset, the A9 and AA event seems to be needed.
                # furthermore, the value used by these events must match the link_byte
                # set in the corresponding SWD file.
                # a mismatch between the value used in these events and the one set in the SWD file
                # will produce no sound.
                first_byte = int(link_byte[:2],base=16)
                second_byte = int(link_byte[2:],base=16)
                smb_descriptor.write(b'\xA9')
                smb_descriptor.write(second_byte.to_bytes(1,'little'))
                smb_descriptor.write(b'\xAA')
                smb_descriptor.write(first_byte.to_bytes(1,'little'))
                position += 4
                smb_descriptor.write(b'\xAC') # SetProgram
                value = int(parts[2][18:])

                # the json file produced uses the pmd soundfont instruments names
                if pmd_flag is True: # "soundfont flag is set"
                    match current_bank:
                        case 0:
                            program_name=PMD_SOUNDFONT.get(value)
                        case 1:
                            program_name=PMD_SOUNDFONT2.get(value)
                        case 2:
                            program_name=PMD_SOUNDFONT3.get(value)
                        case 3:
                            program_name=PMD_SOUNDFONT4.get(value)
                        case 4:
                            program_name=PMD_SOUNDFONT5.get(value)
                        case _:
                            print("A bank value set in the file does not match with the PMD soundfont.\nPerhaps the soundfont option was added by mistake.\n Please try again without that option.")
                            sys.exit(1)
                # if the pmd-soundfont flag is not set, the General MIDI soundfont instruments names are used
                else:
                    program_name = GM_SOUNDFONT.get(value)
                
                # the preset value set for the instrument change is based on:
                # - what instruments were declared prior
                # long story short: we set ID's from 0 to n for each presets (n being the amount of presets in the song)
                # upon their use in the song. The first preset used will have an ID of 0 and so on.
                # Here we check if the preset was used prior (e.g by another track)
                # and if that's the case, give it the same ID
                # if the preset is used here for the first time, we give a new ID
                # a preset is recognised through both it's bank and patch.
                # two presets of same patch but different bank (and vice-versa) are considered different.
                swd_soundfont = next((i for i in range(len(programs_list)) if programs_list[i][1] == program_name),len(programs_list))
                nawa = (current_bank,program_name)
                if programs_list.count(nawa) == 0:
                    programs_list.append(nawa)
                smb_descriptor.write(swd_soundfont.to_bytes(1,'little'))
                position+=2
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
                position,note,octave_mod,new_octave = convert_note(smb_descriptor,midi_note,current_octave,position)
                current_octave = new_octave
                if(current_octave > 9 or current_octave <-1):
                    print("The octave value went out of bounds")
                    sys.exit(1)

                key_down = int(parts[4][9:])#int(math.ceil(int(parts[4][9:])/factor))
                if len(hex(key_down))> 8: # That's a problem (> 0xyyyyyy)
                    print("Format limitation: a key_hold duration is above what the .smd standard can muster.(?)")
                    sys.exit(1)
                elif len(hex(key_down)) > 6: # > 0xyyyy
                    key_duration = key_down.to_bytes(3,'big')
                    nb_param = 0x03
                elif len(hex(key_down)) > 4:# > 0xyy
                    key_duration = key_down.to_bytes(2,'big')
                    nb_param = 0x02
                elif key_down != 0:
                    key_duration = key_down.to_bytes(1,'big')
                    nb_param = 0x01
                else:
                    key_duration = 0
                    nb_param = 0x00
                note_data = (note | (octave_mod << 4) | (nb_param << 6))
                smb_descriptor.write(velocity.to_bytes(1,'little'))
                smb_descriptor.write(note_data.to_bytes(1,'little'))
                position += 2
                if key_duration != 0:
                    smb_descriptor.write(key_duration)
                    position += nb_param
                # key note velocity
            case _:
                print(f"parse error: {instruction} instruction not recognised")
    length = song_duration - master_clock
    if length < 0:
        print('Bad instruction file: the song duration given is less than the one found in the tracks.')
        sys.exit(1)
    position,last_pause = add_wait_time(smb_descriptor,length,last_pause,position)
    smb_descriptor.write(b'\x98')
    position += 1
    padding = get_padding(position,4)
    for i in range(padding):
        smb_descriptor.write(b'\x98')
    print("done.")
    return programs_list

def generate_eoc_chunk(file):
    file.write(b'\x65\x6F\x63\x20') # trk
    file.write(b'\x00\x00\x00\x01')
    file.write(b'\x04\xFF\x00\x00')
    file.write(b'\x00\x00\x00\x00') # length of chunk

def main():
    args = parse_args()
    if len(args.linkbyte) != 4:
        print("option error: link byte is not of size 4.")
        sys.exit(1)
    try:
        hex(int(args.linkbyte, base=16))
    except Exception as e:
        print("option error: link byte is not of hexadecimal format")
        print(e)
        sys.exit(1)
    dir_path = f'SMDS/{args.output}'
    if not os.path.exists(dir_path):
        print(f"Creating directory {args.output}...")
        os.mkdir(dir_path)
    file_name = dir_path + f'/{args.output}.smd'
    with open(file_name,"wb") as file:
        nb_channel = 16
        with open('MIDI_TXT/' + args.input,"r") as midi:
            generate_header_chunk(file,args.linkbyte)
            nbrtrk,tpqn,song_duration =generate_song_chunk(file,midi,nb_channel)
            programs_list = []
            for i in range(nbrtrk):#hmmmm....
                programs_list = generate_track(file,midi,i,args.linkbyte,programs_list,args.pmd_soundfont,song_duration)
            generate_eoc_chunk(file)
    with open(file_name, 'rb') as patch:
        length = 0
        length_list = []
        midi_parse_bytes(patch,128)
        length += 128
        track = midi_parse_bytes(patch,4)
        length += 4
        while(track == 0x74726b20):
            midi_parse_bytes(patch,12)
            length += 12
            track_length = 0
            byte = midi_parse_bytes(patch,1)
            track_length += 1
            while(byte != 0x98):
                byte = midi_parse_bytes(patch,1)
                track_length+=1
                if byte <= 0x7F:
                    note_data = midi_parse_bytes(patch,1)
                    nb_param = note_data >> 6
                    track_length+= nb_param + 1
                    midi_parse_bytes(patch,nb_param)
                elif byte >= 0x90:
                    to_parse = EVENTS.get(byte)
                    midi_parse_bytes(patch,to_parse)
                    track_length+= to_parse
            length_list.append(track_length)
            length += track_length
            padding = get_padding(length,4)
            midi_parse_bytes(patch,padding)
            length += padding
            track = midi_parse_bytes(patch,4)
            length += 4

    length +=12 # 12 byte for eoc chunk (without magic already read.)
    with open(file_name, 'rb+') as fix_length:
        midi_parse_bytes(fix_length,8)
        fix_length.write(length.to_bytes(4,'little'))
        midi_parse_bytes(fix_length,64) # ?
        midi_parse_bytes(fix_length,64)
        pos = 140
        for i in length_list:
            fix_length.write(i.to_bytes(4,'little'))
            pos += 4
            midi_parse_bytes(fix_length,i+12)
            pos += (i+12)
            padding = get_padding(pos,4)
            midi_parse_bytes(fix_length,padding)
            pos += padding

    print(f"\nThe SMD file {args.output}.smd was generated.")
    print("Generating a JSON for SWD configuration...")

    test_list = []
    for elem in programs_list:
        bank,soundfont = elem
        test_dict = {"name" : soundfont}
        test_list.append(test_dict)

    json_output = {"link_byte": args.linkbyte,
    "presets": test_list}
    with open(dir_path + f"/preset_output.json","w") as json_file:
        json.dump(json_output, json_file, indent=4)
    print('A JSON file was generated.')
    print('########################################################################################')
    print('Default names were already written for the presets used in the song.')
    print('This file is yours to edit by changing the name of the presets used in the SMD file.')
    print('The names of the presets should match the names used on the PMD soundfont.')
    print('After editing the desired presets, execute SWDgen to generate the corresponding SWD file.')
    print('########################################################################################')
if __name__ == "__main__":
    main()

