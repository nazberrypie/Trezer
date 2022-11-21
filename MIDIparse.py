
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
        description="Takes a MIDI file as input and prints its functions"
    )

    parser.add_argument("midi",help="The path to the MIDI file to parse")
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

def parse_header(file_descriptor):
    """ reads the header chunk in a MIDI file.
        Currently can only read format 0 MIDI files
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int: the division value of the track (in beats per quarter note)
    
    """
    length = parse_bytes(file_descriptor,4)
    if length != 6:
        print("parse error: the length of the header chunk is different than 6.")
        sys.exit(1)
    format = parse_bytes(file_descriptor,2)
    if format == 2:
        print(f"version error: the MIDI format {format} is not supported")
        sys.exit(1)
    ntrks = parse_bytes(file_descriptor,2)
    # if ntrks != 1:
    #     print(f"parse error: The MIDI file contains {ntrks} tracks despite being format 0 (can only have 1 track)")
    #     sys.exit(1)
    print (f'ntrks {ntrks}')
    division = parse_bytes(file_descriptor,2)
    if division & 0x800 == 0:
        #print("ticks per quarter, yay!")
        return ntrks,(division & 0x7FF)
    else:
        print("negative SMPTE oh boy.")
        sys.exit(1)
    
def parse_length(fd):
    """ reads from the file descriptor length bytes
    giving the length of bytes to read afterwards
    Arguments:
        fd(BufferedReader): the file descriptor

    Returns:
        int: the length read

    """
    length = 0x0
    byte = 0xFF
    while(byte & 0x80 != 0):
        byte = parse_bytes(fd,1)
        #position -= 1
        # print(hex(byte))
        length = (length << 7) | (byte & 0x7F) # 7 or 2?
         # print(f"byt_length : {byte}")
    return length

def make_play_note(key_note,prepro_stack,master_clock):
    endtime = master_clock
    for i in prepro_stack:
        if i[1] == key_note:
            duration = endtime - i[0]
            ret = i
            ret[3] = duration
            prepro_stack.remove(i)
            return ret
    print("warning: A NoteOff has not found its sibling in the processed note list")


def add_processed_note(key_note,velocity,channel,master_clock,prepro_stack):
    #print(velocity)
    duration = 0
    starttime = master_clock
    note = [starttime,key_note,velocity,duration,channel]
    prepro_stack.append(note)

