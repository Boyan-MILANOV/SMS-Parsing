# -*- coding: utf-8 -*-
########################################################################
#                          SMS-Tool-Kit: smsparser
#                          -----------------------
#
# This script enables you to use different SMS parsers in order to find 
# SMS messages in a binary image. The script is divided in 3 parts:
#
# - Framework-Land: The core of the script. It defines structures for 
#       SMS parsers, filters, the different kinds of SMS, and contains
#       the code of the command-line interface that starts when you
#       run the script. It contains also some utilitary functions ( like
#       conversions of strings, of semi_octets, date decoding, etc). 
#       Unless you want to add some functionnalities or more SMS types
#       you should have a reason to modify this part :) 
#
# - Parser-Land: This part of the script is intended to be modified by 
#       the user. In Parser Land you can define your own parsing 
#       functions and build your custom parsers. For more information 
#       about how to declare a Parser, go check the beginning of the 
#       Parser-Land
#
# - Filter-Land: This part of the script is intended to be modified by 
#       the user. It is the same as Parser-Land but here you can define
#       filters. Filters enable you to decide weather a carved SMS is
#       valid or invalid. For more info about how to declare a filter,
#       go check the beginning of Parser-Land 
#
#
#                          How do I use it ??
#                          ------------------ 
#
# To use the smsparser.py script, you have to declare Parsers (mandatory)
# and filters (optionnal) in the Parser-Land and Filter-Land. 
# When you declare new parsers and filters (see Parser-Land & Filter-Land)
# they are automatically added to the menu in the CLI. 
# Then, you simply launch the script, and a command-line-interface appears.  
# The CLI offers several functions. You can select parsers and filters you
# want to use on a binary image you want to analyse. . Once you selected 
# the ones you want, simply use the 'parser-run' command to scan the  
# image for SMS ! 
#
#
# This script comes with no warranty at all
########################################################################

import sys
import re


# ------------------------------------------------------
#
#                    Framework Land
#                    -------------- 
#
# Basic parser plateform definition. 
# Be careful if you modify this section of the code !  
#
# ------------------------------------------------------

ERROR = -1 # Error code for parsing functions 

#######################
# CODES AND CONSTANTS #
# of TPDU format      #
#######################

# MTI : gives the message type on the two least significant bits
#       of the header
MTI_DELIVER = 0b00
MTI_SUBMIT = 0b01

# TON (Type Of Number):
TON_UNKNOWN = 0b000
TON_INTERNATIONAL = 0b001
TON_NATIONAL = 0b010
TON_NETWORK_SPEC = 0b011
TON_SUSCRIBER = 0b100
TON_ALPHANUM = 0b101
TON_ABREV = 0b110

# Data Coding Schemes
# DCS is stored on one byte, the least significant 4 bits give the encoding
DCS_GSM7 = [0,1,2,3]
DCS_ASCII8 = [4,5,6,7]
DCS_UCS2 = [8,9,0xA,0xB]

# VPF (Validity Period Format)
# Bits 3 and 4 of the header
# They give the length for the TP-VP field 
VPF_NO = 0b00 # not present
VPF_ENHANCED = 0b01 # enhanced format, 7 bytes long
VPF_RELATIVE = 0b10 # relative format, 1 byte long
VPF_ABSOLUTE = 0b11 # absolute format, 7 bytes long     

#######################
# Utilitary functions #
#######################

def nibble_to_str(nibble_string, number=True):
    """
    Description
    -----------
    Converts a semi-octet string into a decimal string
    Ex: "\x19\xa5" -> "915a"
    
    Parameters
    ----------
    nibble_string : string of bytes
    number : Set to True <=> converter string must be a phone number 
    
    Return
    ------
    None or string
    """
    
    res = ""
    seen_non_decimal = False
    digits = ["0","1","2","3","4","5","6","7","8","9"]
    for byte in nibble_string:
        # Low 4 bits 
        low = str(ord(byte) & 0x0f )
        # High 4 bits
        high = str(ord(byte) >> 4)
        if( number ):
            # If we want to convert a number
            # Check for non decimal chars
            if( seen_non_decimal ):
                return None
            if( not low in digits ):
                return None
            else:
                res += low
            if( not high in digits ):
                seen_non_decimal = True
            else:
                res += high
        else:
            res += low
            res += high
        
    return res 

