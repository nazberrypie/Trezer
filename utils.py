def parse_bytes(fd,bytes_count):
    """ Reads from the file descriptor an amount of bytes (in little endian)
    Arguments:
        fd(BufferedReader): the file descriptor
        bytes_count(int): the amount of bytes to read

    Returns:
        int: the int value read in little endian
    
    """
    something = fd.read(bytes_count)
    return int.from_bytes(something,byteorder='little',signed=False)

def midi_parse_bytes(fd,bytes_count):
    """ reads from the file descriptor an amount of bytes (in big endian)
    Arguments:
        fd(BufferedReader): the file descriptor
        bytes_count(int): the amount of bytes to read

    Returns:
        int: the int value read in big endian
    
    """
    something = fd.read(bytes_count)
    return int.from_bytes(something,byteorder="big",signed=False)

def get_padding(value,base):
    """ calculate the amount of padding bytes to add from a position.
    If we have a position of 30, and need to align on 16 bytes,
    we need to add 2 padding bytes to be aligned on 16 (32 -> 2*16).
    Arguments:
        value(int): the position we are in
        base(int): the amount of bytes to align to

    Returns:
        int: the amount of paddingbytes to add
    
    """
    return (base - (value % base))%base

# an ugly way to rip the orignal SWD files. 
# (file number,preset ID) -> (bgm{file_number}.swd) ID being the ID of the preset in said file.
# The numbers may be incorrect: some presets despite being the "same" instrument
# does not always declare all the samples (probably for optimisation)
# unmapped soundfonts (not found in the BGM repo) holds a file_number of -1
FETCH_SOUNDFONT = { 
    (164,0x4): "Piano", (49,0x3): "Piano Bass", (3,0x1):"Electric Piano", (41,0x3): "Tine E-Piano", (86,0x3):"FM E-Piano",
    (3,0xE): "Harpsichord 1", (-1,0):"Harpsichord 2", (16,0x61): "Celeste", (3,0x7):"Glockenspiel 1", (6,0x4): "Glockenspiel 2",
    (12,0xA):"Music Box", (22,0x6): "Vibraphone", (23,0x5):"Marimba", (39,0xC): "Tubular Bells", (50,0xF):"Fantasia 1",
    (74,0x3): "Fantasia 2", (74,0x1):"Synth Mallet", (81,0x2C): "Percussive Organ", (64,0x8):"Synth Organ", (71,0x3): "Melodica",
    (136,0x1B):"Finger Bass", (47,0x1C): "Pick Bass", (85,0x8):"J-Bass", (160,0x1D): "Slap Bass", (-1,0):"Bass Harmonics",
    (5,0x19): "Synth Bass 1", (10,0x1A):"Synth Bass 2", (-1,0): "Synth Bass 3", (3,0x14):"Nylon Guitar", (9,0x17): "Steel Guitar",
    (84,0xA):"Mandolin", (99,0x16): "Overdriven Guitar", (178,0x16):"Distorted Guitar", (-1,0): "Guitar Harmonics", (23,0x54):"Sitar",
    (56,0x8): "Banjo", (58,0xB):"Harp", (142,0x49): "Cello", (16,0x4A):"Bass Section", (16,0x48): "Violin 1",
    (-1,0):"Violin 2", (85,0x48): "Violins", (69,0x48):"Viola", (9,0x2E): "Viola Section", (10,0x1F):"String Section", 
    (12,0x4B): "Pizzicato Strings", (69,0x20):"Synth Strings 1", (74,0xD): "Synth Strings 2", (-1,0):"Orchestral Hit", (14,0x23): "Choir Aahs",
    (21,0x3):"Solo Voice", (69,0x24): "Voice Tenor", (193,0x0):"Voice Oohs", (16,0x44): "Trumpet Section", (56,0x10):"Solo Trumpet 1",
    (-1,0): "Solo Trumpet 2", (-1,0):"Muted Trumpet", (1,0x3E): "Trombone", (1,0x3F):"Tuba", (173,0x42): "Saxophone",
    (175,0x44):"Brass Section", (1,0x3B): "Brass 1", (13,0x3D):"Brass 2", (22,0x52): "Brass 3", (90,0x42):"Brass 4",
    (123,0x40): "Horn Section", (140,0x40):"French Horn", (17,0x43): "French Horns 1", (156,0x42):"French Horns 2", (69,0x34): "English Horn",
    (-1,0):"Horns", (167,0x41): "Bass & Horn", (1,0x36):"Bassoon 1", (-1,0): "Bassoon 2", (1,0x33):"Flute 1",
    (85,0x33): "Flute 2", (135,0x34):"Oboe 1", (-1,0): "Oboe 2", (1,0x35):"Clarinet", (-1,0): "Hard Clarinet",
    (4,0x51):"Pan Flute", (10,0x51): "Recorder", (25,0x2A):"Bagpipe", (16,0x5E): "Ocarina", (24,0x62):"Synth Sine",
    (178,0x63): "Synth Triangle 1", (-1,0):"Synth Triangle 2", (3,0x61): "Synth Saw", (12,0x60):"Synth Square", (58,0x5C): "Synth Saw-Triangle",
    (161,0x5D):"Synth Distorted", (162,0x5C): "Synth 1", (-1,0):"Synth 2", (15,0x5E): "Synth 3", (138,0x52):"Synth 4",
    (-1,0): "Unused Synth", (1,0x79):"Timpani 1", (-1,0): "Timpani 2", (5,0x53):"Steel Drum", (107,0x10): "Wood Block",
    (64,0x10):"Drop Echo", (9,0x7B): "Pitched Drum", (99,0x7E):"Pitched Crash Cym", (123,0x3): "Pitched Cymbal", (136,0x7C):"Pitched Tamburine",
    (141,0x11): "Pitched Shaker", (136,0x7B):"Pitched Claves", (29,0xD): "FoggyForest Perc", (139,0x6A):"BoulderQuarryPerc", (26,0x41): "B&H Horn",
    (170,0x41):"B&H Bass", (51,0x10): "Fantasia(bgm051)", (108,0x11):"Fantasia(bgm108)", (-1,0):"OrigPercPitch1", (-1,0): "OrigPercPitch2",
    (8,0x7F): "Drumkit(Guild)", (53,0x7F):"Drumkit", (-1,0): "Drumkit Panned"
}

