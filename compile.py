import argparse, os, sys


def getArgs():
    parser = argparse.ArgumentParser('mmpcomp')
    parser.add_argument(
        'infile',
        type=str,
        help='Input file'
    )
    parser.add_argument(
        '-o',
        '--outfile',
        type=str,
        default='output.bin',
        help='Output file'
    )
    parser.add_argument(
        '-d',
        '--device',
        type=str,
        default='MMP-1',
        help='Device to target'
    )
    parser.add_argument(
        '-l',
        '--list',
        action='store_true',
        help='Generate program listing'
    )

    args = parser.parse_args()

    return args


def isValidTagName(name):
    validChars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ._'
    if name[0] in '0123456789': return False
    for char in name:
        if not char in validChars: return False
    return True


def resolveAddr(ident, program):
    # ident is a pointer
    if ident[0] == '&':
        pointerTarget = resolveAddr(ident[1:], program)
        if pointerTarget is None:
            return None
        
        elif pointerTarget in program.pointers.keys():
            return pointers[pointerTarget]
        
        else:
            pointerAddr = len(program.entries) + len(program.pointers)  # pointers will be embedded directly after the program
            program.pointers[pointerTarget] = pointerAddr
            return pointerAddr

    # ident is a tag name
    elif ident in program.tags:
        return program.tags[ident]

    # ident is a literal address
    else:
        return resolveValue(ident)

def resolveValue(ident):
    try:
        if ident[0:2] == '0x': value = int(ident, base=16)
        elif ident[0:2] == '0b': value = int(ident, base=2)
        else: value = int(ident)
        return value
    except ValueError:
        return None
        

deviceLayouts = {
    'MMP-1': {
        'programOffset': 0x0000,
        'maxProgramSize': 0x4000,
        'tags': {
            'ROM':              0x0000,
            'RAM':              0x4000,
            'ALU.A':            0xF000,
            'ALU.B':            0xF001,
            'ALU.SUM':          0xF002,
            'ALU.DIF':          0xF003,
            'ALU.LSH':          0xF004,
            'ALU.RSH':          0xF005,
            'ALU.AND':          0xF006,
            'ALU.OR':           0xF007,
            'ALU.XOR':          0xF008,
            'ALU.NOT':          0xF009,
            'ALU.GT':           0xF00A,
            'ALU.GTE':          0xF00B,
            'ALU.LT':           0xF00C,
            'ALU.LTE':          0xF00D,
            'DispA':            0xF100,
            'DispB':            0xF101,
            'Matrix.Index':     0xF200,
            'Matrix.Row':       0xF201,
            'ClockMode':        0xFFF0,
            'Step':             0xFFFF
        }
    }
}
deviceLayout = None

def getDeviceLayout(deviceName):
    global deviceLayout
    try: deviceLayout = deviceLayouts[deviceName]
    except IndexError: print('Device {} not recognized'); sys.exit(1)


class _program:
    def __init__(self):
        self.source = []
        self.entries = {}
        self.tags = {}
        self.pointers = {}


# First pass: Generate program object
def parseFile(path):
    program = _program()
    program.tags = deviceLayout['tags']

    # Load source
    with open(path, 'r') as infile:
        program.source = infile.read().split('\n')
    print('Read {} ({} lines)'.format(args.infile, len(program.source)))

    for l, line in enumerate(program.source):
        instr = line.split(';')[0].strip()  # Remove comments and clean up whitespace
        if instr == '': continue


        # Absolute tag
        elif instr[0] == '$':
            name, rawAddr = instr[1:].strip().split()
            if name in program.tags.keys(): print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

            addr = resolveAddr(rawAddr, program)
            if addr is None: print('ERROR Line {}: Cannot resolve address {}'.format(l + 1, rawAddr))
            program.tags[name] = addr

            # print('Line {}: Declare absolute tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))


        # Relative tag
        elif instr[0] == '@':
            if '=' in instr:
                name, rawValue = [part.strip() for part in instr[1:].split('=')]
            else:
                name = instr[1:].strip(); rawValue = None

            if name in program.tags.keys():
                print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

            addr = len(program.entries)

            if not rawValue is None:
                value = resolveValue(rawValue)
                if value is None: print('ERROR Line {}: Invalid value {}'.format(l + 1, rawValue)); sys.exit(1)
                program.entries[l] = value

            program.tags[name] = addr

            # print('Line {}: Declare relative tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))


        # Copy
        else:
            try:
                src, dest = [part.strip() for part in instr.split()]
            except ValueError:
                print('ERROR Line {}: Instruction invalid'.format(l + 1)); sys.exit(1)

            program.entries[l] = (src, dest)

            # print('Line {}: Copy {} to {}'.format(l + 1, src, dest))

    return program