def str_to_date(string, check=True):
    """
    Description
    -----------
    Takes a PDU string and decodes it into a date string
    If check=True the function also checks if the date is valid
    (if the date isn't valid it returns None) 
    
    Parameters
    ----------
    string : string of bytes, length should be 7
    check : bool
    
    Return
    ------
    returns  - a date in string format
             - or None 
    """
    try:
        day = nibble_to_str(string[2])      # Day
        month = nibble_to_str(string[1])    # Month
        year = nibble_to_str(string[0])     # Year
        if( int(year) > 50 ):
            year = "19"+year
        else:
            year = "20"+year 
        hour = nibble_to_str(string[3])     # Hours
        minutes = nibble_to_str(string[4])  # Minutes
        seconds = nibble_to_str(string[5])  # Seconds
        if( (ord(string[6]) & 0b00001000) >> 3 == 1 ):
            sign = "-"
        else:
            sign="+"
        zone = "{0:02x}".format(int("{0:02x}".format((ord(string[6]) & 0b11110111))[::-1],16)/4)

        # Build date string 
        date = ''
        date += day
        date += '/'+month
        date += '/'+year
        date += ' '+hour
        date += ':'+minutes
        date += ':'+seconds
        date += ' (UTC'+sign+zone+")"
        
        if( not check):
            return date
        else:
            wrong = (int(day) > 31) or (int(month) > 12) or (int(hour) > 23)\
                or (int(minutes) > 59) or (int(seconds) > 59) or (int(zone) > 24)\
                or(int(day) < 1) or (int(month) < 1) or (int(hour) < 0)\
                or (int(minutes) < 0) or (int(seconds) < 0) or (int(zone) < 0) 
            if( wrong ):
                return None
            else:
                return date
        
    except Exception as e:
        return None
 
def str_to_date_utc(string, check=True):
    try:
        day = int(nibble_to_str(string[2]))      # Day
        month = int(nibble_to_str(string[1]))    # Month
        year = int(nibble_to_str(string[0]))     # Year
        hour = int(nibble_to_str(string[3]) )    # Hours
        minutes = int(nibble_to_str(string[4]))  # Minutes
        seconds = int(nibble_to_str(string[5]) ) # Seconds
        if( (ord(string[6]) & 0b00001000) >> 3 == 1 ):
            sign = -1
        else:
            sign= 1
        zone = sign*int("{0:02x}".format((ord(string[6]) & 0b11110111))[::-1],16)/4
        
        # Adjusting time 
        hour -= zone
        if( hour < 0 ):
            hour = 24-hour
            day -= 1
            if( day < 1 ):
                if( month in [5,7, 10, 12] ):
                    day = 30
                    month -= 1
                elif( month in [2, 4,6,8,9,11] ):
                    day = 31
                    month -=1
                elif( month == 3 ):
                    if( year%400 == 0 or (year%4 == 0 and year%100 != 0)):
                        day = 29
                    else:
                        day = 28
                    month = 2
                elif( month == 1 ):
                    day = 31
                    month = 12
                    year -= 1
        elif( hour > 23 ):
            hour -= 24
            day += 1
            if( month in [1,3, 5, 7, 8, 10, 12] ):
                if( day > 31 ):
                    day -= 31
                    month += 1 % 12
            elif( month in [4,6,9,11] ):
                if( day > 31 ):
                    day -= 30
                    month += 1
            elif( month == 2 ):
                if( year%400 == 0 or (year%4 == 0 and year%100 != 0)):
                    limit = 29
                else:
                    limit = 28
                if( day > limit ):
                    month = 3
                    day = day - limit
                
                
        # Build date string 
        date = ''
        date += "{0:02d}".format(day)
        date += '-'+"{0:02d}".format(month)
        date += '-'+"{0:02d}".format(year)
        date += ' '+"{0:02d}".format(hour)
        date += ':'+"{0:02d}".format(minutes)
        date += ':'+"{0:02d}".format(seconds)
        
        if( not check):
            return date
        else:
            wrong = (int(day) > 31) or (int(month) > 12) or (int(hour) > 23)\
                or (int(minutes) > 59) or (int(seconds) > 59)\
                or(int(day) < 1) or (int(month) < 1) or (int(hour) < 0)\
                or (int(minutes) < 0) or (int(seconds) < 0) 
            if( wrong ):
                return None
            else:
                return date
        
    except:
        return None

