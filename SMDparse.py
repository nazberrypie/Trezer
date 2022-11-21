
import argparse
import os
import sys
import time


def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "Trezer",
        description="Takes a SMD file as input and prints its functions"
    )

    parser.add_argument("SMD",help="The path to the SMD file to parse")
    parser.add_argument("--check",help="checks if the format of the SMD file is correct",action="store_true")
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
    return int.from_bytes(something,byteorder="big",signed=False)

def parse_little_bytes(fd,bytes_count):
    """ reads from the file descriptor an amount of bytes
    Arguments:
        fd(BufferedReader): the file descriptor
        bytes_count(int): the amount of bytes to read

    Returns:
        int: the int value read in little endian
    
    """
    something = fd.read(bytes_count)
    return int.from_bytes(something,byteorder="little",signed=False)



def parse_header(file_descriptor):
    """ reads the header chunk in a SMD file.
        Currently can only read format 0 SMD files
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int: the division value of the track (in beats per quarter note)
    
    """
    parse_bytes(file_descriptor,4)# 4 bytes of zeroes
    length = parse_bytes(file_descriptor,4)# file length in bytes
    parse_bytes(file_descriptor,2)# Version number?
    parse_bytes(file_descriptor,2)# two unknown bytes
    parse_bytes(file_descriptor,8)# 4 bytes of zeroes (twice)
    parse_bytes(file_descriptor,2)# last modified (year)
    parse_bytes(file_descriptor,1)# last modified (month)
    parse_bytes(file_descriptor,1)# last modified (day)
    parse_bytes(file_descriptor,1)# last modified (hour)
    parse_bytes(file_descriptor,1)# last modified (minute)
    parse_bytes(file_descriptor,1)# last modified (second)
    parse_bytes(file_descriptor,1)# last modified (centisecond)??
    parse_bytes(file_descriptor,16)# file name (ASCII null-terminated string. Extra space after the 0 on the total 16 bytes is padded with 0xAA)??
    parse_bytes(file_descriptor,16)# four unkown set of 4 bytes??


NOTES ={    0x0: "C", 0x1: "C#", 0x2 : "D",
            0x3: "D#", 0x4: "E", 0x5 : "F",
            0x6: "F#", 0x7: "G", 0x8 : "G#",
            0x9: "A", 0xA: "A#", 0xB : "B",
            0xF: "unknown"
}

DURATION ={     0x80: 96, 0x81: 72, 0x82 : 64,
                0x83: 48, 0x84: 36, 0x85 : 32,
                0x86: 24, 0x87: 18, 0x88 : 16,
                0x89: 12, 0x8A: 9, 0x8B : 8,
                0x8C: 6, 0x8D: 4, 0x8E : 3,
                0x8F: 2
}