# same as FETCH_SOUNDFONT, but sound effects
FETCH_SOUNDFONT4 = {
    (106,0x0): "SFX Bubble 1", (106,0x1): "SFX Bubble 2", (179,0x0):"SFX Bubble 3", (107,0x12): "SFX Clock", (191,0x0):"SFX Crack 1",
    (191,0x1): "SFX Crack 2", (3,0x3):"SFX Dojo", (127,0x0): "SFX DrkFtrChrd", (183,0x1):"SFX Droplet 1", (183,0x3): "SFX Droplet 2",
    (126,0x3):"SFX Eating", (112,0x1): "SFX Electro 1", (114,0x1):"SFX Electro 2", (114,0x2): "SFX Electro 3", (81,0x74):"SFX Electro 4",
    (115,0x2): "SFX Fire 1", (116,0x1):"SFX Fire 2", (115,0x1): "SFX Fire Pop", (-1,0):"SFX Harpsichord", (188,0x2): "SFX Hiss",
    (112,0x0):"SFX Magic 1", (117,0x1): "SFX Magic 2", (117,0x0):"SFX Magic 3", (118,0x0): "SFX Magic 4", (190,0x2):"SFX Rustling",
    (14,0x65): "SFX Wind Gust", (179,0x1):"SFX Splash", (113,0x2): "SFX Swoosh", (101,0x0):"SFX Thunder", (103,0x0): "SFX Tremor 1",
    (103,0x1):"SFX Tremor 2", (105,0x0): "SFX Tremor 3", (105,0x1):"SFX Tremor 4", (104,0x0): "SFX Tremor 5", (0,0x33):"SFX WaterR 1",
    (186,0x1): "SFX WaterR 2", (186,0x2):"SFX WaterR 3", (190,0x1): "SFX WaterR 4", (190,0x0):"SFX WaterR 5", (0,0x3B): "SFX WaterRSW 1",
    (100,0x1):"SFX WaterS 1", (185,0x2): "SFX WaterS 2", (-1,0):"SFX WaterS 3", (128, 0x0): "SFX WaterSR 1", (125,0x4):"SFX WaterSW 1", 
    (125,0x3): "SFX WaterW 1", (100,0x0):"SFX Wave or Wind 1", (100,0x2): "SFX Wave or Wind 2", (113,0x0):"SFX Wave or Wind 3", (181,0x1): "SFX Wave or Wind 4",
    (189,0x0):"SFX Wind 1", (182,0x2): "SFX Wind 2", (183,0x0):"SFX Wind 3", (107,0x3C): "SFX WindH 1", (107,0x3B):"SFX WindH 2",
    (101,0x2): "SFX WindH 3", (-1,0):"SFX WindH 4", (107,0x3E): "SFX WindH 5", (18,0x3):"SFX WNoise 1", (96,0x6C): "SFX WNoise 2",
    (-1,0):"SFX Crack 3", (-1,0): "SFX Electro 5", (-1,0):"SFX Electro 6", (-1,0): "SFX Explosion", (-1,0):"SFX Magic 5", 
    (-1,0): "SFX Magic 6", (-1,0):"SFX Ringing Noise", (-1,0): "SFX Thunder Far", (104,0x0):"SFX Tremor 5", (-1,0): "SFX Tremor 6",
    (-1,0):"SFX TremOrFire 1", (-1,0): "SFX TremOrFire 2", (-1,0):"SFX unkn", (-1,0): "SFX WaterRW 1", (-1,0):"SFX WaterSR 2",
    (-1,0): "SFX WaterSW 2", (-1,0):"SFX WindH 1", (-1,0): "SFX WindH 1-1", (-1,0):"SFX WNoise 3", (-1,0): "SFX WNoise 4",
    (-1,0):"SFX Brass5th"
}