# GSM7 format decoding 
# From https://stackoverflow.com/questions/13130935/decode-7-bit-gsm
def gsm7_decode(string):
    f = ''.join(["{0:08b}".format(ord(string[i])) for i in range(0, len(string), 1)][::-1])
    return ''.join([chr(int(f[::-1][i:i+7][::-1], 2)) for i in range(0, len(f), 7)])



####################
# Custom functions #
####################

# Custom charging bar :) 
last_percent = -1 
def charging_bar( nb_iter, curr_iter, bar_len, msg="", char=u"\u2588", end_msg=''):
    """
    Print a charging bar 
    """
    global last_percent
    percent = (100*curr_iter)/nb_iter
    if( curr_iter == nb_iter ):
        bar = '\r\t% '
        bar += str(msg)
        bar += ' |'
        full_part = char * bar_len
        bar += full_part + '| '
        bar += end_msg
        bar += '\n'
        sys.stdout.write(bar)
        last_percent = -1
    elif( last_percent != percent):
        last_percent = percent
        bar = '\r\t% '
        bar += str(msg)
        bar += ' |'
        full_part = char * (curr_iter/(nb_iter/bar_len))
        empty_part = " "*(bar_len-len(full_part))
        bar += full_part + empty_part + '| '
        bar += '{:03d}%'.format(100*curr_iter/nb_iter)
        sys.stdout.write(bar)
    sys.stdout.flush()

###############
# SMS classes #
###############

# Types of SMS
class SMSType:
    SMS_PDU = 1
    SMS_OTHER = 99

def new_sms(sms_type):
    """
    Return an instance of the right class according to the 
    requested SMS type. 
    """
    if( sms_type == SMSType.SMS_PDU ):
        return SMSPDU()
    elif(sms_type == SMS_OTHER):
        return SMSGeneric()
    else:
        raise Exception("Unknown sms_type in sms() function")

class SMSGeneric:
    def __init__(self):
        # Common fields for SMS
        self.bin_offset = None # Offset in the binary  
        self.src = None # Source number
        self.dst = None # Destination number 
        self.msg = None # Message body 
        self.sms_date = None # SMS date in human readable format
        self.date_utc_00 = None    # Date in UTC + 0
        self.sms_status = None # (Received / Sent)

    def date(self):
        """
        Description
        -----------
        Returns the date in readable format
        """
        if( self.sms_date ):
            return self.sms_date
        return "Unknown"
    
    def date_utc(self):
        if( self.date_utc ):
            return self.date_utc_00
        return "Unknown"

    def source(self):
        if( self.src ):
            return self.src
        return "Unknown"
        
    def dest(self):
        if( self.dst ):
            return self.dst
        return "Unknown"

    def status(self):
        if( self.sms_status ):
            return self.sms_status
        else:
            return "Unknown"
            
    def offset(self):
        return self.bin_offset
        
    def message(self):
        if( self.msg ):
            return self.msg
        return ''
    
    def excel_output(self):
        def remove_control_chars(s):
            illegal_chars_re = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')
            res = ""
            for i in range(0,len(s)):
                if( next(illegal_chars_re.finditer(s[i]), None )):
                    res += " "
                else:
                    res += s[i]
            return res
        output = []
        # Offset
        output.append(hex(self.offset()))
        # Status
        output.append(self.status())
        # Number
        if( self.status == "Received" ):
            output.append(self.source())
        elif( self.status == "Sent" ):
            output.append(self.dest())
        elif( self.src ):
            output.append(self.source())
        elif( self.dst ):
            output.append(self.dest())
        else:
            output.append("Unknown")
        # Data
        output.append(remove_control_chars(self.message()))
        # Date
        output.append(self.date())
        output.append(self.date_utc())
        return output
    