# EVENTS -> ["name of event",number of argument bytes]
EVENTS = {  0x90: ["RepeatLastPause",0], 0x91: ["AddToLastPause",1], 0x92 : ["Pause8Bits",1], 0x93: ["Pause16Bits",2],
            0x94: ["Pause24Bits",3], 0x95 : ["PauseUntilRelease",1], 0x98: ["EndOfTrack",0], 0x99: ["LoopPoint",0],
            0xA0 : ["SetTrackOctave",1], 0xA1: ["AddToTrackOctave",1], 0xA4: ["SetTempo",1], 0xA5 : ["SetTempo",1],# SetTempo is intentionnaly putted twice here
            0xAB: ["SkipNextByte",0], 0xAC: ["SetProgram",1], 0xCB : ["SkipNext2Bytes",0], 0xD7: ["PitchBend",2],
            0xE0: ["SetTrackVolume",1], 0xE3: ["SetTrackExpression",1],0xE8 : ["SetTrackPan",1], 0xF8: ["SkipNext2Bytes2",0],
    # Unknown but used
            0x9C: ["9C ->???",1], 0x9D: ["9D ->???",1], 0x9E: ["9E ->???",1], 0xA8: ["A8 ->???",2],
            0xA9: ["A9 -> ???",1], 0xAA: ["AA -> ???",1], 0xAF: ["AF -> ???",3], 0xB0: ["B0 -> ???",0],
            0xB1: ["B1 -> ???",1], 0xB2: ["B2 -> ???",1], 0xB3: ["B3 -> ???",1], 0xB4: ["B4 -> ???",2],
            0xB5: ["B5 -> ???",1], 0xB6: ["B6 -> ???",1], 0xBC: ["BC -> ???",1], 0xBE: ["BE -> ???",2],
            0xBF: ["BF -> ???",1], 0xC0: ["C0 -> ???",1], 0xC3: ["C3 -> ???",1], 0xD0: ["D0 -> ???",2],
            0xD1: ["D1 -> ???",1], 0xD2: ["D2 -> ???",1], 0xD3: ["D3 -> ???",2], 0xD4: ["D4 -> ???",3],
            0xD5: ["D5 -> ???",2], 0xD6: ["D6 -> ???",2], 0xD8: ["D8 -> ???",2], 0xDB: ["DB -> ???",1],
            0xDC: ["DC -> ???",5], 0xDD: ["DD -> ???",4], 0xDF: ["DF -> ???",1], 0xE1: ["E1 -> ???",1],
            0xE2: ["E2 -> ???",3], 0xE4: ["E4 -> ???",5], 0xE5: ["E5 -> ???",4], 0xE7: ["E7 -> ???",1],
            0xE9: ["E9 -> ???",1], 0xEA: ["EA -> ???",3], 0xEC: ["EC -> ???",5], 0xED: ["ED -> ???",4],
            0xEF: ["EF -> ???",1], 0xF0: ["F0 -> ???",5], 0xF1: ["F1 -> ???",4], 0xF2: ["E1 -> ???",2],
            0xF3: ["F3 -> ???",3], 0xF6: ["F6 -> ???",1],
    # Any other 0x (0x90 -> 0xFF) are considered INVALID
            0x96: ["INVALID",0], 0x97: ["INVALID",0], 0x9A: ["INVALID",0], 0x9B: ["INVALID",0],
            0x9F: ["INVALID",0], 0xA2: ["INVALID",0], 0xA3: ["INVALID",0], 0xA6: ["INVALID",0],
            0xA7: ["INVALID",0], 0xAD: ["INVALID",0], 0xAE: ["INVALID",0], 0xB7: ["INVALID",0],
            0xB8: ["INVALID",0], 0xB9: ["INVALID",0], 0xBA: ["INVALID",0], 0xBB: ["INVALID",0],
            0xBD: ["INVALID",0], 0xC1: ["INVALID",0], 0xC2: ["INVALID",0], 0xC4: ["INVALID",0],
            0xC5: ["INVALID",0], 0xC6: ["INVALID",0], 0xC7: ["INVALID",0], 0xC8: ["INVALID",0],
            0xC9: ["INVALID",0], 0xCA: ["INVALID",0], 0xCC: ["INVALID",0], 0xCD: ["INVALID",0],
            0xCE: ["INVALID",0], 0xCF: ["INVALID",0], 0xD9: ["INVALID",0], 0xDA: ["INVALID",0],
            0xDE: ["INVALID",0], 0xE6: ["INVALID",0], 0xEB: ["INVALID",0], 0xEE: ["INVALID",0],
            0xF4: ["INVALID",0], 0xF5: ["INVALID",0], 0xF7: ["INVALID",0], 0xF9: ["INVALID",0],
            0xFA: ["INVALID",0], 0xFB: ["INVALID",0], 0xFC: ["INVALID",0], 0xFD: ["INVALID",0],
            0xFE: ["INVALID",0], 0xFF: ["INVALID",0]
}