def parse_mtrk_event(fd,midi_channel,prepro_stack):
    """ reads from the file descriptor an MTrk event
        It sequentially read first a delta-time and then
        a corresponding sub-event until the end of file (0xFF2F)
    Arguments:
        fd(BufferedReader): the file descriptor

    Returns:
        list(list(string)) -> 16* list string, one for each channel
    """
    master_clock = 0
    test = 0
    last_channel = 0
    last_event = "NoteOff"
    while(True):
        delta_time = parse_length(fd)
        master_clock += delta_time
        event_type = parse_bytes(fd,1)
        #track_length -=1
        if event_type == 0xFF: # FF -> META-event
            meta_type = parse_bytes(fd,1)
            #track_length -=1
            event = ""
            string_flag = False
            match meta_type:
                case 0x00:
                    event = "Sequence Number"
                case 0x01:
                    event = "Text Event"
                    string_flag = True
                case 0x02:
                    event = "Copyright Notice"
                    string_flag = True
                case 0x03:
                    event = "Track Name"
                    string_flag = True
                case 0x04:
                    event = "Instrument Name"
                    string_flag = True
                case 0x05:
                    event = "Lyric"
                    string_flag = True
                case 0x06:
                    event = "Marker"
                    string_flag = True
                case 0x07:
                    event = "Cue Point"
                    string_flag = True
                case 0x20:
                    event = "MIDI Channel Prefix"
                case 0x2F: # End of Track
                    parse_bytes(fd,1) # read 0x00
                    return midi_channel,prepro_stack
                case 0x51:
                    event = "Set Tempo"
                case 0x54:
                    event = "SMPTE Offset"
                case 0x58:
                    event = "Time Signature"
                case 0x59:
                    event = "Key Signature"
                case 0x7F:
                    event = "Sequencer Specific Meta-Event"
                case _:
                    event = "unknown"
            meta_length = parse_length(fd)
            meta_data = parse_bytes(fd,meta_length)
            if string_flag == True:
                meta_data = hex(meta_data)
                meta_data = bytearray.fromhex(meta_data[2:]).decode()
            #track_length -= meta_length
            value = 16 if event == 'Set Tempo' or event == 'Time Signature' or event == 'KeySignature' else 0
            midi_channel[value].append(f"starttime {master_clock}, MetaMessage, type {event}, data {meta_data}")
        elif event_type == 0xF0 or event_type == 0xF7: #F0 / F7 -> Sysex-event
            sysex_length = parse_length(fd)
            sysex_data = parse_bytes(fd,sysex_length)
            #track_length -=sysex_length
            midi_channel[0].append(f"starttime {master_clock}, Sysex event, data {sysex_data}")
        elif ((event_type >> 4) == 0x8): # 1000nnnn -> Note Off
            key_note = parse_bytes(fd,1)
            velocity = parse_bytes(fd,1)
            #track_length -=2
            play_note = make_play_note(key_note,prepro_stack,master_clock)
            if play_note is not None:
                (starttime,key,velocity,duration,channel) = play_note
            midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {key_note}, velocity {velocity}, duration {duration}")
            last_event = "NoteOff"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) ==0x9): #1001nnnn -> Note On
            key_note = parse_bytes(fd,1)
            velocity = parse_bytes(fd,1)
            channel = (event_type & 0xF)
            #track_length -=2
            if velocity == 0:
                play_note= make_play_note(key_note,prepro_stack,master_clock)
                if play_note is not None:
                    (starttime,key,velocity,duration,channel) = play_note
                midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {key_note}, velocity {velocity}, duration {duration}")
                last_event = "NoteOn"
            else:
                add_processed_note(key_note,velocity,channel,master_clock,prepro_stack)
                #midi_channel[(event_type & 0xF)].append(f"length {delta_time}, NoteOn, key_note {key_note}, velocity {velocity}")
                last_event = "NoteOn"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xA): #1010nnnn -> Aftertouch
            key_note = parse_bytes(fd,1)
            velocity = parse_bytes(fd,1)
            #track_length -=2
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, Aftertouch, key_note {key_note}, velocity {velocity}")
            last_event = "Aftertouch"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xB): #1011nnnn -> Control Change
            key_note = parse_bytes(fd,1)
            velocity = parse_bytes(fd,1)
            #track_length -=2
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, ControlChange, key_note {key_note}, velocity {velocity}")
            last_event = "ControlChange"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xC): #1100nnnn -> Program Change
            controller_number = parse_bytes(fd,1)
            #parse_bytes(fd,1) # thebyte is unused???
            #track_length -=2
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, ProgramChange, controller_number {controller_number}")
            last_event = "ProgramChange"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xD): #1101nnnn -> channel Aftertouch
            pressure_value = parse_bytes(fd,1)
            #parse_bytes(fd,1) # the byte is unused
            #track_length -=2
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, Channel Aftertouch, pressure_value {pressure_value}")
            last_event = "Channel Aftertouch"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xE): #1110nnnn -> Pitch Bend
            least_bytes = parse_bytes(fd,1)
            most_bytes = parse_bytes(fd,1)
            #track_length -=2
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, PitchBend, least_bytes {least_bytes}, most_bytes {most_bytes}")
            last_event = "PitchBend"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) < 0x8): #0xxxnnnn -> after delta-time, bytes with values <= 127 represents the same event as the last one.
            # print("case scenario based on last event type?")
            first_part = event_type
            match last_event:
                case "NoteOff":
                    second_part = parse_bytes(fd,1)
                    play_note= make_play_note(first_part,prepro_stack,master_clock)
                    if play_note is not None:
                        (starttime,key,velocity,duration,channel) = play_note
                        midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {first_part}, velocity {velocity}, duration {duration}")
                case "NoteOn":
                    second_part = parse_bytes(fd,1)
                    #track_length -=1
                    if second_part == 0:
                        play_note = make_play_note(first_part,prepro_stack,master_clock)
                        if play_note is not None:
                            (starttime,key,velocity,duration,channel) = play_note
                            midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {first_part}, velocity {velocity}, duration {duration}")
                    else:
                        add_processed_note(first_part,velocity,channel,master_clock,prepro_stack)
                        #midi_channel[last_channel].append(f"starttime {master_clock}, NoteOn, key_note {first_part}, velocity {second_part}")
                case "Aftertouch":
                    #track_length -=1
                    second_part = parse_bytes(fd,1)
                    midi_channel[last_channel].append(f"starttime {master_clock}, Aftertouch, key_note {first_part}, velocity {second_part}")
                case "ControlChange":
                    #track_length -=1
                    second_part = parse_bytes(fd,1)
                    midi_channel[last_channel].append(f"starttime {master_clock}, ControlChange, key_note {first_part}, velocity {second_part}")
                case "ProgramChange":
                    midi_channel[last_channel].append(f"starttime {master_clock}, ProgramChange, controller_number {first_part}")
                case "Channel Aftertouch":
                    midi_channel[last_channel].append(f"starttime {master_clock}, Channel Aftertouch, pressure_value {first_part}")
                case "PitchBend":
                    #track_length -=1
                    second_part = parse_bytes(fd,1)
                    midi_channel[last_channel].append(f"starttime {master_clock}, PitchBend, least_bytes {first_part}, most_bytes {second_part}")
        else:
            print("parse error: a bad MIDI event was found.")
            sys.exit(1)