class SMSPDU(SMSGeneric):
    def __init__(self):
        SMSGeneric.__init__(self)
        # TPDU fields 
        self.tp_header = None  # First octet of the sms
        self.tp_mr = None      # Message Reference 
        self.tp_da = None      # Destination address
        self.tp_oa = None      # Originating Address 
        self.tp_pi = None      # Protocol Identifier 
        self.tp_dcs = None     # Data Coding Scheme
        self.tp_scts = None    # Service Center Time Stamp 
        self.tp_vp = None      # Validity Period 
        self.tp_udl = None     # User Data Length 
        self.tp_ud = None      # User Data 
            
        self.addr_len = None   # Address length for the oa/da fields 

    # Direct access functions
    def header(self):
        return self.tp_header
    def mr(self):
        return self.tp_mr
    def da(self):
        return self.tp_da
    def oa(self):
        return self.tp_oa
    def pi(self):
        return self.tp_pi
    def dcs(self):
        return self.tp_dcs
    def scts(self):
        return self.tp_scts
    def vp(self):
        return self.tp_vp
    def udl(self):
        return self.tp_udl
    def ud(self):
        return self.tp_ud
    def offset(self):
        return self.bin_offset
    
    # Fine-grain access functions 
    def mti(self):
        """
        Description
        -----------
        Returns bits 0 and 1 of the header
        They give the type of PDU message
        """
        return self.header() & 0b00000011

    def vpf(self):
        """
        Description
        -----------
        Returns bits 3 and 4 of the header
        They give the format of the Validity Period field 
        """
        return (self.header() & 0b00011000 ) >> 3
        
    def data_format(self):
        """
        Description
        -----------
        Returns the 4 least significant bytes of the DCS field
        They give the encoding for the user data 
        """
        return self.dcs() & 0x0f
            
    
####################
# Parser class   ###
####################

global_parser_refs = []

class Parser:
    def __init__(self, name, sms_type, func_list):
        global global_parser_refs
        self.parse_functions = func_list
        self.sms_type = sms_type
        self.name = name
        global_parser_refs.append(self)
        
        
    def parse(self, img):
        """
        Description
        -----------
        Parses an image and returns a list of SMS
        
        Parameters
        ----------
        img : a string of bytes
        
        Returns
        -------
        A list of sms instances 
        """
        
        res = []
        for i in range(0,len(img)):
            charging_bar(len(img)-1, i, 20, msg="Parser '{}': ".format(self.name),\
                end_msg = "{} SMS found".format(len(res)))
            sms = new_sms(self.sms_type)
            sms.bin_offset = i
            offset = 0
            for func in self.parse_functions:
                if( i+offset >= len(img)):
                    sms = None
                    break
                parsed_bytes = func(img, i+offset, sms)
                if( parsed_bytes == ERROR):
                    sms = None
                    break
                else:
                    offset += parsed_bytes 
            if( sms ):
                res.append(sms)
        return res


#################
# Filter class ##
#################

global_filter_refs = []
class Filter:
    def __init__(self, name, func_list):
        global global_filter_refs
        self.name = name
        self.filter_functions = func_list 
        global_filter_refs.append(self)
        
    def filter(self, sms_list):
        msg = "\t% Filter '{}': {} -> ".format(self.name, len(sms_list))
        tmp = sms_list
        for func in self.filter_functions:
            tmp = [sms for sms in tmp if func(sms)]
        msg += "{} SMS".format(len(tmp))
        print(msg)
        return tmp

        

#####################
##### CLI script ####
#####################

def bold(string):
    return '\033[1m'+string+'\033[0m'
    
def yellow(string):
    return '\033[93m'+string+'\033[0m'
    
def green(string):
    return '\033[92m'+string+'\033[0m'

def parse(parsers, img):
    res = []
    for parser in parsers:
        res += parser.parse(img)
    return res

def filter_sms(filter_list, sms_list):
    tmp = sms_list
    for f in filter_list:
        tmp = [sms for sms in tmp if f(sms)]
    return tmp
        
# Commands
CMD_LOAD = "load"
CMD_LOAD_SHORT = "l"
image_string = []
def load(filename):
    global image_string
    # Read the binary 
    try:
        f = open(filename, "rb")
        image_string = f.read()  
        print("\n\t% Loaded file: " + filename) 
    except:
        print("\t% Error: could not read binary")
        return 


CMD_FILTER_SELECT = "filter-apply"
CMD_FILTER_SELECT_SHORT = "fa"
selected_filters = []
filter_result = []
def filter_select(filter_numbers):    
    global global_filter_refs
    global selected_filters
    global scan_result
    global filter_result
    
    selected_filters = []
    filter_result = scan_result
    print('')
    if( len(filter_numbers) == 0 ):
        print("\t% Unselected all filters")
        return 
    elif( len(filter_result) == 0 ):
        print("\t% No SMS to filter")
        return 
    for num_arg in filter_numbers:
        try:
            num = int(num_arg)
        except:
            num = 9999
        if( num >= len(global_filter_refs)):
            print("\t% Ignored invalid filter number: {}".format(num_arg))
        else:
            # Filter it
            filter_result = global_filter_refs[num].filter(filter_result)
            selected_filters.append( num )
    selected_filters = list(set(selected_filters))

