def main():
    import sys
    import argparse
    import serial
    from serial.tools.list_ports import comports
    from tinyprog import TinyProg

    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--list", action="store_true",
                        help="list connected and active FPGA boards")
    parser.add_argument("-p", "--program", type=str,
                        help="program FPGA board with the given bitstream")
    parser.add_argument("-u", "--program-userdata", type=str,
                        help="program FPGA board with the given user data")
    parser.add_argument("-b", "--boot", action="store_true",
                        help="command the FPGA board to exit the "
                             "bootloader and load the user configuration")
    parser.add_argument("-c", "--com", type=str, help="serial port name")
    parser.add_argument("-i", "--id", type=str, help="FPGA board ID")
    parser.add_argument("-d", "--device", type=str, default="1d50:fb9a",
                        help="device id (vendor:product); default is (1d50:fb9a)")
    parser.add_argument("-a", "--addr", type=int,
                        help="force the address to write the bitstream to")
    parser.add_argument("-m", "--meta", action="store_true",
                        help="dump out the metadata for all connected boards in JSON")

    args = parser.parse_args()

    device = args.device.lower().replace(':', '')
    if len(device) != 8 or not all(c in '0123456789abcdef' for c in device):
        print "    Invalid device id, use format vendor:product"
        sys.exit(1)
    device = '{}:{}'.format(device[:4], device[4:])
    active_boards = [p[0] for p in comports() if device in p[2]]

    if args.meta:
        meta = []
        for port in active_boards:
            with serial.Serial(port, timeout=1.0, writeTimeout=1.0) as ser:
                p = TinyProg(ser)
                m = p.meta.root
                m["port"] = port
                meta.append(m)
        import json
        print json.dumps(meta, indent=2)
        sys.exit(0)

    print ""
    print "    TinyProg CLI"
    print "    ------------"
    
    print "    Using device id {}".format(device)

    # find port to use
    active_port = None
    if args.com is not None:
        active_port = args.com
    elif args.id is not None:
        for port in active_boards:
            with serial.Serial(port, timeout=1.0, writeTimeout=1.0) as ser:
                p = TinyProg(ser)
                if p.meta.uuid().startswith(args.id):
                    active_port = port
                    break

    elif not active_boards:
        print "    No port was specified and no active bootloaders found."
        print "    Activate bootloader by pressing the reset button."
        sys.exit(1)
    elif len(active_boards) == 1:
        print "    Only one board with active bootloader, using it."
        active_port = active_boards[0]
    else:
        print "    Please choose a board with the -c or -i option."

    # list boards
    if args.list or active_port is None:
        print "    Boards with active bootloaders:"
        for port in active_boards:
            with serial.Serial(port, timeout=1.0, writeTimeout=1.0) as ser:
                p = TinyProg(ser)
                m = p.meta.root
                print ""
                print "        %s: %s %s" % (port, m[u"boardmeta"][u"name"], m[u"boardmeta"][u"hver"])
                print "            UUID: %s" % m[u"boardmeta"][u"uuid"]
                print "            FPGA: %s" % m[u"boardmeta"][u"fpga"]

        if len(active_boards) == 0:
            print "        No active bootloaders found.  Check USB connections"
            print "        and press reset button to activate bootloader."

    # program the flash memory
    elif args.program is not None:
        print "    Programming " + active_port + " with " + args.program

        def progress(info):
            if isinstance(info, str):
                print "    " + info

        with serial.Serial(active_port, timeout=1.0, writeTimeout=1.0) as ser:
            fpga = TinyProg(ser, progress)
            bitstream = fpga.slurp(args.program)
            addr = fpga.meta.userimage_addr_range()[0]
            if args.addr is not None:
                addr = args.addr
            if addr < 0:
                print "    Negative write addr: {}".format(addr)
                sys.exit(1)
            if not fpga.is_bootloader_active():
                print "    Bootloader not active"
                sys.exit(1)
            print "    Programming at addr {:06x}".format(addr)
            if fpga.program_bitstream(addr, bitstream):
                sys.exit(0)
            else:
                sys.exit(1)

    # boot the FPGA
    if args.boot:
        print "    Booting " + active_port
        with serial.Serial(active_port, timeout=1.0, writeTimeout=1.0) as ser:
            fpga = TinyProg(ser)
            fpga.boot()

if __name__ == '__main__':
    main()