def parse_event(fd,chunk_length):
    """ reads from the file descriptor an MTrk event
        It sequentially read first a delta-time and then
        a corresponding sub-event until the end of file (0xFF2F)
    Arguments:
        fd(BufferedReader): the file descriptor

    Returns:
        list(list(string)) -> 16* list string, one for each channel
    """
    position =0
    while(True):
        event_type = parse_bytes(fd,1)
        position +=1
        print(hex(event_type))
        if event_type <= 0x7F: # 0x0 to 0x7F -> PlayNote
            note_data = parse_bytes(fd,1)
            position += 1
            nb_param = (note_data & 0xC0) >> 6
            if nb_param > 3:
                print(f"parse error: byte number {fd.tell()} the number of parameters for a PlayNote was {nb_param}, above 3.")
            octave_mod = (note_data & 0x30) >> 4
            if octave_mod > 3:
                print(f"parse error: byte number {fd.tell()} the octave mod for a PlayNote was {octave_mod}, above 3.")
            note = (note_data & 0xF)
            if octave_mod > 15:
                print(f"parse error: byte number {fd.tell()} the Note for a PlayNote was {note}, above 15.")
            key_down_dur = parse_little_bytes(fd,nb_param) # dunno if big or little endian?
            position += nb_param
            octave_shift = octave_mod - 2
            note = NOTES.get(note)
            print(f"PlayNote, OctaveShift{octave_shift}, note{note}, hold down {key_down_dur}")
        elif event_type > 0x7F and event_type <= 0x8F: # 0x80 to 0x8F -> duration pause events
            duration = DURATION.get(event_type)
            print(f"DurationPause {duration} Ticks")
        else: # 0x90 to 0xFF -> unique event
            if event_type == 0x98:
                padding = (4 - (position % 4))% 4
                print(f"### position : {position} padding: {padding}")
                parse_bytes(fd,padding)
                return 
            else:
                event_name,arguments = EVENTS.get(event_type)
                parse_bytes(fd,arguments)
                position += arguments
                print(f"Event {event_name}, arg {arguments}")


def parse_preamble(file_descriptor,chunk_length):
    track_id = parse_bytes(file_descriptor,1)
    channel_id = parse_bytes(file_descriptor,1)
    parse_bytes(file_descriptor,1) # unknown
    parse_bytes(file_descriptor,1) # unknown
    chunk_length = chunk_length -4
    parse_event(file_descriptor,chunk_length)
    return


def parse_track(file_descriptor,ticks_per):
    """ reads from the SMd file the only track in it (intended for format 0 SMD files)
    Arguments:
        file_descriptor(BufferedReader): the file descriptor

    Returns:
        int: the int value read in big endian
    
    """
    magic = parse_bytes(file_descriptor,4)
    if magic != 0x74726B20:
        print("parse error: magic word found is not a SMD track")
        sys.exit(1)
    parse_bytes(file_descriptor,4)
    parse_bytes(file_descriptor,4)
    chunk_length = parse_little_bytes(file_descriptor,4)
    parse_preamble(file_descriptor,chunk_length)


def parse_song_chunk_header(file_descriptor):
    parse_bytes(file_descriptor,4) # "song" chunk label
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,2) # unknown
    tpqn = parse_bytes(file_descriptor,2) # ticks per quarter note?? (Aparently, it works like MIDI clock ticks, which should be a good thing)
    parse_bytes(file_descriptor,2) # unknown
    nb_track = parse_bytes(file_descriptor,1) # number of track chunks
    nb_channel = parse_bytes(file_descriptor,1) # number of channels (the doc is unsure on how channel works in DSE)
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,2) # unknown
    parse_bytes(file_descriptor,2) # unknown
    parse_bytes(file_descriptor,4) # unknown
    parse_bytes(file_descriptor,16) # unknown/possibly padding
    return tpqn,nb_track,nb_channel

def main():
    args = parse_args()
    if (args.check == True):
        print("check flag detected")
    if not os.path.exists(args.SMD):
        print(f"File {args.SMD} is not found")
        sys.exit(1)
    with open(args.SMD,"rb") as file:
        magic = file.read(4)
        if magic != b'smdl':
            print("parse errpr: The magic number read indicates the file is not of the .smd format")
            sys.exit(1)
        try:
            parse_header(file)
            ticks_per_quarter,nb_track,nb_channel = parse_song_chunk_header(file)
            print(f"nb_track {nb_track} nb_channel {nb_channel}")
            for i in range(nb_track):
                print("##########\nTrack " + str(i) + "\n##########")
                parse_track(file,ticks_per_quarter)



        except Exception as e:
            print( "an exception has occured" + e)
if __name__ == "__main__":
    main()

