
import argparse
import os
import sys

from utils import parse_bytes,midi_parse_bytes

def parse_args():
    """ creates the parser of the command line

    Returns:
        Namespace: the values given as arguments in the CLI.
    
    """
    parser = argparse.ArgumentParser(
        prog = "MIDIparse",
        description="Takes a MIDI file as input and prints its instructions on a file in the MIDI_TXT directory"
    )

    parser.add_argument("midi",help="The path to the MIDI file to parse")
    parser.add_argument("output",help="The name of the file to write")
    parser.add_argument("--loop",help="Makes the song loop at a specific time in ticks(?). Defaults to 0 if unspecified.",default=0,type= (int))
    return parser.parse_args()


def parse_header(file_descriptor):
    """ reads the header chunk in a MIDI file.
        Currently can only read format 0 and 1 MIDI files
    Arguments:
        file_descriptor(BufferedReader): the file descriptor
    Returns:
        int: the division value of the track (in beats per quarter note)
    
    """
    length = midi_parse_bytes(file_descriptor,4)
    if length != 6:
        print("parse error: the length of the header chunk is different than 6.")
        sys.exit(1)
    format = midi_parse_bytes(file_descriptor,2)
    if format == 2:
        print(f"version error: the MIDI format {format} is not supported")
        sys.exit(1)
    ntrks = midi_parse_bytes(file_descriptor,2)
    division = midi_parse_bytes(file_descriptor,2)
    if division & 0x800 == 0:
        return ntrks,(division & 0x7FF)
    else:
        print("version error: The division value uses a negative SMPTE format which is not supported.")
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
        byte = midi_parse_bytes(fd,1)
        length = (length << 7) | (byte & 0x7F)
    return length

def make_play_note(key_note,prepro_stack,channel,master_clock):
    """ Matches a NoteOff with a previously stored NoteOn.
        Adds to the text file a PlayNote instruction,
        with the duration of the note.
        If no previous NoteOn happens to match the NoteOff instruction
        (which shouldn't happen) a warning is printed.
    Arguments:
        key_note(): the NoteOff key value, that matches a NoteOn.
        prepro_stack(list): A list of all incomplete NoteOn.
        channel(int): The channel from which the NoteOff belong.
        master_clock(int): the time (in ticks) at which the NoteOff instruction happens
    Returns:
        list: a list of datas needed for a PlayNote instrcution
        (namely the start time, the key note, the velocity,
        the note hold duration, the channel concerned)
    
    """
    endtime = master_clock
    for i in prepro_stack:
        if i[1] == key_note and i[4] == channel:
            duration = endtime - i[0]
            ret = i
            ret[3] = duration
            prepro_stack.remove(i)
            return ret
    print("warning: A NoteOff has not found its sibling in the processed note list")


def add_processed_note(key_note,velocity,channel,master_clock,prepro_stack):
    """ Adds a NoteOn instruction datas in a list, expecting a 
    sibling NoteOff instruction later on the file.
    Arguments:
        key_note(): the NoteOn key value.
        velocity(): the velocity of the NoteOn instruction.
        channel(int): The channel from which the NoteOn belong.
        master_clock(int): the time (in ticks) at which the NoteOn instruction happens
        prepro_stack(list): A list of all incomplete NoteOn.
    """
    duration = 0
    starttime = master_clock
    note = [starttime,key_note,velocity,duration,channel]
    prepro_stack.append(note)

def make_bank_select(value,channel,master_clock,bank_stack):
    """ Matches a ControlChange(32) with a previously stored ControlChange(0).
        Adds to the text file a BankSelect instruction,
        with the bank value changed.
        If no previous ControlChange(0) happens to match the ControlChange(32) instruction
        (which shouldn't happen) a warning is printed.
    Arguments:
        value(): the ControlChange LSB value.
        channel(int): The channel from which the NoteOff belong.
        master_clock(int): the time (in ticks) at which the ControlChange(32) instruction happens
        bank_stack(list): A list of all incomplete ControlChange(0).
    Returns:
        list: a list of datas needed for a PlayNote instrcution
        (namely the start time, the key note, the velocity,
        the note hold duration, the channel concerned)
    
    """
    endtime = master_clock
    for i in bank_stack:
        if i[2] == channel: # hoooopefully that's enough.
            duration = endtime - i[0]
            bank_value = (i[1] << 7) + value
            ret = i
            ret[2] = bank_value
            ret[3] = duration
            bank_stack.remove(i)
            return ret
    print("warning: A Bank Select has not found it's sibling in the processed controller changes.")