# A dictionnary of the GM MIDI soundfont.
# used by json files to give an idea of what should be used for this preset
# (although PMD Soundfont is better here)
GM_SOUNDFONT = {
    0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano", 2:"Electric Grand Piano", 3: "Honky-tonk Piano", 4:"Electric Piano 1", 
    5: "Electric Piano 2", 6:"Harpsichord", 7: "Clavinet", 8:"Celesta", 9: "Glockenspiel", 10:"Music Box", 11: "Vibraphone", 12:"Marimba", 
    13: "Xylophone", 14:"Tubular Bells", 15: "Dulcimer", 16:"Drawbar Organ", 17: "Percussive Organ", 18:"Rock Organ", 19: "Church Organ", 20:"Reed Organ", 
    21: "Accordion", 22:"Harmonica", 23: "Tango Accordion", 24:"Acoustic Guitar (nylon)", 25: "Acoustic Guitar (steel)", 26:"Electric Guitar (jazz)", 27: "Electric Guitar (clean)", 28:"Electric Guitar (muted)", 
    29: "Overdriven Guitar", 30:"Distortion Guitar", 31: "Guitar harmonics", 32:"Acoustic Bass", 33: "Electric Bass (fingered)", 34:"Electric Bass (picked)", 35: "Fretless Bass", 36:"Slap Bass 1", 
    37: "Slap Bass 2", 38:"Synth Bass 1", 39: "Synth Bass 2", 40:"Violin", 41: "Viola", 42:"Cello", 43: "Contrabass", 44:"Tremolo Strings", 
    45: "Pizzicato Strings", 46:"Orchestral Harp", 47: "Timpani", 48:"String Ensemble 1", 49: "String Ensemble 2", 50:"SynthStrings1", 51: "SynthStrings2", 52:"Choir Aahs", 
    53: "Voice Oohs", 54:"Synth Voice", 55: "Orchestra Hit", 56:"Trumpet", 57: "Trombone", 58:"Tuba", 59: "Muted Trumpet", 60:"French horn", 
    61: "Brass Section", 62:"SynthBrass 1", 63: "SynthBrass 2", 64:"Soprano Sax", 65: "Alto Sax", 66:"Tenor Sax", 67: "Baritone Sax", 68:"Oboe", 
    69: "English Horn", 70:"Bassoon", 71: "Clarinet", 72:"Piccolo", 73: "Flute", 74:"Recorder", 75: "Pan Flute", 76:"Blown Bottle", 
    77: "Shakuhachi", 78:"Whistle", 79: "Ocarina", 80:"Square Wave", 81: "Sawtooth wave", 82:"Calliope", 83: "Chiffer", 84:"Charang", 
    85: "Voice Solo", 86:"Fifths", 87: "Bass + Lead", 88:"Fantasia", 89: "Warm", 90:"Polysynth", 91: "Choir Space Voice", 92:"Bowed Glass", 
    93: "Metallic pro", 94:"Halo", 95: "Sweep", 96:"Rain", 97: "Soundtrack", 98:"Crystal", 99: "Atmosphere", 100:"Brightness", 
    101: "Goblins", 102:"Echoes Drops", 103: "Sci-fi", 104:"Sitar", 105: "Banjo", 106:"Shamisen", 107: "Koto", 108:"Kalimba", 
    109: "Bag pipe", 110:"Fiddle", 111: "Shanai", 112:"Tinkle Bell", 113: "Agogo", 114:"Steel Drums", 115: "Woodblock", 116:"Taiko Drum", 
    117: "Melodic Tom", 118:"Synth Drum", 119: "Reverse Cymbal", 120:"Guitar Fret Noise", 121: "Breath Noise", 122:"Seashore", 123: "Bird Tweet", 124:"Telephone Ring", 
    125: "Helicopter", 126:"Applause", 127: "Gunshot"

}