CMD_FILTER_LIST = "filter-list"
CMD_FILTER_LIST_SHORT = "fl"
def filter_list():
    global global_filter_refs
    global selected_filters
    print("\n\t-------------------------------")
    print("\t"+bold("SMS-Tool-Kit filters"))
    print("\t('"+green('*')+"'"+yellow(" indicate selected filters")+")")
    print("\t-------------------------------\n")
    
    if( len(global_filter_refs) == 0):
        print("\tNo filters are available")
        return 
        
    for i in range(0,len(global_filter_refs)):
        if( i in selected_filters ):
            selected = green('* ')
        else:
            selected = '  ' 
        print("\t{}.\t{}{}".format(i, selected, global_filter_refs[i].name))
       

CMD_PARSER_LIST = "parser-list"
CMD_PARSER_LIST_SHORT = "pl"
def parser_list():
    global global_parser_refs
    global selected_parsers
    print("\n\t-------------------------------")
    print("\t"+bold("SMS-Tool-Kit parsers"))
    print("\t('"+green('*')+"'"+yellow(" indicate selected parsers")+")")
    print("\t-------------------------------\n")
    
    if( len(global_parser_refs) == 0):
        print("\tNo parsers are available")
        return 
        
    for i in range(0, len(global_parser_refs)):
        if( i in selected_parsers):
            selected = green('* ')
        else:
            selected = '  ' 
        
        print("\t{}.\t{}{}".format(i, selected, global_parser_refs[i].name))

CMD_QUIT = "quit"
CMD_QUIT_SHORT = "q"

CMD_HELP = "help"
CMD_HELP_SHORT = "h"
def show_help():
    print("\n\t-------------------------")
    print("\t"+bold("SMS-Tool-Kit commands"))
    print("\t---------------------------\n")  

    print("\n\t"+bold(CMD_LOAD)+', '+bold(CMD_LOAD_SHORT)+\
        ":\t\tLoad a binary image to parse")
    
    print("\n\t"+bold(CMD_PARSER_LIST)+', '+bold(CMD_PARSER_LIST_SHORT)+\
        ":\tShow available SMS parsers")
    print("\n\t"+bold(CMD_PARSER_RUN)+', '+bold(CMD_PARSER_RUN_SHORT)+\
        ":\t\tRun parsers on the loaded image"+\
        "\n\t\t\t\t"+bold("Usage: ")+CMD_PARSER_RUN_SHORT+" <parser_num> [<parser_nums>]") 
    
    print("\n\t"+bold(CMD_FILTER_LIST)+', '+bold(CMD_FILTER_LIST_SHORT)+\
        ":\tShow available SMS filters")
    print("\n\t"+bold(CMD_FILTER_SELECT)+', '+bold(CMD_FILTER_SELECT_SHORT)+\
        ":\tApply SMS filters"+\
        "\n\t\t\t\t"+bold("Usage: ")+CMD_FILTER_SELECT_SHORT+" <filter_num> [<filter_nums>]")
    
    print("\n\t"+bold(CMD_EXPORT_EXCEL)+', '+bold(CMD_EXPORT_EXCEL_SHORT)+\
        ":\tExport SMS in an excel file"+\
        "\n\t\t\t\t"+bold("Usage: ")+CMD_EXPORT_EXCEL_SHORT+" <filename>")
    
    print("\n\t"+bold(CMD_HELP)+', '+bold(CMD_HELP_SHORT)+\
        ":\t\tShow this help")
    
    print("\n\t"+bold(CMD_QUIT)+', '+bold(CMD_QUIT_SHORT)+\
        ":\t\tQuit the SMS-Tool-Kit")
 
