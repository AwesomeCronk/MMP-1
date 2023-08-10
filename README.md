# MMP-1

The Memory Mapped Processor only copies data between addresses.

### Instructions

Every instruction is written as a source and a destination, either with a tag or a literal address:

```
0x0000 0x419A
A B
SUM Score
0x5F9D Step
```

## Tags

$ tags are assigned an address manually. @ tags are assigned an address based on their location in the program. The location of an @ tag is dependent on what code is around it, while the address of a $ tag is provided.

```
$ NewTag 0x15

@ SomePointInTheCode
A B
Step C
D Step
```

***May drop, undetermined***

$ tags with a directly assigned address can be relative to other tags:

```
$ NewTag OldTag + 0x30
```

Any tag that resides within the space occupiable by the program can have a value filled in there:

```
$ A 0x200 = 6

@ B = 7
```

$ tags may point to an instruction in the program. If such tags are assigned a value, the value will overwrite the instruction there. @ tags normally point to the instruction immediately following the tag. If assigned a value, the value will be inserted into the program (without overriding instructions)

## Pointers

Prefixing a tag or literal in an instruction with an ampersand (&) causes the address of tag or literal to be copied instead of the data *at* the address. The compiler achieves this by appending a bank of pointer data at the end of the program and inserting the address of the related pointer entry into the instruction. For example, here is the listing of a basic test program demonstrating this:

```
Read programs/test.mmp (15 lines)
Wrote program.bin (24B)
 Addr  :     Compiled     | Line : Source
====== : ================ | ==== : ==================================================================================
                          |    1 : ; Test jump
                          |    2 : 
                          |    3 : ; If this instruction is commented out, DispA should
                          |    4 : ; show 2, then 3. Otherwise, DispA should just show 3.
0x0000 : 0x0005 -> 0xFFFF |    5 : &Display3 Step
                          |    6 : 
                          |    7 : @ Display2
0x0001 : 0x0003 -> 0xF100 |    8 : Const_2 DispA
                          |    9 : 
                          |   10 : @ Display3
0x0002 : 0x0004 -> 0xF100 |   11 : Const_3 DispA
                          |   12 : 
0x0003 : 0x00000002       |   13 : @ Const_2 = 2
0x0004 : 0x00000003       |   14 : @ Const_3 = 3
                          |   15 : 
0x0005 : &0x00000002      |

```

## Addresses

The address space is 16 bits, with 32 bit words. Hardware is mapped to these addresses, pre-configured in the compiler with different hardware versions selectable with a command-line argument:
```
0x0000-0x3FFF : ROM/EEPROM
0x4000-0x7FFF : RAM
0xF000-0xF00A : ALU A, B, SUM, AND, OR, XOR, NOT, GT, GTE, LT, LTE
0xFFFF        : Step
```

## Comments

Line comments are denoted with a semicolon (`;`). All text to the right of a semicolon is ignored. Block comments are surrounded within left and right arrows(`<>`)