# A dictionnary of the PMD soundfont
# a one-to-one replica of the StaticR soundfont ID's.
# the idea is perhaps to immediately match soundfonts correctly
# if the MIDI used the StaticR soundfont.
PMD_SOUNDFONT = {
    0: "Piano", 1: "Piano Bass", 2:"Electric Piano", 3: "Tine E-Piano", 4:"FM E-Piano", 
    5: "Harpsichord 1", 6:"Harpsichord 2", 7: "Celeste", 8:"Glockenspiel 1", 9: "Glockenspiel 2", 10:"Music Box", 11: "Vibraphone", 12:"Marimba", 
    13: "Tubular Bells", 14:"Fantasia 1", 15: "Fantasia 2", 16:"Synth Mallet", 17: "Percussive organ", 18:"Synth Organ", 19: "Melodica", 20:"Finger Bass", 
    21: "Pick Bass", 22:"J-Bass", 23: "Slap Bass", 24:"Bass Harmonics", 25: "Synth Bass 1", 26:"Synth Bass 2", 27: "Synth Bass 3", 28:"Nylon Guitar", 
    29: "Steel Guitar", 30:"Mandolin", 31: "Overdriven Guitar", 32:"Distorted Guitar", 33: "Guitar Harmonics", 34:"Sitar", 35: "Banjo", 36:"Harp", 
    37: "Cello", 38:"Bass Section", 39: "Violin 1", 40:"Violin 2", 41: "Violins", 42:"Viola", 43: "Viola Section", 44:"String Section", 
    45: "Pizzicato Strings", 46:"Synth Strings 1", 47: "Synth Strings 2", 48:"Orchestral Hit", 49: "Choir Aahs", 50:"Solo Voice", 51: "Voice Tenor", 52:"Voice Oohs", 
    53: "Trumpet Section", 54:"Solo Trumpet 1", 55: "Solo Trumpet 2", 56:"Muted Trumpet", 57: "Trombone", 58:"Tuba", 59: "Saxophone", 60:"Brass Section", 
    61: "Brass 1", 62:"Brass 2", 63: "Brass 3", 64:"Brass 4", 65: "Horn Section", 66:"French Horn", 67: "French Horns 1", 68:"French Horns 2", 
    69: "English Horn", 70:"Horns", 71: "Bass & Horn", 72:"Bassoon 1", 73: "Bassoon 2", 74:"Flute 1", 75: "Flute 2", 76:"Oboe 1", 
    77: "Oboe 2", 78:"Clarinet", 79: "Hard Clarinet", 80:"Pan Flute", 81: "Recorder", 82:"Bagpipe", 83: "Ocarina", 84:"Synth Sine", 
    85: "Synth Triangle 1", 86:"Synth Triangle 2", 87: "Synth Saw", 88:"Synth Square", 89: "Synth Saw/Triangle", 90:"Synth Distorted", 91: "Synth 1", 92:"Synth 2", 
    93: "Synth 3", 94:"Synth 4", 95: "Unused Synth", 96:"Timpani 1", 97: "Timpani 2", 98:"Steel Drum", 99: "Wood Block", 100:"Drop Echo", 
    101: "Pitched Drum", 102:"Pitched Crash Cym", 103: "Pitched Cymbal", 104:"Pitched Tamburine", 105: "Pitched Shaker", 106:"Pitched Claves", 107: "FoggyForest Perc", 108:"BoulderQuarryPerc", 
    109: "B&H Horn", 110:"B&H Bass", 111: "Fantasia(bgm051)", 112:"Fantasia(bgm108)", 113: "None", 114:"None", 115: "None", 116:"None", 
    117: "None", 118:"None", 119: "None", 120:"OrigPercPitch1", 121: "OrigPercPitch2", 122:"None", 123: "None", 124:"None", 
    125: "Drumkit(Guild)", 126:"Drumkit", 127: "Drumkit Panned"
}