CMD_PARSER_RUN = "parser-run"
CMD_PARSER_RUN_SHORT = "pr"
selected_parsers = []
scan_result = [] # List of parsed SMS
def parser_run(parser_numbers):
    global selected_parsers
    global global_parser_refs
    global scan_result
    global filter_result
    global image_string
    
    selected_parsers = []
    res = []
    if( not image_string ):
        print("You must load a binary before running parsers :) ")
        return
    print('')
    for num_arg in parser_numbers:
        try:
            num = int(num_arg)
        except:
            num = 9999
        if( num >= len(global_parser_refs)):
            print("\t% Ignored invalid parser number: {}".format(num_arg))
        else:
            res += global_parser_refs[num].parse(image_string)
            selected_parsers.append (num )
    
    selected_parsers = list(set(selected_parsers))
    scan_result = res
    filter_result = res
    print(bold("\t% Found {} SMS".format(len(res))))
        
    
CMD_EXPORT_EXCEL = "export-excel"
CMD_EXPORT_EXCEL_SHORT = "ee"
def export_excel(filename):
    global filter_result
    try:
        import openpyxl
    except:
        print("\tError: package 'openpyxl' missing, could not export sms")
        exit(1)
        
    out = openpyxl.Workbook()
    out.active.title = "SMS Scan Results"
    out.active.append(["Offset in binary", "Status", "Number", "Data", "Date (DD:MM:YYYY HH:MM:SS UTC)", "Date (UTC+00)"])
    for sms in filter_result:
        out.active.append(sms.excel_output())
    out.save(filename)
    print("{} SMS saved in file: {}".format(str(len(filter_result)), filename))
    
    
def main():
    finish = False
    while(not finish):
        user_input = raw_input('\n>>> ')
        user_args = user_input.split()
        if( not user_args ):
            continue
        command = user_args[0]
        if( command in [CMD_LOAD_SHORT, CMD_LOAD]):
            if( len(user_args) >= 2 ):
                load(user_args[1])
            else:
                print("Missing filename")
        elif( command in [CMD_FILTER_LIST, CMD_FILTER_LIST_SHORT] ):
            filter_list()
        elif( command in [CMD_PARSER_LIST, CMD_PARSER_LIST_SHORT]):
            parser_list()
        elif( command in [CMD_PARSER_RUN, CMD_PARSER_RUN_SHORT]):
            if( len(user_args) >= 2 ):
                parser_run(user_args[1:])
            else:
                print("Missing parser numbers")
        elif( command in [CMD_FILTER_SELECT, CMD_FILTER_SELECT_SHORT]):
            if( len(user_args) >= 2 ):
                filter_select(user_args[1:])
            else:
                filter_select([])
        elif( command in [CMD_QUIT, CMD_QUIT_SHORT]):
            finish = True
        elif( command in [CMD_HELP, CMD_HELP_SHORT]):
            show_help()
        elif( command in [CMD_EXPORT_EXCEL, CMD_EXPORT_EXCEL_SHORT]):
            if( len(user_args) >= 2 ):
                export_excel(user_args[1])
            else:
                print("Missing excel file name")
        else:
            print('Unknown command')


# ------------------------------------------------------
#
#                    Parser Land
#                    ----------- 
#
# Here you can define your own parsing functions and 
# declare your own parsers 
#
#           How do I declare a new parser ? 
#           -------------------------------
#
# To declare a new parser, you simply have to create a new
# instance of the 'Parser' class. A parser takes 3 arguments: 
#  - name : a string, the name of the parser
#  - sms_type : an instance of the 'SMSType' class defined in 
#               Framework-Land, it is the type of SMS you want
#               to parse (like SMS_PDU ;) ) 
#  - a list of parsing functions : the functions that the parser
#               will succesively use to parse a SMS 
# For example, you can declare a parser by adding a line like :
#   -> my_parser = Parser("my new parser", SMSType.SMS_PDU, [\
#                    parsing_func_1, parsing_func_2, parsing_func_3])
#
#        How do I define my parsing functions ?
#        -------------------------------------- 
#
# In order to define a parser, you first need to define parsing 
# functions or use already defined parsing functions.
# A parsing function MUST take 3 arguments : 
#  - img : a string of bytes representing the binary image
#          to analyze. img[i] corresponds to the byte number 
#          i in the binary file
#   
#  - ind : the index in 'img' from where the parsing
#          must start. The first byte the parsing function will 
#          look at is img[ind]  
#          
#  - sms : the 'SMS' instance where to save the information that is
#          being parsed. For example if the function parses a date,
#          it will store it in sms.date ;).
#
# A parsing function MUST return 1 value : it returns the number 
# of bytes it has parsed. If the parsing functions parses a field
# of length 3, it returns 3, if length 7 it returns 7, etc. 
# If the function fails to parse the desired field the value 'ERROR'
# is returned. 'ERROR' is defined in Framework-Land as '-1'  
#
# ------------------------------------------------------


