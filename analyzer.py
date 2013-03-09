import sys
import os
import time
import re
from pcap import *
from optparse import OptionParser
from userstats import *
from TCPAnalyzer import *
from HttpConversationParser import *
from PacketStreamAnalyzer import *
from HTMLAnalyzer import *
import utils
from utils import *


# Setup command line options
parser = OptionParser()
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Prints extra information useful for debugging.")
# MODE
#parser.add_option("-i", "--interface", action="store", dest="interface", default=None, help="Name of interface to be sniffed")
#parser.add_option("-f", "--filter", action="store_true", dest="filter_enabled", default=False, help="Runs PacketSniffer in FILTER mode.")
## SNIFF mode options
#parser.add_option("-t", "--transcript", action="store_true", dest="save_transcript", default=False, help="Saves a transcript of your sniffing session (which can be used for filtering later).")
#parser.add_option("-n", "--seconds", action="store", dest="runtime_seconds", default=None, help="Specify the number of seconds for which you'd like to sniff.")
## FILTER mode options
#parser.add_option("-s", "--source", action="store", dest="filter_source_ip", default=None, help="The source IP used for filtering packets.")
#parser.add_option("-d", "--dest", action="store", dest="filter_destination_ip", default=None, help="The destination IP used for filtering packets.")
#parser.add_option("-l", "--protocol", action="store", dest="filter_protocol", default=None, help="The protocol name used for filtering packets.")
#parser.add_option("-p", "--port", action="store", dest="filter_port", default=None, help="The port used for filtering packets.")



def filter(packet):
    return True

def main(options, args):
    utils.VERBOSE = options.verbose
    utils.create_TMP()

    trace = args[0]
    stats = UserStats()
    
    ##
    ## STEP ONE: Analyze individual packets
    ##
    print 'Analyzing individual packets...'
    p = PacketStreamAnalyzer()
    try:
        # Create PCap object
        # Offline network capture
        listener = OfflineNetworkCapture(trace)

    except (PCapPermissionDeniedException,PCapInvalidNetworkAdapter), e:
        print e
        sys.exit(1)
        


    # Process packet trace
    try:
        for packet in listener.get_packets(filter):
            #print packet.length, packet,'\n'
            p.update(packet)
    except (KeyboardInterrupt, SystemExit), e:
         sys.exit()
    finally:
        listener.close()

    # Updated user stats
    stats.update_os(p.os)
    stats.update_languages(p.languages)
    stats.update_browsers(p.browsers)
    stats.update_visited_domains(p.visited_domains)
    stats.update_visited_subdomains(p.visited_subdomains)
    stats.update_google_queries(p.google_queries)



    ##
    ## STEP TWO: Analyze TCP streams
    ##
    print 'Analyzing TCP streams...'
    t = TCPAnalyzer(trace)

    print 'Analyzing HTTP conversations...'
    # Don't waste time reconstructing HTTP conversations that don't contain HTML
    html_streams = []
    for s in p.tcp_html_streams:
        sinfo = s.split(',')
        html_streams += [st for st in t.http_streams if sinfo[0] in st.ip_addresses and sinfo[2] in st.ip_addresses and int(sinfo[1]) in st.ports and int(sinfo[3]) in st.ports]

    for html_stream in html_streams:
        dprint('    Analyzing stream: %s' % html_stream)
        parser = HttpConversationParser(html_stream.http_data)
        for page in parser.html_pages:
            ha = HTMLAnalyzer(page)
            stats.update_page_titles( ha.page_titles )
            stats.update_amazon_products( ha.amazon_products )
        
    print stats

    # Remove TMP dir
    utils.delete_TMP()

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    sys.exit(main(options, args))