PMD_SOUNDFONT2 = {
    0: "Record Scratch", 1: "String Pad2var.", 2:"Sweeping Drum", 3: "E-Guitar Mix", 4:"Hard Pizzicato", 
    5: "Oboe All Samples", 6:"French Horn 1+2", 7: "Full Orchestra", 8:"Piano Extended", 9: "Superstrings", 10:"Bongo Conga"
}

PMD_SOUNDFONT3 = {
    0: "BassDrum-S", 1: "Bongo", 2:"Clap", 3: "CongaHi", 4:"CongaLo", 
    5: "CongaMu", 6:"Cowbell", 7: "CrashCy1-S", 8:"CrashCy2-S", 9: "CrashCy3-S", 10:"Guiro", 11: "HiAgogo", 12:"HiHatClosed", 
    13: "HiHatOpen", 14:"HiHatPedal", 15: "Kick", 16:"RecScratch-1", 17: "RecScratch-2", 18:"Rim Hit 1", 19: "Rim Hit 2", 20:"Shaker", 
    21: "Shaker2", 22:"Shaker3", 23: "Snare-1", 24:"Snare-2", 25: "Snare-3", 26:"Snare-4", 27: "Snare-5", 28:"Snare-6", 
    29: "Snare-7", 30:"Timbale", 31: "Tom", 32:"TriangleMute", 33: "TriangleOpen", 34:"unknDrum-1", 35: "unknDrum-2", 36:"unknDrum-3", 
    37: "Taiko", 38:"unknDrum-5", 39: "unknDrum-6", 40:"unknDrum-S-1", 41: "unknDrum-S-2", 42:"unknDrum-S-3", 43: "unknDrum-S-4", 44:"Conga 2 hit 1", 
    45: "Conga 2 hit 2", 46:"Conga 2 mute 1", 47: "Conga 2 mute 2", 48:"Tamburine 1", 49: "unknHat-2", 50:"Tamburine 2", 51: "Tamburine 3", 52:"unknHat-S", 
    53: "unknKnock-1", 54:"Wood Block 1", 55: "Piccolo Snare", 56:"Slap 1", 57: "Slap 2", 58:"Wood Block 2", 59: "Clave", 60:"Whistle"
}