######################
# Standard PDU SMS   #
######################
 
# Define your parsing functions here
# ----------------------------------
def parse_pdu_submit_header(img, ind, sms): 
    # Get the first octet
    if( ind >= len(img) ):
        return ERROR 
    sms.tp_header = ord(img[ind])
    if( sms.mti() != MTI_SUBMIT ):
        return ERROR
    else:
        sms.sms_status = "Sent"
        return 1

def parse_pdu_submit_mr(img,ind,sms):
    try:
        sms.tp_mr = ord(img[ind])
        return 1
    except:
        return ERROR

def parse_pdu_pi_dcs(img, ind, sms):
    # Get Protocol Identifier and Data Coding Scheme 
    if( ind > len(img)-2 ):
        return ERROR
    sms.tp_pi = ord(img[ind])
    sms.tp_dcs = ord(img[ind+1])
    return 2
        
def parse_pdu_submit_vp(img, ind, sms):

    # Get the TP-VP
    if( sms.vpf() == VPF_ENHANCED or sms.vpf() == VPF_ABSOLUTE ):
        if( ind > len(img)-7):
            return ERROR
        sms.tp_vp = img[ind:ind+7+1]
        return 7
        sms.sms_date = str_to_date(sms.vp(),check=True)
        sms.date_utc_00 = str_to_date_utc(sms.vp())
    elif( sms.vpf() == VPF_RELATIVE ):
        if( ind > len(img)-1):
            return ERROR
        sms.tp_vp = img[ind]
        return 1
    else:
        return 0

def parse_pdu_addr(img, ind, sms):
    """
    Description
    -----------
    Parse an address field (some info + phone number)
    The mode parameters is used because some phone do not use
    the standard PDU format. They specify custom 'address length'
    field, so each custom format is decribe with a mode. 
    
    mode 1 : normal PDU format
    mode 2 : the length specified is for the (EXT,TON,NPI) byte + address digits
    
    Parameters
    ----------
    img : string of bytes
    ind : int
    sms : SMS
    mode : int. 
    
    Return
    ------
    If success: length in bytes of the address field
    If failure: -1 
    """
    
    
     # Get the addr length in octets
    addr_len = (ord(img[ind])+1)/2
    if( addr_len > 12 ):
        return ERROR
    else:
        ind = ind + 1
        sms.addr_len = addr_len
        
    if( addr_len == 0 ):
        return 2
    
    # Check if end of binary 
    if( ind+addr_len > len(img)):
        return ERROR
        
    # Check the type of address
    ton = (ord(img[ind]) & 0b01110000) >> 4
    # Get the number
    nibbles = img[ind+1:ind+1+addr_len]
    num = nibble_to_str(nibbles)
    if( not num ):
        return ERROR
    if( ton == TON_INTERNATIONAL ):
        num = "+"+num
    if( sms.mti() == MTI_SUBMIT ):
        sms.dst = num
    elif( sms.mti() == MTI_DELIVER ):
        sms.src = num
    return addr_len+2
 
def parse_pdu_user_data(img, ind, sms):
    # Get the user data length 
    if( ind > len(img)-1 ):
        return False
    sms.tp_udl = ord(img[ind])
    if( sms.udl() == 0 ):
        return False
    ind = ind + 1
    
    # Get the user data 
    if( ind > len(img) - sms.udl() ):
        return False
    sms.tp_ud = img[ind:ind+sms.udl()]
    if( sms.data_format() in DCS_ASCII8 ):
        sms.msg = sms.ud().decode('ascii', errors='replace')[:sms.udl()]
    elif( sms.data_format() in DCS_UCS2 ):
        sms.msg = sms.ud().decode('utf-16', errors='replace')[:sms.udl()]
    elif( sms.data_format() in DCS_GSM7 ):
        sms.msg = gsm7_decode(sms.ud())[:sms.udl()]
    else:
        return False
    
    return True

