import argparse, sys


def getArgs():
    parser = argparse.ArgumentParser('mmpcomp')
    parser.add_argument(
        'infile',
        type=str,
        help='Input file'
    )
    parser.add_argument(
        '-o',
        '--output',
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
        'ROM':      0x0000,
        'RAM':      0x4000,
        'ALU.A':    0xF000,
        'ALU.B':    0xF001,
        'ALU.SUM':  0xF002,
        'ALU.AND':  0xF003,
        'ALU.OR':   0xF004,
        'ALU.XOR':  0xF005,
        'ALU.NOT':  0xF006,
        'ALU.GT':   0xF007,
        'ALU.GTE':  0xF008,
        'ALU.LT':   0xF009,
        'ALU.LTE':  0xF00A,
        'Step':     0xFFFF
    }
}


if __name__ == '__main__':
    args = getArgs()
    try: tags = deviceLayouts[args.device]
    except IndexError: print('Device {} not recognized'); sys.exit(1)
    valuesToWrite = {}
    binary = b''
    program = []

    with open(args.infile, 'r') as infile:
        for l, line in enumerate(infile.readlines()):
            instr = line.split(';')[0].strip()  # Remove comments and clean up whitespace
            if instr == '': continue
            
            elif instr[0] == '$':
                if '=' in instr:
                    declaration, rawValue = [part.strip() for part in instr[1:].split('=')]
                    value = resolveValue(rawValue)
                    if value is None: print('ERROR Line {}: Absolute tag {} has invalid value {}'.format(l + 1, name, rawValue)); sys.exit(1)

                else:
                    declaration = instr[1:].strip(); value = None

                name, rawAddr = declaration.split()
                if name in tags.keys(): print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

                addr = resolveAddr(rawAddr)
                if addr is None: print('ERROR Line {}: Absolute tag {} has invalid address {}'.format(l + 1, name, rawAddr)); sys.exit(1)

                if not value is None:
                    valuesToWrite[addr] = value

                tags[name] = addr

                print('Line {}: Declare absolute tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))

            elif instr[0] == '@':
                if '=' in instr:
                    name, value = [part.strip() for part in instr[1:].split('=')]
                else:
                    name = instr[1:].strip(); value = None

                if name in tags.keys():
                    print('ERROR Line {}: Tag {} declared multiple times'.format(l + 1, name)); sys.exit(1)

                addr = len(program)

                if not value is None:
                    program.append(value)

                tags[name] = addr

                print('Line {}: Declare relative tag {} at 0x{:04X}'.format(l + 1, name, addr) + ('' if value is None else ' with value {}'.format(value)))

            else:
                rawSrc, rawDest = [part.strip() for part in instr.split()]

                src = resolveAddr(rawSrc)
                dest = resolveAddr(rawDest)

                if src is None: print('ERROR Line {}: Invalid source {}'.format(l + 1, rawSrc)); sys.exit(1)
                if dest is None: print('ERROR Line {}: Invalid destination {}'.format(l + 1, rawDest)); sys.exit(1)

                print('Line {}: Copy {} to {}'.format(l + 1, src, dest))
                program.append((src, dest))

        print('Program listing:')
        for instr in program: print(instr)