def add_bank_select(value,channel,master_clock,bank_stack):
    """ Adds a ControlChange(0) instruction datas in a list, expecting a 
    sibling ControlChange(32) instruction later on the file.
    Arguments:
        value(): the ControlChange MSB value.
        channel(int): The channel from which the ControlChange belong.
        master_clock(int): the time (in ticks) at which the ControlChange instruction happens
        bank_stack(list): A list of all incomplete BankSelects.
    """
    starttime = master_clock
    duration = 0
    bank = [starttime,value,channel,duration]
    bank_stack.append(bank)

def parse_mtrk_event(fd,midi_channel,prepro_stack,bank_stack):
    """ reads from the file descriptor an MTrk event
        It sequentially read first a delta-time and then
        a corresponding sub-event until the end of file (0xFF2F)
    Arguments:
        fd(BufferedReader): the file descriptor

    Returns:
        list(list(string)) -> 16* list string, one for each channel
    """
    # Defaults for starttime, last channel used, last MIDI instruction
    master_clock = 0
    last_channel = 0
    last_event = "NoteOff"
    while(True):
        # reading the waiting time before the instruction
        delta_time = parse_length(fd)
        # advancing master clock
        master_clock += delta_time
        # reading MIDI event
        event_type = midi_parse_bytes(fd,1)
        if event_type == 0xFF: # FF -> META-event
            meta_type = midi_parse_bytes(fd,1)
            event = ""
            # the datas of the event should be read as a string
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
                    midi_parse_bytes(fd,1) # read 0x00
                    return midi_channel,prepro_stack,bank_stack
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
            meta_data = midi_parse_bytes(fd,meta_length)
            if string_flag == True:
                meta_data = hex(meta_data)
            # Putting these Meta Event on a separate channel (17th)
            value = 16 if event == 'Set Tempo' or event == 'Time Signature' or event == 'KeySignature' else 0
            midi_channel[value].append(f"starttime {master_clock}, MetaMessage, type {event}, data {meta_data}")
        elif event_type == 0xF0 or event_type == 0xF7: #F0 / F7 -> Sysex-event
            sysex_length = parse_length(fd)
            sysex_data = midi_parse_bytes(fd,sysex_length)
            midi_channel[0].append(f"starttime {master_clock}, Sysex event, data {sysex_data}")
        elif ((event_type >> 4) == 0x8): # 1000nnnn -> Note Off
            key_note = midi_parse_bytes(fd,1)
            velocity = midi_parse_bytes(fd,1)
            channel = (event_type & 0xF)
            # Finding NoteOff sibling in the stack
            play_note = make_play_note(key_note,prepro_stack,channel,master_clock)
            if play_note is not None:
                (starttime,key,velocity,duration,channel) = play_note
            midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {key_note}, velocity {velocity}, duration {duration}")
            last_event = "NoteOff"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) ==0x9): #1001nnnn -> Note On
            key_note = midi_parse_bytes(fd,1)
            velocity = midi_parse_bytes(fd,1)
            channel = (event_type & 0xF)
            # a NoteOn of velocity 0 is equivalent to a NoteOff.
            if velocity == 0:
                play_note= make_play_note(key_note,prepro_stack,channel,master_clock)
                if play_note is not None:
                    (starttime,key,velocity,duration,channel) = play_note
                midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {key_note}, velocity {velocity}, duration {duration}")
                last_event = "NoteOn"
            else:
                # adding the NoteOn to the stack
                add_processed_note(key_note,velocity,channel,master_clock,prepro_stack)
                last_event = "NoteOn"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xA): #1010nnnn -> Aftertouch
            key_note = midi_parse_bytes(fd,1)
            velocity = midi_parse_bytes(fd,1)
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, Aftertouch, key_note {key_note}, velocity {velocity}")
            last_event = "Aftertouch"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xB): #1011nnnn -> Control Change
            key_note = midi_parse_bytes(fd,1)
            velocity = midi_parse_bytes(fd,1)
            if key_note == 0: # Bank select (MSB)
                add_bank_select(velocity,(event_type & 0xF),master_clock,bank_stack)
            elif key_note == 32:#Bank select (LSB)
                bank = make_bank_select(velocity,(event_type & 0xF),master_clock,bank_stack)
                if bank is not None:
                    (starttime,value,channel,duration) = bank
                midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, BankSelect, bank {value}")
            else:
                midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, ControlChange, key_note {key_note}, velocity {velocity}")
            last_event = "ControlChange"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xC): #1100nnnn -> Program Change
            controller_number = parse_bytes(fd,1)
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, InstrChange, controller_number {controller_number}")
            last_event = "InstrChange"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xD): #1101nnnn -> channel Aftertouch
            pressure_value = midi_parse_bytes(fd,1)
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, Channel Aftertouch, pressure_value {pressure_value}")
            last_event = "Channel Aftertouch"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) == 0xE): #1110nnnn -> Pitch Bend
            least_bytes = midi_parse_bytes(fd,1)
            most_bytes = midi_parse_bytes(fd,1)
            midi_channel[(event_type & 0xF)].append(f"starttime {master_clock}, PitchBend, least_bytes {least_bytes}, most_bytes {most_bytes}")
            last_event = "PitchBend"
            last_channel = event_type & 0xF # not sure if event_type is the same after if clause
        elif ((event_type >> 4) < 0x8): #0xxxnnnn -> after delta-time, bytes with values <= 127 represents the same event as the last one.
            first_part = event_type
            match last_event:
                case "NoteOff":
                    second_part = midi_parse_bytes(fd,1)
                    play_note= make_play_note(first_part,prepro_stack,last_channel,master_clock)
                    if play_note is not None:
                        (starttime,key,velocity,duration,channel) = play_note
                        midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {first_part}, velocity {velocity}, duration {duration}")
                case "NoteOn":
                    second_part = midi_parse_bytes(fd,1)
                    if second_part == 0:
                        play_note = make_play_note(first_part,prepro_stack,last_channel,master_clock)
                        if play_note is not None:
                            (starttime,key,velocity,duration,channel) = play_note
                            midi_channel[channel].append(f"starttime {starttime}, PlayNote, key_note {first_part}, velocity {velocity}, duration {duration}")
                    else:
                        add_processed_note(first_part,velocity,channel,master_clock,prepro_stack)
                case "Aftertouch":
                    second_part = midi_parse_bytes(fd,1)
                    midi_channel[last_channel].append(f"starttime {master_clock}, Aftertouch, key_note {first_part}, velocity {second_part}")
                case "ControlChange":
                    second_part = midi_parse_bytes(fd,1)
                    if first_part == 0: # Bank select (MSB)
                        add_bank_select(second_part,last_channel,master_clock,bank_stack)
                    elif first_part == 32:#Bank select (LSB)
                        bank = make_bank_select(second_part,last_channel,master_clock,bank_stack)
                        if bank is not None:
                            (starttime,value,channel,duration) = bank
                            midi_channel[last_channel].append(f"starttime {master_clock}, BankSelect, bank {value}")
                    else:
                        midi_channel[last_channel].append(f"starttime {master_clock}, ControlChange, key_note {first_part}, velocity {second_part}")
                case "InstrChange":
                    midi_channel[last_channel].append(f"starttime {master_clock}, InstrChange, controller_number {first_part}")
                case "Channel Aftertouch":
                    midi_channel[last_channel].append(f"starttime {master_clock}, Channel Aftertouch, pressure_value {first_part}")
                case "PitchBend":
                    second_part = midi_parse_bytes(fd,1)
                    midi_channel[last_channel].append(f"starttime {master_clock}, PitchBend, least_bytes {first_part}, most_bytes {second_part}")
        else:
            print("parse error: a bad MIDI event was found.")
            sys.exit(1)