def parse_pdu_deliver_header(img,ind,sms):
    # Get the first octet
    if( ind >= len(img) ):
        return ERROR 
    sms.tp_header = ord(img[ind])
    if( sms.mti() != MTI_DELIVER ):
        return ERROR
    else:
        sms.sms_status = "Received"
        return 1
        
def parse_pdu_deliver_scts(img, ind, sms):
    # Get the Service Center Time Stamp
    if( ind > len(img)-7):
        return ERROR
    sms.tp_scts = img[ind:ind+7+1]
    sms.sms_date = str_to_date(sms.scts(),check=True)
    sms.date_utc_00 = str_to_date_utc(sms.scts())
    return 7 

# Declare your parsers here
# -------------------------

pdu_submit_parser = Parser("SMS-PDU-Submit", SMSType.SMS_PDU, [\
    parse_pdu_submit_header,\
    parse_pdu_submit_mr,\
    parse_pdu_addr,\
    parse_pdu_pi_dcs,\
    parse_pdu_submit_vp,\
    parse_pdu_user_data
    ])

pdu_deliver_parser = Parser("SMS-PDU-Deliver", SMSType.SMS_PDU, [\
    parse_pdu_deliver_header,\
    parse_pdu_addr,\
    parse_pdu_pi_dcs,\
    parse_pdu_deliver_scts,\
    parse_pdu_user_data
    ])


# ------------------------------------------------------
#
#                    Filter Land
#                    ----------- 
#
# Here you can define your own filtering functions and 
# declare your own filters. 
#
#             How do I declare a new filter ?
#             -------------------------------
#
# To declare a new filter, you have to create an new instance
# of the 'Filter' class. You need to give it 2 arguments:
#  - name : a string, the name of the filter
#  
#  - a list of filtering functions : the filter will apply all 
#       the filtering functions to each SMS. If the SMS passes
#       all the tests, it is selected, otherwise it is 
#       removed. (You can see a Filter as a combinaison of 
#       filtering functions ;) )
#
# For example you can declare a new filter with the line: 
# -> my_filter = Filter('my filter', [filter_date, filter_number\
#               , filter_msg_len])
#
#
#         How fo I declare my filtering functions ?
#         -----------------------------------------
#
# Declaring a filtering function is really simple. A filtering
# function MUST take only one argument : a 'SMS' instance. 
# Then, the function MUST return True of False. YOu can do 
# any treatment in the functions body as long as it always 
# returns True (SMS passes the test) or False (SMS is not good) 
#
# ------------------------------------------------------

# Define your filtering functions here
# -------------------------------------
class LanguageSymbolSignature:
    """
    Description
    -----------
    LanguageSymbolSignature stores a list of intervals (integers)
    Each interval represents a set of unicode characters
    Those characters are 'typical' and the most common of the language
        that we want to describe
    This enables to test the likelihood for a potential parsed PDU msg
        to be a valid message by checking if its chars belong to the 
        language or not 
    """
    
    def __init__(self, intervals=None):
        """
        Parameters
        ----------
        intervals : (int,int)
        """
        if( not intervals):
            self.char_intervals = []
        else:
            self.char_intervals = intervals
            
    def belongs(self, char):
        """
        Description
        -----------
        Checks if a character belongs to the language signature
        """
        for interval in self.char_intervals:
            if( ord(char) >= interval[0] and ord(char) <= interval[1]):
                return True
        return False

def filter_lang_latin(sms):
    """
    Description
    -----------
        
    Parameters
    ----------
    sms : SMS
    lang : LanguageSymbolSignature
    
    Returns
    -------
    True | False
    """
    if( len(sms.message()) == 0 ):
        return False
    percentage = 0.92
    yes = 0
    no = 0
    lang = LanguageSymbolSignature([(0x20, 0x7f), (0xc0, 0x17f)]) 
    for char in sms.message():
        if( lang.belongs(char)):
            yes = yes + 1
        else:
            no = no + 1
    p = float(yes)/float(len(sms.message()))
    if( p > percentage ):
        return True
    else:
        return False

def filter_date(sms):
    """
    Description
    -----------
    Filters only SMS that have a valid date
    """
    return sms.sms_date != None


# Declare your filters here
# -------------------------
pdu_filter_classical = Filter("PDU-classical",[\
    filter_lang_latin,\
    filter_date])



# --------------------------
#
# Tiny Framework-Land:
# just executing the script :)  
#
# --------------------------
main()
exit()
