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


def resolveAddr(addr):
    if addr in tags:
        addr = tags[addr]
    else:
        try:
            if addr[0:2] == '0x': addr = int(addr, base=16)
            elif addr[0:2] == '0b': addr = int(addr, base=2)
            else: addr = int(addr)
        except ValueError:
            return None
        
    return addr

def resolveValue(value):
    try:
        if value[0:2] == '0x': value = int(value, base=16)
        elif value[0:2] == '0b': value = int(value, base=2)
        else: value = int(value)
    except ValueError:
        return None
    return value
        

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
            'ALU.AND':          0xF003,
            'ALU.OR':           0xF004,
            'ALU.XOR':          0xF005,
            'ALU.NOT':          0xF006,
            'ALU.GT':           0xF007,
            'ALU.GTE':          0xF008,
            'ALU.LT':           0xF009,
            'ALU.LTE':          0xF00A,
            'DispA':            0xF100,
            'DispB':            0xF101,
            'Matrix.XIndex':    0xF200,
            'Matrix.CValues':   0xF201,
            'Step':             0xFFFF
        }
    }
}


if __name__ == '__main__':
    args = getArgs()
    try: tags = deviceLayouts[args.device]['tags']
    except IndexError: print('Device {} not recognized'); sys.exit(1)
    binary = b''
    program = {}


    # Load code
    with open(args.infile, 'r') as infile:
        code = infile.read().split('\n')
    print('Read {} ({} lines)'.format(args.infile, len(code)))


    # First pass: Generate program object
    for l, line in enumerate(code):
        instr = line.split(';')[0].strip()  # Remove comments and clean up whitespace
        if instr == '': continue


        # Absolute tag
        elif instr[0] == '$':
            name, rawAddr = instr[1:].strip().split()
            if name in tags.keys(): print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

            addr = resolveAddr(rawAddr)
            if addr is None: print('ERROR Line {}: Cannot resolve address {}'.format(l + 1, rawAddr))
            tags[name] = addr

            # print('Line {}: Declare absolute tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))


        # Relative tag
        elif instr[0] == '@':
            if '=' in instr:
                name, rawValue = [part.strip() for part in instr[1:].split('=')]
            else:
                name = instr[1:].strip(); rawValue = None

            if name in tags.keys():
                print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

            addr = len(program)

            if not rawValue is None:
                value = resolveValue(rawValue)
                if value is None: print('ERROR Line {}: Invalid value {}'.format(l + 1, rawValue))
                program[l] = value

            tags[name] = addr

            # print('Line {}: Declare relative tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))


        # Copy
        else:
            src, dest = [part.strip() for part in instr.split()]

            program[l] = (src, dest)

            # print('Line {}: Copy {} to {}'.format(l + 1, src, dest))


    # Second pass: Replace tag names with their resolutions
    for l in program.keys():
        instr = program[l]
        if isinstance(instr, tuple):
            src, dest = [resolveAddr(part) for part in instr]
            
            if src is None: print('ERROR Line {}: Unable to resolve address for {}'.format(l + 1, instr[0])); sys.exit(1)
            if dest is None: print('ERROR Line {}: Unable to resolve address for {}'.format(l + 1, instr[1])); sys.exit(1)

            program[l] = (src, dest)

    # Third pass: Generate binary
    binary = b''
    for instr in program.values():
        if isinstance(instr, tuple):
            binary = binary + int.to_bytes(instr[0], 2, 'big') + int.to_bytes(instr[1], 2, 'big')
        elif isinstance(instr, int):
            binary = binary + int.to_bytes(instr, 4, 'big')


    # Write binary
    with open(args.outfile, 'wb') as outfile:
        outfile.write(binary)
    
    binarySize = len(binary)
    prefixes = ['B', 'kB', 'MB', 'GB', 'TB', 'PB']

    for prefix in prefixes:
        if binarySize < 1024:
            print('Wrote {} ({}{})'.format(args.outfile, binarySize, prefix))
            break
        else:
            binarySize //= 1024


    # Generate program listing
    if args.list:
        terminalWidth = os.get_terminal_size()[0]
        compiledWidth = 16
        lineNumSize = len(str(len(code)))   # Max number of digits in line numbers
        print(' Addr  : {} | Line : Source'.format('Compiled'.center(compiledWidth)))
        print('====== : {} | ==== : {}'.format('=' * compiledWidth, '=' * (terminalWidth - compiledWidth - 19)))
        for l, line in enumerate(code):
            if l in program.keys():
                addr = tuple(program.keys()).index(l)

                compiled = program[l]
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