def parse_track(file_descriptor,midi_channel,prepro_stack,bank_stack):
    """ reads from the MIDI file the only track in it (intended for format 0 MIDI files)
    Arguments:
        file_descriptor(BufferedReader): the file descriptor

    Returns:
        int: the int value read in big endian
    
    """
    # checking magic number
    magic = file_descriptor.read(4)
    if magic != b'MTrk':
        print(f"parse error: magic word found is not a MIDI track.\n Found:{magic}")
        sys.exit(1)
    # length of track (useless)
    midi_parse_bytes(file_descriptor,4)
    # reading the track
    midi_channel,prepro_stack,bank_stack = parse_mtrk_event(file_descriptor,midi_channel,prepro_stack,bank_stack)
    return midi_channel,prepro_stack,bank_stack


def get_max_duration(instruction):
    """ Finds the time in ticks at which an instruction
    is finished.
    The objective is to find the song duration in ticks.
    Finding the instruction that starts the latest will give us
    the song duration.
    PlayNote instruction are not "instantaneous" in time,
    as they usually hold a note for an amount of time.
    Arguments:
        instruction(string): a MIDI instruction .

    Returns:
        int: the duration in ticks at which the instruction is finished
    
    """
    # getting starttime value
    parts = instruction.split(', ')
    starttime = int(parts[0][10:])
    match parts[1]:
        # a PlayNote instruction holds a note for some time
        # the max duration should takes this time into account
        case "PlayNote":
            key_down = int(parts[4][9:])
        # any other instructions are "instantaneous"
        case _:
            key_down = 0
    return starttime + key_down