# Second pass: Replace tag names with their resolutions
def resolveTags(program):
    for l in program.entries.keys():
        instr = program.entries[l]
        if isinstance(instr, tuple):
            src, dest = [resolveAddr(part, program) for part in instr]
            
            if src is None: print('ERROR Line {}: Unable to resolve address for {}'.format(l + 1, instr[0])); sys.exit(1)
            if dest is None: print('ERROR Line {}: Unable to resolve address for {}'.format(l + 1, instr[1])); sys.exit(1)

            program.entries[l] = (src, dest)

# Third pass: Generate binary
def generateBinary(program):
    binary = b''
    for instr in program.entries.values():
        if isinstance(instr, tuple):
            binary = binary + int.to_bytes(instr[0], 2, 'big') + int.to_bytes(instr[1], 2, 'big')
        elif isinstance(instr, int):
            binary = binary + int.to_bytes(instr, 4, 'big')

    for pointerTarget in program.pointers.keys():
        binary = binary + int.to_bytes(pointerTarget, 4, 'big')

    return binary


def listProgram(program):
    terminalWidth = os.get_terminal_size()[0]
    compiledWidth = 16
    pointerWidth = 11
    lineNumSize = len(str(len(program.source)))   # Max number of digits in line numbers
    print(' Addr  : {} | Line : Source'.format('Compiled'.center(compiledWidth)))
    print('====== : {} | ==== : {}'.format('=' * compiledWidth, '=' * (terminalWidth - compiledWidth - 19)))
    for l, line in enumerate(program.source):
        if l in program.entries.keys():
            addr = tuple(program.entries.keys()).index(l)

            compiled = program.entries[l]
            if isinstance(compiled, tuple):
                src, dest = compiled
                if isinstance(src, int): src = '0x{:04X}'.format(src)
                if isinstance(dest, int): dest = '0x{:04X}'.format(dest)
                compiled = '{} -> {}'.format(str(src).rjust((compiledWidth - 4) // 2), str(dest).ljust((compiledWidth - 4) // 2))
            
            elif isinstance(compiled, int):
                compiled = '0x{:08X}'.format(compiled).ljust(compiledWidth)

            # Should never get here if passes 1 and 2 worked, but hey it never hurts to add an else
            else:
                compiled = repr(compiled).ljust(compiledWidth)

        else:
            compiled = ' ' * compiledWidth
            addr = None

        if addr is None: addr = ' ' * 8
        else: addr = '0x{:04X} :'.format(addr)

        print('{} {} | {} : {}'.format(addr, compiled, str(l + 1).rjust(max(lineNumSize, 4)), line))

    print(' Addr  : {}'.format('Pointer'.center(pointerWidth)))

    
    reversePointers = {}
    pointerTargets = tuple(program.pointers.keys())

    for p, pointerAddress in enumerate(program.pointers.values()):
        reversePointers[pointerAddress] = pointerTargets[p]

    for pointerAddress in reversePointers.keys():
        addr = '0x{:04X} :'.format(pointerAddress)
        compiled = '&0x{:08X}'.format(reversePointers[pointerAddress])

        print('{} {}'.format(addr, compiled))


if __name__ == '__main__':
    args = getArgs()

    getDeviceLayout(args.device)
    program = parseFile(args.infile)
    resolveTags(program)
    binary = generateBinary(program)

    # Write binary
    with open(args.outfile, 'wb') as outfile:
        outfile.write(binary)
    
    binarySize = len(binary)
    suffixes = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']

    for suffix in suffixes:
        if binarySize < 1024:
            print('Wrote {} ({}{})'.format(args.outfile, binarySize, suffix))
            break
        else:
            binarySize //= 1024

    if args.list: listProgram(program)