def parse_track(file_descriptor,position,midi_channel,prepro_stack):
    """ reads from the MIDI file the only track in it (intended for format 0 MIDI files)
    Arguments:
        file_descriptor(BufferedReader): the file descriptor

    Returns:
        int: the int value read in big endian
    
    """
    magic = file_descriptor.read(4)
    # print(magic)
    if magic != b'MTrk':
        print(magic)
        print("parse error: magic word found is not a MIDI track")
        sys.exit(1)
    track_length = parse_bytes(file_descriptor,4)
    # print(track_length)
    position +=8
    midi_channel,prepro_stack = parse_mtrk_event(file_descriptor,midi_channel,prepro_stack)
    return midi_channel,prepro_stack
    # cpt = 0
    # for channel in midi_channel:
    #     if len(channel) != 0:
    #         print(f"###########\n#channel {cpt}:\n############")
    #         for statements in channel:
    #             print(statements)
    #     cpt += 1



def main():
    args = parse_args()
    position = 0
    if (args.check == True):
        print("check flag detected")
    if not os.path.exists(args.midi):
        print(f"File {args.midi} is not found")
        sys.exit(1)
    with open(args.midi,"rb") as file:
        magic = file.read(4)
        # print(magic)
        if magic != b'MThd':
            print("Thats not a MIDI file :(")
            sys.exit(1)
        try:
            position += 4
            nb_tracks,division = parse_header(file) # verifies the MIDI correctness (format 0,one track) and returns the division (ticks per quarter note)
            print(f'tpqn {division}')
            print('')
            position += 10
            midi_channel = [ [],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] # 17 lists: one for each 16 channel + the 17th -> stores Tempo parameters.
            prepro_stack = []
            # cpt = 0
            # for channel in midi_channel:
            #     if len(channel) != 0:
            #         print(f"###########\n#channel {cpt}:\n############")
            for i in range(nb_tracks):
                midi_channel,prepro_stack = parse_track(file,position,midi_channel,prepro_stack)
                #print("\n\n NEW_TRACK \n\n")
            for statements in midi_channel[16]:
                print(statements)
            for i in range(16):
                list = []
                for statements in midi_channel[i]:
                    parts = statements.split(', ')
                    starttime_value = int(parts[0][10:])
                    list.append(starttime_value)
                ordered_list = zip(list,midi_channel[i])
                midi_sorted = [x for _, x in sorted(ordered_list)]
                midi_channel[i] = midi_sorted
            for j in range(16):
                print('')
                for statements in midi_channel[j]:
                    print(statements)

        except Exception as e:
            print( "an exception has occured" + e)
if __name__ == "__main__":
    main()