def main():
    args = parse_args()
    # checking midi file existence
    if not os.path.exists(args.midi):
        print(f"File {args.midi} is not found")
        sys.exit(1)
    # checking loop option value, as a LoopPoint starttime cannot be negative
    if args.loop < 0:
        print("option error: loop value is negative.")
        sys.exit(1)
    with open(args.midi,"rb") as file:
        #checking MIDI file magic
        magic = file.read(4)
        if magic != b'MThd':
            print("That's not a MIDI file :(")
            sys.exit(1)
        try:
            # reading header chunk
            nb_tracks,division = parse_header(file)
            # 17 lists: one for each 16 channel + the 17th -> stores Tempo parameters.
            midi_channel = [ [],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] 
            # list storing NoteOn instructions
            prepro_stack = []
            #list storing incomplete BankSelect instruction
            bank_stack = []
            # reading each tracks of the file
            for i in range(nb_tracks):
                midi_channel,prepro_stack,bank_stack = parse_track(file,midi_channel,prepro_stack,bank_stack)
            # the number of tracks to write back
            nb_trks = 0
            # counting how many channels are used
            for elem in midi_channel:
                if len(elem)> 0:
                    nb_trks += 1
            file_path = f'MIDI_TXT/{args.output}'
            with open(file_path, "w") as output:
                output.write(f'ntrks {nb_trks}\n')
                output.write(f'tpqn {division}\n')
                song_duration = 0
                # for all 16 channels: (Tempo channel unaffected)
                for i in range(16):
                    list = []
                    # Adding a LoopPoint instruction to used channels
                    if len(midi_channel[i]) > 0:
                        midi_channel[i].append(f'starttime {args.loop}, LoopPoint, ')
                    # getting all starttime values of the channel
                    for statements in midi_channel[i]:
                        parts = statements.split(', ')
                        starttime_value = int(parts[0][10:])
                        list.append(starttime_value)
                    # sorting the channel instruction by starttime order (asc)
                    ordered_list = zip(list,midi_channel[i])
                    midi_sorted = [x for _, x in sorted(ordered_list)]
                    midi_channel[i] = midi_sorted
                    #getting last instruction of the channel, in order to find the longest time.
                    if len(midi_channel[i])>0:
                        song_duration = max(song_duration,get_max_duration(midi_channel[i][-1]))
                # adding song duration
                output.write(f'song_duration {song_duration}\n')
                output.write('\n')
                # adding "Tempo channel" first
                for statements in midi_channel[16]:
                    output.write(statements + '\n')
                # adding all other channels next.
                for j in range(16):
                    if len(midi_channel[j]) != 0:
                        output.write('\n')
                        for statements in midi_channel[j]:
                            output.write(statements + '\n')
        except Exception as e:
            print( "an exception has occured:")
            print(e)

if __name__ == "__main__":
    main()

