#!/usr/bin/env python

import sys
import time
import os
import logging
import re
import subprocess
import signal
import argparse
from userstats import *
import utils
import analyzer

TCPDUMP = '/usr/bin/env tcpdump'

def analyze_trace(trace_path, stats):
    logging.getLogger(__name__).info('Analyzing trace %s', trace_path)
    stats = analyzer.analyze_trace(trace_path, stats)

    if args.outfile:
        try:
            with open(args.outfile, 'w') as f:
                f.write(stats.json)
            f.closed
        except Exception as e:
            logging.getLogger(__name__).error(e)
    else:
        print stats.json

def capture_live_traces():
    # Start tcpdump
    utils.init_temp_dir('traces')
    tempdir = utils.get_temp_dir('traces')
    logging.getLogger(__name__).debug('Dumping traces to temp dir: %s', tempdir)
    tracefile = os.path.join(tempdir, '%F_%H-%M-%S_trace.pcap')
    try:
        p = subprocess.Popen('%s -i %s -G %i -w %s' % (TCPDUMP, args.interface, args.rotate_seconds, tracefile), shell=True)
    except Exception as e:
        logging.getLogger(__name__).error('Error starting tcpdump: %s', e)
        sys.exit()


    try:
        stats = UserStats()
        while True:
            full_traces = os.listdir(utils.get_temp_dir('traces'))[0:-1]  # don't start reading trace tcpdump is currently filling
            if len(full_traces) == 0:
                time.sleep(5)
            elif len(full_traces) * int(args.rotate_seconds) > 300:
                logging.getLogger(__name__).warning('Analyzer is more than 5 minutes behind (%d unprocessed trace files of %s seconds each)', len(full_traces), args.rotate_seconds)
            
            for trace in full_traces:
                trace_path = os.path.join(utils.get_temp_dir('traces'), trace)
                stats = analyze_trace(trace_path, stats)
                os.remove(trace_path)
    except (KeyboardInterrupt, SystemExit), e:
        p.terminate()
        sys.exit()
    except Exception as e:
        logging.getLogger(__name__).error(e)
        p.terminate()
        sys.exit()
    finally:
        utils.remove_temp_dir('traces')
    

def main():
    global p

    utils.init_temp_dir('images') # deletes existing if there is one

    if args.tracefile:
        stats = UserStats()
        analyze_trace(args.tracefile, stats)
    else:
        capture_live_traces()



def kill_handler(signum, frame): 
    if p:
        p.terminate()
    sys.exit()



if __name__ == '__main__':
    # set up command line args
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                        description='Analyze network traffic for leaked information')
    parser.add_argument('-i', '--interface', default='en0', help='Name of interface to sniff (use "ifconfig" to see options).')
    parser.add_argument('-G', '--rotate_seconds', default=30, help='Number of seconds to sniff before creating new trace file and analyzing previous')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Print extra information for debugging.')
    parser.add_argument('-o', '--outfile', default=None, help='Save output JSON to a file instead of printing to terminal.')
    parser.add_argument('-r', '--tracefile', default=None, help='Analyze existing trace (PCAP file) instead of live traffic.')
    args = parser.parse_args()

    args.rotate_seconds = int(args.rotate_seconds)

    # set up signal handlers
    signal.signal(signal.SIGTERM, kill_handler)
    signal.signal(signal.SIGINT , kill_handler)
    
    # set up logging
    logging.basicConfig(
        #filename = fileName,
        format = "%(levelname) -10s %(asctime)s %(module)s:%(lineno)s %(funcName) -26s %(message)s",
        level = logging.DEBUG if args.verbose else logging.WARNING
    )

    main()