PMD_SOUNDFONT4 = {
    0: "SFX Bubble 1", 1: "SFX Bubble 2", 2:"SFX Bubble 3", 3: "SFX Clock", 4:"SFX Crack 1", 
    5: "SFX Crack 2", 6:"SFX Dojo", 7: "SFX DrkFtrChrd", 8:"SFX Droplet 1", 9: "SFX Droplet 2", 10:"SFX Eating", 11: "SFX Electro 1", 12:"SFX Electro 2", 
    13: "SFX Electro 3", 14:"SFX Electro 4", 15: "SFX Fire 1", 16:"SFX Fire 2", 17: "SFX Fire Pop", 18:"SFX Harpsichord", 19: "SFX Hiss", 20:"SFX Magic 1", 
    21: "SFX Magic 2", 22:"SFX Magic 3", 23: "SFX Magic 4", 24:"SFX Rustling", 25: "SFX Wind Gust", 26:"SFX Splash", 27: "SFX Swoosh", 28:"SFX Thunder", 
    29: "SFX Tremor 1", 30:"SFX Tremor 2", 31: "SFX Tremor 3", 32:"SFX Tremor 4", 33: "SFX Tremor 5", 34:"SFX WaterR 1", 35: "SFX WaterR 2", 36:"SFX WaterR 3", 
    37: "SFX WaterR 4", 38:"SFX WaterR 5", 39: "SFX WaterRSW 1", 40:"SFX WaterS 1", 41: "SFX WaterS 2", 42:"SFX WaterS 3", 43: "SFX WaterSR 1", 44:"SFX WaterSW 1", 
    45: "SFX WaterW 1", 46:"SFX Wave or Wind 1", 47: "SFX Wave or Wind 2", 48:"SFX Wave or Wind 3", 49: "SFX Wave or Wind 4", 50:"SFX Wind 1", 51: "SFX Wind 2", 52:"SFX Wind 3", 
    53: "SFX WindH 1", 54:"SFX WindH 2", 55: "SFX WindH 3", 56:"SFX WindH 4", 57: "SFX WindH 5", 58:"SFX WNoise 1", 59: "SFX WNoise 2", 60:"SFX Crack 3", 
    61: "SFX Electro 5", 62:"SFX Electro 6", 63: "SFX Explosion", 64:"SFX Magic 5", 65: "SFX Magic 6", 66:"SFX Ringing Noise", 67: "SFX Thunder Far", 68:"SFX Tremor 5", 
    69: "SFX Tremor 6", 70:"SFX TremOrFire 1", 71: "SFX TremOrFire 2", 72:"SFX unkn", 73: "SFX WaterRW 1", 74:"SFX WaterSR 2", 75: "SFX WaterSW 2", 76:"SFX WindH 1", 
    77: "SFX WindH 1-1", 78:"SFX WNoise 3", 79: "SFX WNoise 4", 80:"SFX Brass5th"
}
PMD_SOUNDFONT5 = {
    0: "Bagpipe 1-C2", 1: "Bagpipe 2-C3", 2:"Bagpipe 3-C4", 3: "Bassoon 1 1-C1", 4:"Bassoon 1 2-C2", 
    5: "Bassoon 1 3-C3", 6:"Brass 2 1-C3", 7: "Brass 2 2-A4", 8:"Brass 2 3-F5", 9: "Brass 3 1-C4", 10:"Brass 3 2-C5", 11: "Choir Aahs 1-C3", 12:"Choir Aahs 2-G3", 
    13: "Choir Aahs 3-G4", 14:"Clarinet 1-C3", 15: "Clarinet 2-C4", 16:"Clarinet 3-C5", 17: "E-Piano 1-C4", 18:"E-Piano 2-C5", 19: "Fantasia 1 1-G2", 20:"Fantasia 1 2-C3", 
    21: "Fantasia 1 3-C4", 22:"Fantasia 1 4-C5", 23: "Fantasia 2 1-G2", 24:"Fantasia 2 2-G3", 25: "Fantasia 2 3-G4", 26:"Finger Bass 1-G0", 27: "Finger Bass 2-E1", 28:"Finger Bass 3-D2", 
    29: "Flute 1 1-G3", 30:"Flute 1 2-F4", 31: "Flute 1 3-D#5", 32:"Flute 2 1-G3", 33: "Flute 2 2-F4", 34:"Harp 1-C2", 35: "Harp 2-C4", 36:"Harpsichrd 1 1-C3", 
    37: "Harpsichrd 1 2-C4", 38:"Harpsichrd 1 3-C5", 39: "Harpsichrd 2 1-C3", 40:"Harpsichrd 2 2-C4", 41: "Harpsichrd 2 3-C5", 42:"Horns 1-B2", 43: "Horns 2-F3", 44:"Marimba 1-C4", 
    45: "Marimba 2-C5", 46:"Music Box 1-C3", 47: "Music Box 2-C4", 48:"Nylon Guitar 1-C2", 49: "Nylon Guitar 2-C4", 50:"Oboe 1 1-C#3", 51: "Oboe 1 2-E4", 52:"Oboe 2 1-C4", 
    53: "Oboe 2 2-C5", 54:"Pan Flute 1-C3", 55: "Pan Flute 2-C4", 56:"Pan Flute 3-C5", 57: "Piano 1-F#2", 58:"Piano 2-F#3", 59: "Piano 3-F#4", 60:"Pick Bass 1-D0", 
    61: "Pick Bass 2-D1", 62:"Pizz Strings 1-A1", 63: "Pizz Strings 2-F#", 64:"Pizz Strings 3-C3", 65: "Pizz Strings 4-C4", 66:"Sitar 1-D2", 67: "Sitar 2-D3", 68:"Steel Guitar 1-C2", 
    69: "Steel Guitar 1-D3", 70:"String Sec. 1-C2", 71: "String Sec. 2-C3", 72:"String Sec. 3-C4", 73: "Syn Mallet 1-C1", 74:"Syn Mallet 2-C4", 75: "Syn String 1 1-C1", 76:"Syn String 1 2-C2", 
    77: "Syn String 1 3-E3", 78:"Syn String 1 4-C4", 79: "Syn String 1 5-C5", 80:"Synth 1 1-C2", 81: "Synth 1 2-C3", 82:"Synth 2 1-C3", 83: "Synth 2 2-C4", 84:"Synth 2 3-C5", 
    85: "Trombone 1-G1", 86:"Trombone 2-E2", 87: "Trombone 3-F3", 88:"Tuba 1-A0", 89: "Tuba 2-G1", 90:"Tuba 3-C2", 91: "Tubular Bell 1-C3", 92:"Tubular Bell 2-C3", 
    93: "UnusedSynth 1-C1", 94:"UnusedSynth 2-C3", 95: "Vibraphone 1-C4", 96:"Vibraphone 2-C5", 97: "Violin 1 1-C#3", 98:"Violin 1 2-G3", 99: "Violin 1 3-G4", 100:"Violin 2 1-G3", 
    101: "Violin 2 2-G4", 102:"Voice Oohs 1-C2", 103: "Voice Oohs 3-A3", 104:"Voice Oohs 3-C3"
}