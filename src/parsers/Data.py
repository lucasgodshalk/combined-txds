"""Data structures and read/write methods for input and output data file formats

Author(s):
    Jesse Holzer, jesse.holzer@pnnl.gov
    Victoria Ciplickas

Date Created: 2018-04-05
Date Modified: 2019-06

"""
# data.py
# module for input and output data
# including data structures
# and read and write functions

import csv
import os
import sys
import math
import traceback
import re
from io import StringIO
    
    

#this file only contains the framework necessary to read RAW files
#and cannot handle .INL, .CON, etc    

 
#prints an alert
def alert(alert_dict):
    print(alert_dict)
    
#gets a value from a specific place on a line and turns it into the desired value type
def parse_token(token, val_type, default=None, isIntFloat = False):
    val = None
    if len(token) > 0:
        if isIntFloat:
            token = re.search(r'\d+', token).group()
        val = val_type(token)
    elif default is not None:
        val = val_type(default)
    else:
        try:
            print('required field missing data, token: %s, val_type: %s' % (token, val_type))
            raise Exception('empty field not allowed')
        except Exception as e:
            traceback.print_exc()
            raise e
        #raise Exception('empty field not allowed')
    return val

#removes comments at the end of the row, and raises an exception if 
#the row is missing/has extra fields
def pad_row(row, new_row_len):

    try:
        if len(row) != new_row_len:
            print(len(row), new_row_len)
            if len(row) < new_row_len:
                print('missing field, row:')
                print(row)
                raise Exception('missing field not allowed')
            elif len(row) > new_row_len:
                row = remove_end_of_line_comment_from_row(row, '/')
                '''if len(row) > new_row_len:
                    alert(
                        {'data_type': 'Data',
                         'error_message': 'extra field, please ensure that all rows have the correcct number of fields',
                         'diagnostics': str(row)})'''
                    
        else:
            row = remove_end_of_line_comment_from_row(row, '/')
    except Exception as e:
        traceback.print_exc()
        raise e
    return row
    

#adds blanks to the end of the row to make parsing easier
def make_full_row(row, new_row_len):
    row_len = len(row)
    row_len_diff = new_row_len - row_len
    row_new = row
    if row_len_diff > 0:
        row_new = row + row_len_diff * ['']
    return row_new
    

#checks if the row is missing fields
def check_row_missing_fields(row, row_len_expected):

    try:
        if len(row) < row_len_expected:
            print('missing field, row:')
            print(row)
            raise Exception('missing field not allowed')
    except Exception as e:
        traceback.print_exc()
        raise e


def remove_end_of_line_comment_from_row_first_occurence(row, end_of_line_str):

    index = [r.find(end_of_line_str) for r in row]
    len_row = len(row)
    entries_with_end_of_line_strs = [i for i in range(len_row) if index[i] > -1]
    num_entries_with_end_of_line_strs = len(entries_with_end_of_line_strs)
    if num_entries_with_end_of_line_strs > 0:
        first_entry_with_end_of_line_str = min(entries_with_end_of_line_strs)
        len_row_new = first_entry_with_end_of_line_str + 1
        row_new = [row[i] for i in range(len_row_new)]
        row_new[len_row_new - 1] = remove_end_of_line_comment(row_new[len_row_new - 1], end_of_line_str)
    else:
        row_new = [r for r in row]
    return row_new

def remove_end_of_line_comment_from_row(row, end_of_line_str):

    index = [r.find(end_of_line_str) for r in row]
    len_row = len(row)
    entries_with_end_of_line_strs = [i for i in range(len_row) if index[i] > -1]
    num_entries_with_end_of_line_strs = len(entries_with_end_of_line_strs)
    if num_entries_with_end_of_line_strs > 0:
        #last_entry_with_end_of_line_str = min(entries_with_end_of_line_strs)
        #len_row_new = last_entry_with_end_of_line_str + 1
        row_new = [r for r in row]
        #row_new = [row[i] for i in range(len_row_new)]
        for i in entries_with_end_of_line_strs:
            row_new[i] = remove_end_of_line_comment(row_new[i], end_of_line_str)
        #row_new[len_row_new - 1] = remove_end_of_line_comment(row_new[len_row_new - 1], end_of_line_str)
    else:
        #row_new = [r for r in row]
        row_new = row
    return row_new

def remove_end_of_line_comment(token, end_of_line_str):
    
    token_new = token
    index = token_new.find(end_of_line_str)
    if index > -1:
        token_new = token_new[0:index]
    return token_new
    
#data class 

class Data:
    '''In physical units, i.e. data convention, i.e. input and output data files'''
    #here read/write for other file types (.INL, .CON) can be added
    def __init__(self):

        self.raw = Raw()
        

    def read(self, raw_name):

        self.raw.read(raw_name)

    def write(self, raw_name):

        self.raw.write(raw_name)
        


    
#RAW file class 

class Raw:
    '''In physical units, i.e. data convention, i.e. input and output data files'''

    def __init__(self):

        self.case_identification = CaseIdentification()
        self.buses = {}
        self.loads = {}
        self.fixed_shunts = {}
        self.generators = {}
        self.nontransformer_branches = {}
        self.transformers = {}
        self.areas = {}
        self.switched_shunts = {}
        self.zones = {}
        self.owners = {}
        self.interareas = {}
        self.vsc = {}
        self.two_terminal = {}
        self.facts_device = {}
        self.multi_section_lines = {}
        self.imp_corr_tables = {}
        self.two_wind_xfmrs = {}
        self.three_wind_xfmrs = {}
        self.slack_buses = []
        
    #all of the "get" functions reference the classes of the type they are getting 
    def get_buses(self):
        return sorted(self.buses.values(), key=(lambda r: r.i))

    def get_loads(self):

        return sorted(self.loads.values(), key=(lambda r: (r.i, r.id)))

    def get_fixed_shunts(self):

        return sorted(self.fixed_shunts.values(), key=(lambda r: (r.i, r.id)))

    def get_generators(self):

        return sorted(self.generators.values(), key=(lambda r: (r.i, r.id)))

    def get_nontransformer_branches(self):

        return sorted(self.nontransformer_branches.values(), key=(lambda r: (r.i, r.j, r.ckt)))

    def get_two_xfmrs(self):

        return sorted(self.two_wind_xfmrs.values(), key=(lambda r: (r.i, r.j, r.k, r.ckt)))
        
    def get_three_xfmrs(self):
        
        return sorted(self.three_wind_xfmrs.values(), key=(lambda r: (r.i, r.j, r.k, r.ckt)))

    def get_areas(self):

        return sorted(self.areas.values(), key=(lambda r: r.i))
        
    def get_switched_shunts(self):

        return sorted(self.switched_shunts.values(), key=(lambda r: r.i))
        
    def get_zones(self):
        return sorted(self.zones.values(), key = (lambda r: r.i))
        
    def get_owners(self):
        return sorted(self.owners.values(), key = (lambda r: r.i))
        
    def get_interareas(self):
        return sorted(self.interareas.values(), key = (lambda r: (r.arfrom, r.arto, r.trid)))
        
    def get_vsc(self):
        return sorted(self.vsc.values(), key = (lambda r: r.name))
    
    def get_two_term_dc(self):
        return sorted(self.two_terminal.values(), key = (lambda r: (r.name, r.ipi, r.ipi)))
        
    def get_facts_device(self):
        return sorted(self.facts_device.values(), key = (lambda r: (r.i,r.j)))
        
    def get_multi_section_line(self):
        return sorted(self.multi_section_lines.values(), key = (lambda r: (r.i, r.j, r.id)))
        
    def get_ic_tables(self):
        return sorted(self.imp_corr_tables.values(), key = (lambda r: r.i))

    ### Writing ###
    

    
    def switched_shunts_combine_blocks_steps(self):

        for r in self.switched_shunts.values():
            b_min_max = r.compute_bmin_bmax()
            b_min = b_min_max[0]
            b_max = b_min_max[1]
            r.n1 = 0
            r.b1 = 0.0
            r.n2 = 0
            r.b2 = 0.0
            r.n3 = 0
            r.b3 = 0.0
            r.n4 = 0
            r.b4 = 0.0
            r.n5 = 0
            r.b5 = 0.0
            r.n6 = 0
            r.b6 = 0.0
            r.n7 = 0
            r.b7 = 0.0
            r.n8 = 0
            r.b8 = 0.0
            if b_max > 0.0:
                r.n1 = 1
                r.b1 = b_max
                if b_min < 0.0:
                    r.n2 = 1
                    r.b2 = b_min
            elif b_min < 0.0:
                r.n1 = 1
                r.b1 = b_min
    ### Reading ###
    def find_delim(self, lines): #finds if the delimiter is space or comma
        first_line = lines[0]
        if "," in first_line:
            return ","
        else:
            return " "
    
    #reads the raw file
    def read(self, file_name):

        with open(file_name, 'r') as in_file:
            lines = in_file.readlines()
        delimiter_str = self.find_delim(lines)
        
        quote_str = "'"
        skip_initial_space = True
        rows = csv.reader(
            lines,
            delimiter=delimiter_str,
            quotechar=quote_str,
            skipinitialspace=skip_initial_space)
        rows = [[t.strip() for t in r] for r in rows]
        self.read_from_rows(rows, file_name)
        #self.set_areas_from_buses()
     
     #checks of a row is the end of the whole file   
    def row_is_file_end(self, row):

        is_file_end = False
        if len(row) == 0:
            is_file_end = True
        if row[0][:1] in {'','q','Q'}:
            is_file_end = True
        return is_file_end
    
    #checks if a row is the end of a data type/start of a new data type
    def row_is_section_end(self, row): 
        temp_row = ' '.join(row)
        new_row = remove_end_of_line_comment(temp_row, ' /')
        
        is_section_end = False
        if (new_row == '0'):
            is_section_end = True
        return is_section_end
        
    def row_is_key(self, row):
        if row[0][0] == '@':
            return True
        return False
    
    #actually does the work of reading from the raw file
    
    
    def read_from_rows(self, rows, file_name):
        
        row_num = 0
        if self.row_is_key(rows[row_num]):
            row_num += 1
        cid_rows = rows[row_num:(row_num + 3)]
        self.case_identification.record_2 = ' '.join(cid_rows[1])
        self.case_identification.record_3 = ' '.join(cid_rows[2])
        #case ID data
        if len(rows[row_num]) == 2:
            self.case_identification.read_from_rows(rows, 30)
        else:
            self.case_identification.read_from_rows(rows)
        version = self.case_identification.rev
        row_num += 2
        
        if version == 34:
            while True: #system wide data
                row_num += 1
                row = rows[row_num]
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
        while True: #bus data
            
            row_num += 1
            row = rows[row_num]
            while True:
                
                
                if rows[row_num][0][0] == '@':
                    
                    row_num += 1
                else:
                    
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            bus = Bus(version)
            bus.read_from_row(row, version)
            self.buses[bus.i] = bus
            if bus.ide == 3:
                #print(bus.i)
                self.slack_buses.append(bus.i)
        s_r = row_num
        while True: #load data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            load = Load(version)
            load.read_from_row(row, version)
            self.loads[(load.i, load.id)] = load
        if version != 30: #version 30 does not have fixed bus shunt data
            while True: #fixed bus shunt data
                row_num += 1
                row = rows[row_num]
                while True:
                    if rows[row_num][0][0] == '@':
                        row_num += 1
                    else:
                        break
                row = rows[row_num]
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
                row = rows[row_num]
                fixed_shunt = FixedShunt()
                fixed_shunt.read_from_row(row, version)
                self.fixed_shunts[(fixed_shunt.i, fixed_shunt.id)] = fixed_shunt
        while True: #generator data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            generator = Generator()
            generator.read_from_row(row, version)
            self.generators[(generator.i, generator.id)] = generator
        while True: #branch data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            nontransformer_branch = NontransformerBranch()
            nontransformer_branch.read_from_row(row, version)
            self.nontransformer_branches[(
                nontransformer_branch.i,
                nontransformer_branch.j,
                nontransformer_branch.ckt)] = nontransformer_branch
                
        if version == 34:
            while True: #system switching device data
                row_num += 1
                row = rows[row_num]
                while True:
                    if rows[row_num][0][0] == '@':
                        row_num += 1
                    else:
                        row = rows[row_num]
                        break
                
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
                    
        while True: #transformer data
            row_num += 1
            row = rows[row_num]
            
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            
            
            if row[2] == '0': #two winding transformer
                two_xfmr = Two_xfmr(version)
                row2 = rows[row_num+1]
                row3 = rows[row_num+2]
                row4 = rows[row_num+3]
                two_xfmr.read_from_row(row,row2, row3, row4, version)
                self.two_wind_xfmrs[two_xfmr.i, two_xfmr.j, two_xfmr.ckt] = two_xfmr
                row_num += 3
            else: #three winding transformer
                three_xfmr = Three_xfmr()
                row2 = rows[row_num+1]
                row3 = rows[row_num+2]
                row4 = rows[row_num+3]
                row5 = rows[row_num+4]
                three_xfmr.read_from_row(row, row2, row3, row4, row5, version)
                self.three_wind_xfmrs[three_xfmr.i, three_xfmr.j, three_xfmr.k, three_xfmr.ckt] = three_xfmr
                row_num += 4
                
        while True: # areas 

            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            area = Area()
            area.read_from_row(row, version)
            self.areas[area.i] = area
            
        while True: #two-terminal DC transmission line data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            row2 = rows[row_num+1]
            row3 = rows[row_num+2]
            two_term_dc_line = Two_terminal_dc()
            two_term_dc_line.read_from_row(row, row2, row3, version)
            self.two_terminal[(two_term_dc_line.name, two_term_dc_line.ipr, two_term_dc_line.ipi)] = two_term_dc_line
            row_num +=2
        while True: #VSC DC transmission line data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
                
            vsc_dc_line = VSC()
            row = rows[row_num]
            row2 = rows[row_num+1]
            row3 = rows[row_num+2]
            vsc_dc_line.read_from_row(row, row2, row3, version)
            self.vsc[vsc_dc_line.name] = vsc_dc_line
            row_num += 2
        if version == 30:
            while True: #switched shunt data
                row_num += 1
                row = rows[row_num]
                while True:
                    if rows[row_num][0][0] == '@':
                        row_num += 1
                    else:
                        break
                row = rows[row_num]
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
                row = rows[row_num]
                switched_shunt = SwitchedShunt()
                switched_shunt.read_from_row(row, version)
                self.switched_shunts[switched_shunt.i] = switched_shunt
        while True: #xfmr impedance corr. tables
            
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            if version == 3:
                break
            row = rows[row_num]
            ic_table = Impedance_corr()
            ic_table.read_from_row(row, version)
            self.imp_corr_tables[ic_table.i] = ic_table
        while True: #Multi-terminal DC transmission line data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
        while True: #multi-section line grouping data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            ms_line_grouping = Multi_section_line_grouping()
            ms_line_grouping.read_from_row(row, version)
            self.multi_section_lines[(ms_line_grouping.i, ms_line_grouping.j, ms_line_grouping.id)] =ms_line_grouping
        while True: # zone data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            zone = Zone()
            zone.read_from_row(row, version)
            self.zones[zone.i] = zone
        while True: #interarea transfer data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            interarea = Interarea_transfer()
            interarea.read_from_row(row, version)
            self.interareas[(interarea.arfrom, interarea.arto, interarea.trid)] = interarea
        while True: #owner data
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            owner = Owner()
            owner.read_from_row(row, version)
            self.owners[owner.i] = owner
        while True: #facts device data 
            row_num += 1
            row = rows[row_num]
            while True:
                if rows[row_num][0][0] == '@':
                    row_num += 1
                else:
                    break
            row = rows[row_num]
            if self.row_is_file_end(row):
                return
            if self.row_is_section_end(row):
                break
            row = rows[row_num]
            fact = FACTS_device()
            fact.read_from_row(row, version)
            self.facts_device[(fact.i,fact.j)] = fact
        if version != 30:
            while True: #switched shunt data
                row_num += 1
                row = rows[row_num]
                while True:
                    if rows[row_num][0][0] == '@':
                        row_num += 1
                    else:
                        break
                row = rows[row_num]
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
                row = rows[row_num]
                switched_shunt = SwitchedShunt()
                switched_shunt.read_from_row(row, version)
                self.switched_shunts[switched_shunt.i] = switched_shunt
        if version == 34 or version == 33:
            while True: #GNE device data
                row_num += 1
                row = rows[row_num]
                while True:
                    if rows[row_num][0][0] == '@':
                        row_num += 1
                    else:
                        break
                if self.row_is_file_end(row):
                    return
                if self.row_is_section_end(row):
                    break
                row = rows[row_num]
            if version == 34:
                while True: #induction machine data
                    row_num += 1
                    row = rows[row_num]
                    while True:
                        if rows[row_num][0][0] == '@':
                            row_num += 1
                        else:
                            break
                    if self.row_is_file_end(row):
                        return
                    if self.row_is_section_end(row):
                        break
                    row = rows[row_num]
                while True: #substation data
                    row_num += 1
                    row = rows[row_num]
                    while True:
                        if rows[row_num][0][0] == '@':
                            row_num += 1
                        else:
                            break
                    if self.row_is_file_end(row):
                        return
                    if self.row_is_section_end(row):
                        break
                    row = rows[row_num]
       
       
#### Data Type Classes ####           

 
class CaseIdentification:

    def __init__(self):

        self.ic = 0
        self.sbase = 100.0
        self.rev = 33
        self.xfrrat = 0
        self.nxfrat = 1
        self.basfrq = 60.0
        self.record_2 = 'GRID OPTIMIZATION COMPETITION'
        self.record_3 = 'INPUT DATA FILES ARE RAW '

   
    def read_record_1_from_row(self, row, rev = 33):
        if rev == 30:
            self.ic = parse_token(row[0], int, 0)
            self.sbase = parse_token(row[1], float, default=None)
            self.rev = 30
        else:
            row = row[0:6]
            row = pad_row(row, 6)
            row[5] = remove_end_of_line_comment(row[5], '/')
            
            self.sbase = parse_token(row[1], float, default=None)
        
            self.ic = parse_token(row[0], int, 0)
            self.rev = parse_token(row[2], int, 33)
            #self.xfrrat = (1 if (parse_token(row[3], float, 0.0) > 0.0) else 0)
            #self.nxfrat = (1 if (parse_token(row[4], float, 1.0) > 0.0) else 0)
            self.xfrrat = parse_token(row[3], int, 0)
            self.nxfrat = parse_token(row[4], int, 1)
            self.basfrq = parse_token(row[5], float, 60.0) # need to remove end of line comment

    def get_other_records(self, row1, row2):
        self.record_2 = row1
        self.record_3 = row2
        
    def read_from_rows(self, rows, rev = 33):
        row_num = 0
        while True:
            if rows[row_num][0][0] == '@':
                row_num += 1
            else:
                break
       
        self.read_record_1_from_row(rows[row_num], rev)
        #self.record_2 = '' # not preserving these at this point
        #self.record_3 = '' # do that later

class Bus:

    def __init__(self, version = 32):

        self.i = None # no default allowed - we want this to throw an error
        self.name = 12*' '
        self.baskv = 0.0
        self.ide = 1
        self.area = 1
        self.zone = 1
        self.owner = 1
        self.vm = 1.0
        self.va = 0.0
        self.version = version
        if self.version in (33, 34):
            self.nvhi = 1.1
            self.nvlo = 0.9
            self.evhi = 1.1
            self.evlo = 0.9
        if self.version == 30:
            self.gl = 0.0
            self.bl = 0.0

    def clean_name(self):

        self.name = ''

    def read_from_row(self, row, rev):
        goal_rows = 9
        if rev == 32:
            goal_rows = 9
        elif rev == 34 or rev==33:
            goal_rows = 13
        elif rev == 30:
            goal_rows = 11
       
        row = pad_row(row, goal_rows)
        if rev == 30:
            self.i = parse_token(row[0], int, default=None)
            self.name = parse_token(row[1], str, 12*' ')
            self.baskv = parse_token(row[2], float, 0.0)
            self.ide = parse_token(row[3], int, 1)
            self.gl = parse_token(row[4], float, default=0.0)
            self.bl = parse_token(row[5], float, default=0.0)
            self.area = parse_token(row[6], int, default=1)
            self.zone = parse_token(row[7], int, 1)
            self.vm = parse_token(row[8], float, default=1.0)
            self.va = parse_token(row[9], float, default=0.0)
            self.owner = parse_token(row[10], int, 1)
        else:
            self.i = parse_token(row[0], int, default=None)
            self.area = parse_token(row[4], int, default=1)
            self.vm = parse_token(row[7], float, default=1.0)
            self.va = parse_token(row[8], float, default=0.0)
            if id in (33, 34):
                self.nvhi = parse_token(row[9], float, default=1.1)
                self.nvlo = parse_token(row[10], float, default=0.9)
                self.evhi = parse_token(row[11], float, default=1.1)
                self.evlo = parse_token(row[12], float, default=0.9)
        
            self.name = parse_token(row[1], str, 12*' ')
            self.baskv = parse_token(row[2], float, 0.0)
            self.ide = parse_token(row[3], int, 1)
            self.zone = parse_token(row[5], int, 1)
            self.owner = parse_token(row[6], int, 1)
        
    
class Load:

    def __init__(self, version = 32):

        self.i = None # no default allowed - should be an error
        self.id = '1'
        self.status = 1
        self.area = 1 # default is area of bus self.i, but this is not available yet
        self.zone = 1
        self.pl = 0.0
        self.ql = 0.0
        self.ip = 0.0
        self.iq = 0.0
        self.yp = 0.0
        self.yq = 0.0
        self.owner = 1
        self.scale = 1
        if version == 33:
            pass
            #self.intrpt = 0
        if version == 34:
            #self.intrpt = 0
            self.dgenp = 0.0
            self.dgenq = 0.0
            self.dgenm = 0
        

   

    def clean_rev(self):
        '''remove spaces and non-allowed characters
        hope that this does not introduce duplication'''

        self.rev = clean_short_str(self.id)

    def read_from_row(self, row, rev):

        #row = pad_row(row, 13)
        self.i = parse_token(row[0], int, default=None)
        self.id = parse_token(row[1], str, default='1').strip()
        self.status = parse_token(row[2], int, default=1)
        self.pl = parse_token(row[5], float, default=0.0)
        self.ql = parse_token(row[6], float, default=0.0)
    
        self.area = parse_token(row[3], int, 1)
        self.zone = parse_token(row[4], int, 1)
        self.ip = parse_token(row[7], float, 0.0)
        self.iq = parse_token(row[8], float, 0.0)
        self.yp = parse_token(row[9], float, 0.0)
        self.yq = parse_token(row[10], float, 0.0)
        self.owner = parse_token(row[11], int, 1)
        if rev != 30:
            self.scale = parse_token(row[12], int, 1)
        if rev == 33:
            if len(row) == 12:
                self.intrp  =  parse_token(row[13], int, 0)
        if rev==34:
            pass
            '''#self.intrpt = parse_token(row[13], int, 0)
            self.dgenp = parse_token(row[14], float, 0.0)
            self.dgenq = parse_token(row[15], float, 0.0)
            self.dgenm = parse_token(row[15], float, 0) '''
        

class FixedShunt:

    def __init__(self):

        self.i = None # no default allowed
        self.rev = '1'
        self.status = 1
        self.gl = 0.0
        self.bl = 0.0

   

    def check_id_len_1_or_2(self):

        if not(len(self.id) in [1, 2]):
            alert(
                {'data_type': 'FixedShunt',
                 'error_message': 'fails id string len 1 or 2. Please ensure that the id field of every fixed shunt is a 1- or 2-character string with no blank characters',
                 'diagnostics': {
                     'i': self.i,
                     'id': self.id}})

    def read_from_row(self, row, id):

        #row = pad_row(row, 5)
        self.i = parse_token(row[0], int, default=None)
        self.id = parse_token(row[1], str, default='1').strip()
        self.status = parse_token(row[2], int, default=1)
        self.gl = parse_token(row[3], float, default=0.0)
        self.bl = parse_token(row[4], float, default=0.0)
        

class Generator:

    def __init__(self):
        self.i = None # no default allowed
        self.id = '1'
        self.pg = 0.0
        self.qg = 0.0
        self.qt = 9999.0
        self.qb = -9999.0
        self.vs = 1.0
        self.ireg = 0
        self.mbase = 100.0 # need to take default value for this from larger Raw class
        self.zr = 0.0
        self.zx = 1.0
        self.rt = 0.0
        self.xt = 0.0
        self.gtap = 1.0
        self.stat = 1
        self.rmpct = 100.0
        self.pt = 9999.0
        self.pb = -9999.0
        self.o1 = 1
        self.f1 = 1.0
        self.o2 = 0
        self.f2 = 1.0
        self.o3 = 0
        self.f3 = 1.0
        self.o4 = 0
        self.f4 = 1.0
        self.wmod = 0
        self.wpf = 1.0



    def read_from_row(self, row, rev):
        if len(row) < 16:
            print('error: data missing from generator')
        else:
            if rev != 30 and len(row)>26:
                self.wmod = parse_token(row[-2], int, 0, True)
                self.wpf = parse_token(row[-1], float, 0)
            if len(row)<28:
                diff = 28-len(row)
                row += ['']*diff
            #row = pad_row(row, 28)
            self.i = parse_token(row[0], int, default=None)
            self.id = parse_token(row[1], str, default='1').strip()
            self.pg = parse_token(row[2], float, default=0.0)
            self.qg = parse_token(row[3], float, default=0.0)
            self.qt = parse_token(row[4], float, default=9999.0)
            self.qb = parse_token(row[5], float, default=-9999.0)
            self.stat = parse_token(row[14], int, default=1)
            self.pt = parse_token(row[16], float, default=9999.0)
            self.pb = parse_token(row[17], float, default=-9999.0)
        
            self.vs = parse_token(row[6], float, 1.0)
            self.ireg = parse_token(row[7], int, 0)
            self.mbase = parse_token(row[8], float, 100.0)
            self.zr = parse_token(row[9], float, 0.0)
            self.zx = parse_token(row[10], float, 1.0)
            self.rt = parse_token(row[11], float, 0.0)
            self.xt = parse_token(row[12], float, 0.0)
            self.gtap = parse_token(row[13], float, 1.0)
            self.rmpct = parse_token(row[15], float, 100.0)
            self.o1 = parse_token(row[18], int, 1)
            self.f1 = parse_token(row[19], float, 1.0, True)
            self.o2 = parse_token(row[20], int, 0)
            self.f2 = parse_token(row[21], float, 1.0, True)
            self.o3 = parse_token(row[22], int, 0)
            self.f3 = parse_token(row[23], float, 1.0, True)
            self.o4 = parse_token(row[24], int, 0)
            self.f4 = parse_token(row[25], float, 1.0, True)

class NontransformerBranch:

    def __init__(self, version = 32):

        self.i = None # no default
        self.j = None # no default
        self.ckt = '1'
        self.r = None # no default
        self.x = None # no default
        self.b = 0.0
        self.ratea = 0.0
        self.rateb = 0.0
        self.ratec = 0.0
        self.gi = 0.0
        self.bi = 0.0
        self.gj = 0.0
        self.bj = 0.0
        self.st = 1
        self.met = 1
        self.len = 0.0
        self.o1 = 1
        self.f1 = 1.0
        self.o2 = 0
        self.f2 = 1.0
        self.o3 = 0
        self.f3 = 1.0
        self.o4 = 0
        self.f4 = 1.0
        if version == 34:
            self.name = ' '*12
   

    def read_from_row(self, row, rev):
        if rev == 34:
            if len(row)< 34:
                diff = 34-len(row)
                row += ['']*diff
            self.i = parse_token(row[0], int, default=None)
            self.j = parse_token(row[1], int, default=None)
            self.ckt = parse_token(row[2], str, default='1').strip()
            self.r = parse_token(row[3], float, default=None)
            self.x = parse_token(row[4], float, default=None)
            self.b = parse_token(row[5], float, default=0.0)
            self.name = parse_token(row[6], str, ' '*12)
            self.ratea = parse_token(row[7], float, default=0.0)
            self.rateb = parse_token(row[8], float, 0.0)
            self.ratec = parse_token(row[9], float, default=0.0)
            self.st = parse_token(row[23], int, default=None)
        
            
            self.gi = parse_token(row[19], float, 0.0)
            self.bi = parse_token(row[20], float, 0.0)
            self.gj = parse_token(row[21], float, 0.0)
            self.bj = parse_token(row[22], float, 0.0)
            self.met = parse_token(row[24], int, 1)
            self.len = parse_token(row[25], float, 0.0)
            self.o1 = parse_token(row[26], float, 1)
            self.f1 = parse_token(row[27], float, 1.0)
            self.o2 = parse_token(row[28], float, 0)
            self.f2 = parse_token(row[29], float, 1.0)
            self.o3 = parse_token(row[30], float, 0)
            self.f3 = parse_token(row[31], float, 1.0)
            self.o4 = parse_token(row[32], float, 0)
            self.f4 = parse_token(row[33], float, 1.0)
        else:
            if len(row)< 24:
                diff = 24-len(row)
                row += ['']*diff
            #row = pad_row(row, 24)
            self.i = parse_token(row[0], int, default=None)
            self.j = parse_token(row[1], int, default=None)
            self.ckt = parse_token(row[2], str, default='1').strip()
            self.r = parse_token(row[3], float, default=None)
            self.x = parse_token(row[4], float, default=None)
            self.b = parse_token(row[5], float, default=0.0)
            self.ratea = parse_token(row[6], float, default=0.0)
            self.rateb = parse_token(row[7], float, 0.0)
            self.ratec = parse_token(row[8], float, default=0.0)
            self.st = parse_token(row[13], int, default=None)
        
            
            self.gi = parse_token(row[9], float, 0.0)
            self.bi = parse_token(row[10], float, 0.0)
            self.gj = parse_token(row[11], float, 0.0)
            self.bj = parse_token(row[12], float, 0.0)
            self.met = parse_token(row[14], int, 1)
            self.len = parse_token(row[15], float, 0.0)
            self.o1 = parse_token(row[16], float, 1)
            self.f1 = parse_token(row[17], float, 1.0)
            self.o2 = parse_token(row[18], float, 0)
            self.f2 = parse_token(row[19], float, 1.0)
            self.o3 = parse_token(row[20], float, 0)
            self.f3 = parse_token(row[21], float, 1.0)
            self.o4 = parse_token(row[22], float, 0)
            self.f4 = parse_token(row[23], float, 1.0)
        
        


#two winding transformer
class Two_xfmr:
    
    def __init__(self, version):

        self.i = None # no default
        self.j = None # no default
        self.k = 0
        self.ckt = '1'
        self.cw = 1
        self.cz = 1
        self.cm = 1
        self.mag1 = 0.0
        self.mag2 = 0.0
        self.nmetr = 2
        self.name = 12*' '
        self.stat = 1
        self.o1 = 1
        self.f1 = 1.0
        self.o2 = 0
        self.f2 = 1.0
        self.o3 = 0
        self.f3 = 1.0
        self.o4 = 0
        self.f4 = 1.0
        
        self.r1_2 = 0.0
        self.x1_2 = None # no default allowed
        self.sbase1_2 = 100.0
        self.windv1 = 1.0
        self.nomv1 = 0.0
        self.ang1 = 0.0
        self.rata1 = 0.0
        self.ratb1 = 0.0
        self.ratc1 = 0.0
        self.cod1 = 0
        self.cont1 = 0
        self.rma1 = 1.1
        self.rmi1 = 0.9
        self.vma1 = 1.1
        self.vmi1 = 0.9
        self.ntp1 = 33
        self.tab1 = 0
        self.cr1 = 0.0
        self.cx1 = 0.0
        self.windv2 = 1.0
        self.nomv2 = 0.0
        
        if version in (33, 34):
            self.vecgrp = ' '*12
            self.cnxa1 = 0.0
    
    def read_from_row(self, row, row2, row3, row4, version):
        #two winding xfmrs have 4 rows of data 
        #row 1
        
        self.i = parse_token(row[0], str)
        self.j = parse_token(row[1], str)
        self.k = 0
        self.ckt = parse_token(row[3], str)
        self.cw = parse_token(row[4], int, 1)
        self.cz = parse_token(row[5], int, 1)
        self.cm = parse_token(row[6], int, 1)
        self.mag1 = parse_token(row[7], float, 0.0)
        self.mag2 = parse_token(row[8], float, 0.0)
        self.nmetr = parse_token(row[9], int, 2)
        self.name = parse_token(row[10], str, 12*' ')
        self.stat = parse_token(row[11], int, 1)
        self.o1 = parse_token(row[12], int, 1)
        self.f1 = parse_token(row[13], float, 1.0)
        if (len(row) > 15):
            self.o2 = parse_token(row[14], int, 0)
            self.f2 = parse_token(row[15], float, 1.0)
        if (len(row) > 17):
            self.o3 = parse_token(row[16], int, 0)
            self.f3 = parse_token(row[17], float, 1.0)
        if (len(row) > 19):
            self.o4 = parse_token(row[18], int, 0)
            self.f4 = parse_token(row[19], float, 1.0)
        if version in (33, 34):
            self.vecgrp = parse_token(row[20], str, ' '*12)
        
        #row2
        self.r1_2 = parse_token(row2[0], float, 0.0)
        self.x1_2 = parse_token(row2[1], float )
        self.sbase1_2 = parse_token(row2[2], float, 100.0)
        
        #row3 
        self.windv1 = parse_token(row3[0], float, 1.0)
        self.nomv1 = parse_token(row3[1], float, 0.0)
        self.ang1 = parse_token(row3[2], float, 0.0)
        self.rata1 = parse_token(row3[3], float, 0.0)
        self.ratb1 = parse_token(row3[4], float, 0.0)
        self.ratc1 = parse_token(row3[5], float, 0.0)
        self.cod1 = parse_token(row3[6], float, 0)
        self.cont1 = parse_token(row3[7], float, 0)
        self.rma1 = parse_token(row3[8], float, 1.1)
        self.rmi1 = parse_token(row3[9], float, 0.9)
        self.vma1 = parse_token(row3[10], float, 1.1)
        self.vmi1 = parse_token(row3[11], float, 0.9)
        self.ntp1 = parse_token(row3[12], float, 33 )
        self.tab1 = parse_token(row3[13], float, 0)
        self.cr1 = parse_token(row3[14], float, 0.0)
        self.cx1 = parse_token(row3[15], float, 0.0)
        if version in (33, 34):
            self.cnxa1 = parse_token(row3[16], float, 0.0)
        
        #row4
        self.windv2 = parse_token(row4[0], float, 1.0)
        self.nomv2 = parse_token(row4[1], float, 0.0)



class Three_xfmr:
    def __init__(self, version = 32):
        self.i = None # no default
        self.j = None # no default
        self.k = 0
        self.ckt = '1'
        self.cw = 1
        self.cz = 1
        self.cm = 1
        self.mag1 = 0.0
        self.mag2 = 0.0
        self.nmetr = 2
        self.name = 12*' '
        self.stat = 1
        self.o1 = 1
        self.f1 = 1.0
        self.o2 = 0
        self.f2 = 1.0
        self.o3 = 0
        self.f3 = 1.0
        self.o4 = 0
        self.f4 = 1.0
        
        self.r1_2 = 0.0
        self.x1_2 = 0.0
        self.sbase1_2 = 0.0
        self.r2_3 = 0.0
        self.x2_3 = 0.0
        self.sbase2_3 = 0.0
        self.r3_1 = 0.0
        self.x3_1 = 0.0
        self.sbase3_1 = 0.0
        self.vmstar = 1.0
        self.anstar = 0.0
        
        self.windv1 = 1.0
        self.nomv1 = 0.0
        self.ang1 = 0.0
        self.rata1, self.ratb1, self.ratv1 = 0.0, 0.0, 0.0
        self.cod1 = 0
        self.cont1 = 0
        self.rma1 = 1.1
        self.rmi1 = 0.9
        self.vma1 = 1.1
        self.vmi1 = 0.9
        self.ntp1 = 33
        self.tab1 = 0
        self.cr1 = 0.0
        self.cx1 = 0.0
        
        self.windv2 = 1.0
        self.nomv2 = 0.0
        self.ang2 = 0.0
        self.rata2, self.ratb2, self.ratv2 = 0.0, 0.0, 0.0
        self.cod2 = 0
        self.cont2 = 0
        self.rma2 = None
        self.rmi2 = None
        self.vma2 = None
        self.vmi2 = None
        self.ntp2 = None
        self.tab2 = None
        self.cr2 = None
        self.cx2 = None
        
        self.windv3 = 1.0
        self.nomv3 = 0.0
        self.ang3 = 0.0
        self.rata3, self.ratb3, self.ratv3 = 0.0, 0.0, 0.0
        self.cod3 = 0
        self.cont3 = 0
        self.rma3 = None
        self.rmi3 = None
        self.vma3 = None
        self.vmi3 = None
        self.ntp3 = 33
        self.tab3 = 0
        self.cr3 = 0.0
        self.cx3 = 0.0
        
        if version in(33, 34):
            self.vecgrp = ' '*12
            self.cnxa1 = 0.0
            self.cnxa2 = 0.0
            self.cnxa3 = 0.0
        
    def read_from_row(self, row, row2, row3, row4, row5, version):
        #row 1
        self.i = parse_token(row[0], int, '')
        self.j = parse_token(row[1], int, '')
        self.k = parse_token(row[2], int, 0)
        self.ckt = parse_token(row[3], str, '1')
        self.cw = parse_token(row[4], int, 1)
        self.cz = parse_token(row[5], int, 1)
        self.cm = parse_token(row[6], int, 1)
        self.mag1 = parse_token(row[7], float, 0.0)
        self.mag2 = parse_token(row[8], float, 0.0)
        self.nmetr = parse_token(row[9], int, 2)
        self.name = parse_token(row[10], str, 12*' ')
        self.stat = parse_token(row[11], int, 1)
        self.o1 = parse_token(row[12], int, 0)
        self.f1 = parse_token(row[13], float, 1.0)
        if (len(row) > 15):
            self.o2 = parse_token(row[14], int, 0)
            self.f2 = parse_token(row[15], float, 1.0)
        if (len(row) > 17):
            self.o3 = parse_token(row[16], int, 0)
            self.f3 = parse_token(row[17], float, 1.0)
        if (len(row) > 19):
            self.o4 = parse_token(row[18], int, 0)
            self.f4 = parse_token(row[19], float, 1.0)
        if version in (33, 34):
            self.vecgrp = parse_token(row[20], str, ' '*12)
        
        #row2
        self.r1_2 = parse_token(row2[0], float, 0.0)
        self.x1_2 = parse_token(row2[1], float, 0.0)
        self.sbase1_2 = parse_token(row2[2], float, 0.0)
        self.r2_3 = parse_token(row2[3], float, 0.0)
        self.x2_3 = parse_token(row2[4], float, 0.0)
        self.sbase2_3 = parse_token(row2[5], float, 0.0)
        self.r3_1 = parse_token(row2[6], float, 0.0)
        self.x3_1 = parse_token(row2[7], float, 0.0)
        self.sbase3_1 = parse_token(row2[8], float, 0.0)
        self.vmstar = parse_token(row2[9], float, 1.0)
        self.anstar = parse_token(row2[10], float, 0.0)
        
        #row 3
        self.windv1 = parse_token(row3[0], float, 1.0)
        self.nomv1 = parse_token(row3[1], float, 0.0)
        self.ang1 = parse_token(row3[2], float, 0.0)
        self.rata1 = parse_token(row3[3], float, 0.0)
        self.ratb1 = parse_token(row3[4], float, 0.0)
        self.ratc1 = parse_token(row3[5], float, 0.0)
        self.cod1 = parse_token(row3[6], float, 0)
        self.cont1 = parse_token(row3[7], float, 0)
        self.rma1 = parse_token(row3[8], float, 1.1)
        self.rmi1 = parse_token(row3[9], float, 0.9)
        self.vma1 = parse_token(row3[10], float, 1.1)
        self.vmi1 = parse_token(row3[11], float, 0.9)
        self.ntp1 = parse_token(row3[12], float, 33)
        self.tab1 = parse_token(row3[13], float, 0)
        self.cr1 = parse_token(row3[14], float, 0.0)
        self.cx1 = parse_token(row3[15], float, 0.0)
        if version in (33, 34):
            self.cnxa1 = parse_token(row3[16], float, 0.0)
        
        #row 4
        self.windv2 = parse_token(row4[0], float, 1.0)
        self.nomv2 = parse_token(row4[1], float, 0.0)
        self.ang2 = parse_token(row4[2], float, 0.0)
        self.rata2 = parse_token(row4[3], float, 0.0)
        self.ratb2 = parse_token(row4[4], float, 0.0)
        self.ratc2 = parse_token(row4[5], float, 0.0)
        self.cod2 = parse_token(row4[6], float, 0)
        self.cont2 = parse_token(row4[7], float, 0)
        self.rma2 = parse_token(row4[8], float, 1.1)
        self.rmi2 = parse_token(row4[9], float, 0.9)
        self.vma2 = parse_token(row4[10], float, 1.1)
        self.vmi2 = parse_token(row4[11], float, 0.9)
        self.ntp2 = parse_token(row4[12], float, 33)
        self.tab2 = parse_token(row4[13], float, 0)
        self.cr2 = parse_token(row4[14], float, 0.0)
        self.cx2 = parse_token(row4[15], float, 0.0)
        if version in (33, 34):
            self.cnxa2 = parse_token(row4[16], float, 0.0)
        
        #row 5
        self.windv3 = parse_token(row5[0], float, 1.0)
        self.nomv3 = parse_token(row5[1], float, 0.0)
        self.ang3 = parse_token(row5[2], float, 0.0)
        self.rata3 = parse_token(row5[3], float, 0.0)
        self.ratb3 = parse_token(row5[4], float, 0.0)
        self.ratc3 = parse_token(row5[5], float, 0.0)
        self.cod3 = parse_token(row5[6], float, 0)
        self.cont3 = parse_token(row5[7], float, 0)
        self.rma3 = parse_token(row5[8], float, 1.1)
        self.rmi3 = parse_token(row5[9], float, 0.9)
        self.vma3 = parse_token(row5[10], float, 1.1)
        self.vmi3 = parse_token(row5[11], float, 0.9)
        self.ntp3 = parse_token(row5[12], float, 33)
        self.tab3 = parse_token(row5[13], float, 0)
        if len(row) > 14:
            self.cr3 = parse_token(row[14], float, 0.0)
        if len(row) > 15:
            self.cx3 = parse_token(row[15], float, 0.0)
        if version in (33, 34):
            self.cnxa3 = parse_token(row5[16], float, 0.0)

    

class Area:

    def __init__(self):

        self.i = None # no default
        self.isw = 0
        self.pdes = 0.0
        self.ptol = 10.0
        self.arname = 12*' '

    def clean_arname(self):

        self.arname = ''

    def check(self):

        self.check_i_pos()


    def read_from_row(self, row, version):

        #row = pad_row(row, 5)
        self.i = parse_token(row[0], int, default=None)
        self.isw = parse_token(row[1], int, 0)
        self.pdes = parse_token(row[2], float, 0.0)
        self.ptol = parse_token(row[3], float, 10.0)
        self.arname = parse_token(row[4], str, 12*' ')

class Zone:

    def __init__(self):

        self.i = None # no default
        self.zoname = 12*' '

    def clean_zoname(self):

        self.zoname = ''

        
    def read_from_row(self, row, version):

        #row = pad_row(row, 2)
        self.i = parse_token(row[0], int, default=None)
    
        self.zoname = parse_token(row[1], str, 12*' ')

class SwitchedShunt:

    def __init__(self):
        
        self.i = None # no default
        self.modsw = 1
        self.adjm = 0
        self.stat = 1
        self.vswhi = 1.0
        self.vswlo = 1.0
        self.swrem = 0
        self.rmpct = 100.0
        self.rmidnt = 12*' '
        self.binit = 0.0
        self.n1 = 0
        self.b1 = 0.0
        self.n2 = 0
        self.b2 = 0.0
        self.n3 = 0
        self.b3 = 0.0
        self.n4 = 0
        self.b4 = 0.0
        self.n5 = 0
        self.b5 = 0.0
        self.n6 = 0
        self.b6 = 0.0
        self.n7 = 0
        self.b7 = 0.0
        self.n8 = 0
        self.b8 = 0.0

    
    def read_from_row(self, row, version):
        if version in (32, 33, 34):
            row = make_full_row(row, 26) #to account for varying numbers of n/b
            #row = pad_row(row, 26)
            self.i = parse_token(row[0], int, default=None)
            self.stat = parse_token(row[3], int, default=1)
            self.binit = parse_token(row[9], float, default=0.0)
            self.n1 = parse_token(row[10], int, default=0)
            self.b1 = parse_token(row[11], float, default=0.0)
            self.n2 = parse_token(row[12], int, default=0)
            self.b2 = parse_token(row[13], float, default=0.0)
            self.n3 = parse_token(row[14], int, default=0)
            self.b3 = parse_token(row[15], float, default=0.0)
            self.n4 = parse_token(row[16], int, default=0)
            self.b4 = parse_token(row[17], float, default=0.0)
            self.n5 = parse_token(row[18], int, default=0)
            self.b5 = parse_token(row[19], float, default=0.0)
            self.n6 = parse_token(row[20], int, default=0)
            self.b6 = parse_token(row[21], float, default=0.0)
            self.n7 = parse_token(row[22], int, default=0)
            self.b7 = parse_token(row[23], float, default=0.0)
            self.n8 = parse_token(row[24], int, default=0)
            self.b8 = parse_token(row[25], float, default=0.0)
            
        
            self.modsw = parse_token(row[1], int, 1)
            self.adjm = parse_token(row[2], int, 0)
            self.vswhi = parse_token(row[4], float, 1.0)
            self.vswlo = parse_token(row[5], float, 1.0)
            self.swrem = parse_token(row[6], int, 0)
            self.rmpct = parse_token(row[7], float, 100.0)
            self.rmidnt = parse_token(row[8], str, 12*' ')
        elif version == 30:
            row = make_full_row(row, 24)
            self.i = parse_token(row[0], int, default=None)
            self.modsw = parse_token(row[1], int, 1)
            self.vswhi = parse_token(row[2], float, 1.0)
            self.vswlo = parse_token(row[3], float, 1.0)
            self.swrem = parse_token(row[4], int, 0)
            self.rmpct = parse_token(row[5], float, 100.0)
            self.rmidnt = parse_token(row[6], str, 12*' ')
            self.binit = parse_token(row[7], float, default=0.0)
            self.n1 = parse_token(row[8], int, default=0)
            self.b1 = parse_token(row[9], float, default=0.0)
            self.n2 = parse_token(row[10], int, default=0)
            self.b2 = parse_token(row[11], float, default=0.0)
            self.n3 = parse_token(row[12], int, default=0)
            self.b3 = parse_token(row[13], float, default=0.0)
            self.n4 = parse_token(row[14], int, default=0)
            self.b4 = parse_token(row[15], float, default=0.0)
            self.n5 = parse_token(row[16], int, default=0)
            self.b5 = parse_token(row[17], float, default=0.0)
            self.n6 = parse_token(row[18], int, default=0)
            self.b6 = parse_token(row[19], float, default=0.0)
            self.n7 = parse_token(row[20], int, default=0)
            self.b7 = parse_token(row[21], float, default=0.0)
            self.n8 = parse_token(row[22], int, default=0)
            self.b8 = parse_token(row[23], float, default=0.0)


class Two_terminal_dc:

    def __init__(self):
        #first line
        self.name = None #no default allowed
        self.mdc = 0
        self.rdc = None #no default allowed
        self.setvl = None #no default allowed
        self.vschd = None #no default allowed
        self.vcmod = 0.0
        self.rcomp = 0.0
        self.delti = 0.0
        self.meter = 'I'
        self.dcvmin = 0.0
        self.cccitmx = 20
        self.cccacc = 1.0
        #second line
        self.ipr = None #no default allowed
        self.nbr = None #no default allowed
        self.anmxr = None #no default allowed
        self.anmnr = None #no default allowed
        self.rcr = None #no default allowed
        self.xcr = None #no default allowed
        self.ebasr = None #no default allowed
        self.trr = 1.0
        self.tapr = 1.0
        self.tmxr = 1.5
        self.tmnr = 0.51
        self.stpr = 0.00625
        self.icr = 0
        self.ifr = 0
        self.itr = 0
        self.idr = '1'
        self.xcapr = 0.0
        #third line
        self.ipi = None
        self.nbi = None
        self.anmxi = None
        self.anmni = None
        self.rci = None
        self.xci = None
        self.ebasi = None
        self.tri = None
        self.tapi = None
        self.tmxi = None
        self.tmni = None
        self.stpi = None
        self.ici = None
        self.ifi = None
        self.iti = None
        self.idi = None
        self.xcapi = None
        
    def read_from_row(self, row1, row2, row3, version):
        #first line
        self.name = parse_token(row1[0], str)
        self.mdc = parse_token(row1[1], int, 0)
        self.rdc = parse_token(row1[2], float)
        self.setvl = parse_token(row1[3], float)
        self.vschd = parse_token(row1[4], float)
        self.vcmod = parse_token(row1[5], float, 0.0)
        self.rcomp = parse_token(row1[6], float, 0.0)
        self.delti = parse_token(row1[7], float, 0.0)
        self.meter = parse_token(row1[8], str, 'I')
        self.dcvmin = parse_token(row1[9], float, 0.0)
        self.cccitmx = parse_token(row1[10], int, 20)
        self.cccacc = parse_token(row1[11], float, 1.0)
        #start second line
        
        self.ipr = parse_token(row2[0], int)
        self.nbr = parse_token(row2[1], int)
        self.anmxr = parse_token(row2[2], float)
        self.anmnr = parse_token(row2[3], float)
        self.rcr = parse_token(row2[4], float)
        self.xcr = parse_token(row2[5], float)
        self.ebasr = parse_token(row2[6], float)
        self.trr = parse_token(row2[7], float, 1.0)
        self.tapr = parse_token(row2[8], float, 1.0)
        self.tmxr = parse_token(row2[9], float, 1.5)
        self.tmnr = parse_token(row2[10], float, 0.51)
        self.stpr = parse_token(row2[11], float, 0.00625)
        self.icr = parse_token(row2[12], str, '0')
        self.ifr = parse_token(row2[13], int, 0)
        self.itr = parse_token(row2[14], int, 0)
        self.idr = parse_token(row2[15], str, '1')
        self.xcapr =parse_token(row2[16], float, 0.0)
        #start third line (inverter qualities)
        self.ipi = parse_token(row3[0], int)
        self.nbi = parse_token(row3[1], int)
        self.anmxi = parse_token(row3[2], float)
        self.anmni = parse_token(row3[3], float)
        self.rci = parse_token(row3[4], float)
        self.xci = parse_token(row3[5], float)
        self.ebasi = parse_token(row3[6], float)
        self.tri = parse_token(row3[7], float)
        self.tapi = parse_token(row3[8], float)
        self.tmxi = parse_token(row3[9], float)
        self.tmni = parse_token(row3[10], float)
        self.stpi = parse_token(row3[11], float)
        self.ici = parse_token(row3[12], float)
        self.ifi = parse_token(row3[13], int)
        self.iti = parse_token(row3[14], int)
        self.idi = parse_token(row3[15], str)
        self.xcapi = parse_token(row3[16], float)
        
class VSC:
    
    def __init__(self):
        #line one
        self.name = None
        self.mdc = 1
        self.rdc = None
        self.o1 = 1
        self.o2, self.o3, self.o4 = 0, 0 , 0
        self.f1, self.f2, self.f3, self.f4, = 1, 1, 1, 1
        #line two
        self.ibus = None
        self.type = None
        self.mode = 1
        self.dcset = None
        self.acset = 1.0
        self.aLoss, self.bLoss = 0.0, 0.0
        self.minLoss = 0.0
        self.smax = 0.0
        self.imax = 0.0
        self.pwf = 1.0
        self.maxq, self.minq = 9999.0, -9999.0
        self.remot = '0'
        self.rmpct = 100.0
        #line three
        self.ibus2 = None
        self.type2 = None
        self.mode2 = 1
        self.dcset2 = None
        self.acset2 = 1.0
        self.aLoss2, self.bLoss2 = 0.0, 0.0
        self.minLoss2 = 0.0
        self.smax2 = 0.0
        self.imax2 = 0.0
        self.pwf2 = 1.0
        self.maxq2, self.minq2 = 9999.0, -9999.0
        self.remot2 = '0'
        self.rmpct2 = 100.0

    def read_from_row(self, row1, row2, row3, version):
        if len(row1) <5:
            print("missing data from VSC line")
        if len(row1) < 11:
            diff = 11-len(row1)
            '''eachDiff = diff/2
            row1 = row1[:]+['']*eachDiff+row1[:]*eachDiff'''
            row1 += ['']*diff
        #line one
        self.name = parse_token(row1[0], str)
        self.mdc = parse_token(row1[1], int, 1)
        self.rdc = parse_token(row1[2], float)
        self.o1 = parse_token(row1[3], float, 1)
        self.o2 = parse_token(row1[4], float, 0)
        self.o3 = parse_token(row1[5], float, 0)
        self.o4 = parse_token(row1[6], float, 0)
        self.f1 = parse_token(row1[7], float, 1.0)
        self.f2 = parse_token(row1[8], float, 1.0)
        self.f3 = parse_token(row1[9], float, 1.0)
        self.f4 = parse_token(row1[10], float, 1.0)
        #line two
        self.ibus = parse_token(row2[0], str)
        self.type = parse_token(row2[1], int)
        self.mode = parse_token(row2[2], int, 1)
        self.dcset =parse_token(row2[3], float)
        self.acset = parse_token(row2[4], float, 1.0)
        self.aLoss = parse_token(row2[5], float, 0.0)
        self.bLoss = parse_token(row2[6], float, 0.0)
        self.minLoss = parse_token(row2[7], float, 0.0)
        self.smax = parse_token(row2[8], float, 0.0)
        self.imax = parse_token(row2[9], float, 0.0)
        self.pwf = parse_token(row2[10], float, 1.0)
        self.maxq = parse_token(row2[11], float, 9999.0)
        self.minq = parse_token(row2[12],float, -9999.0)
        self.remot = parse_token(row2[13], str, '0')
        self.rmpct = parse_token(row2[14], float, 100.0)
        #line three
        self.ibus2 = parse_token(row3[0], str)
        self.type2 = parse_token(row3[1], int)
        self.mode2 = parse_token(row3[2], int, 1)
        self.dcset2 =parse_token(row3[3], float)
        self.acset2 = parse_token(row3[4], float, 1.0)
        self.aLoss2 = parse_token(row3[5], float, 0.0)
        self.bLoss2 = parse_token(row3[6], float, 0.0)
        self.minLoss2 = parse_token(row3[7], float, 0.0)
        self.smax2 = parse_token(row3[8], float, 0.0)
        self.imax2 = parse_token(row3[9], float, 0.0)
        self.pwf2 = parse_token(row3[10], float, 1.0)
        self.maxq2 = parse_token(row3[11], float, 9999.0)
        self.minq2 = parse_token(row3[12],float, -9999.0)
        self.remot2 = parse_token(row3[13], str, '0')
        self.rmpct2 = parse_token(row3[14], float, 100.0)
        
        
        
class Impedance_corr:
    
    def __init__(self):
        self.i = None #no deafult allowed
        self.t1, self.t2, self.t3 = 0.0, 0.0, 0.0
        self.t4, self.t5, self.t6 = 0.0, 0.0, 0.0
        self.t7, self.t8, self.t9 = 0.0, 0.0, 0.0
        self.t10, self.t11 = 0.0, 0.0
        self.f1, self.f2, self.f3 = 0.0, 0.0, 0.0
        self.f4, self.f5, self.f6 = 0.0, 0.0, 0.0
        self.f7, self.f8, self.f9 = 0.0, 0.0, 0.0
        self.f10, self.f11 = 0.0, 0.0
        
    def read_from_row(self, row, version):
        if version == 34:
            pass
        else:
            row = make_full_row(row, 23)
            self.i = parse_token(row[0], int)
            self.t1 = parse_token(row[1], float, 0.0)
            self.f1 = parse_token(row[2], float, 0.0)
            self.t2 = parse_token(row[3], float, 0.0)
            self.f2 = parse_token(row[4], float, 0.0)
            self.t3 = parse_token(row[5], float, 0.0)
            self.f3 = parse_token(row[6], float, 0.0)
            self.t4 = parse_token(row[7], float, 0.0)
            self.f4 = parse_token(row[8], float, 0.0)
            self.t5 = parse_token(row[9], float, 0.0)
            self.f5 = parse_token(row[10], float, 0.0)
            self.t6 = parse_token(row[11], float, 0.0)
            self.f6 = parse_token(row[12], float, 0.0)
            self.t7 = parse_token(row[13], float, 0.0)
            self.f7 = parse_token(row[14], float, 0.0)
            self.t8 = parse_token(row[15], float, 0.0)
            self.f8 = parse_token(row[16], float, 0.0)
            self.t9 = parse_token(row[17], float, 0.0)
            self.f9 = parse_token(row[18], float, 0.0)
            self.t10 = parse_token(row[19], float, 0.0)
            self.f10 = parse_token(row[20], float, 0.0)
            self.t11 = parse_token(row[21], float, 0.0)
            self.f11 = parse_token(row[22], float, 0.0)
        
        
        
class Multi_term_DC:
    
    def __init__(self):
        pass
        

        
class Owner:
    
    def __init__(self):
        self.i = None
        self.owname = 12*' '
        
    def read_from_row(self, row, version):
        self.i = parse_token(row[0], int)
        self.owname = parse_token(row[1], str, 12*' ')
    
    
    
    
    
    
class Interarea_transfer:
    def __init__(self):
        self.arfrom = None
        self.arto = None
        self.trid = None
        self.ptran = 0.0
        
    def read_from_row(self, row, version):
        self.arfrom = parse_token(row[0], int)
        self.arto = parse_token(row[1], int)
        self.trid = parse_token(row[2], str, '1')
        self.ptran = parse_token(row[3],float, 0.0 )
    
    
class FACTS_device:
    def __init__(self):
        self.name = None
        self.i = None
        self.j = 0
        self.mode = 1
        self.pdes = 0.0
        self.qdes = 0.0
        self.vset = 1.0
        self.shmx = 9999.0
        self.trmx = 9999.0
        self.vtmn = 0.9
        self.vtmx = 1.1
        self.vsmx = 1.0
        self.imx = 0.0
        self.linx  = 0.05
        self.rmpct = 100.0
        self.owner = 1
        self.set1 = 0.0
        self.set2 = 0.0
        self.vsref = 0
        self.remot = 0
        self.mname = ''
    
    def read_from_row(self, row, version):
        self.name = parse_token(row[0], str)
        self.i = parse_token(row[1], int)
        self.j = parse_token(row[2], int)
        self.mode = parse_token(row[3], int)
        self.pdes = parse_token(row[4], float, 0.0)
        self.qdes = parse_token(row[5], float, 0.0)
        self.vset = parse_token(row[6], float, 1.0)
        self.shmx = parse_token(row[7], float, 9999.0)
        self.trmx = parse_token(row[8], float, 9999.0)
        self.vtmn = parse_token(row[9], float,0.9)
        self.vtmx = parse_token(row[10], float,1.1)
        self.vsmx = parse_token(row[11], float, 1.0)
        self.imx = parse_token(row[12], float, 0.0)
        self.linx  = parse_token(row[13], float, 0.05)
        self.rmpct = parse_token(row[14], float, 100.0)
        self.owner = parse_token(row[15], int, 1)
        self.set1 = parse_token(row[16], float,0.0)
        self.set2 = parse_token(row[17], float, 0.0)
        self.vsref = parse_token(row[18], int, 0)
        if version != 30:
            self.remot = parse_token(row[19], int, 0)
            self.mname = parse_token(row[20], str, '')
    
    
class Multi_section_line_grouping:
    
    def __init__(self):
        self.i = None #from bus number
        self.j = None #to bus number
        self.id = '&1'
        self.met = 1
        self.dum1, self.dum2, self.dum3 = None, None, None
        self.dum4, self.dum5, self.dum6 = None, None, None
        self.dum7, self.dum8, self.dum9 = None, None, None
        
    def read_from_row(self,row, version):
        if len(row)<5:
            print('missing information form multi section line grouping')
        elif len(row)<13:
            diff = 13-len(row)
            row += ['']*diff
            
        self.i = parse_token(row[0], int)
        self.j = parse_token(row[1], int)
        self.id = parse_token(row[2], str, '&1')
        self.met = parse_token(row[3], int, 1)
        self.dum1 = parse_token(row[4], int)
        if len(row) > 5:
            self.dum2 = parse_token(row[5],  int, 0)
        if len(row) > 6:
            self.dum3 = parse_token(row[6],  int, 0)
        if len(row) > 7:
            self.dum4 = parse_token(row[7],  int, 0)
        if len(row) > 8:
            self.dum5 = parse_token(row[8],  int, 0)
        if len(row) > 9:
            self.dum6 = parse_token(row[9],  int, 0)
        if len(row) > 10:
            self.dum7 = parse_token(row[10], int, 0)
        if len(row) > 11:
            self.dum8 = parse_token(row[11], int, 0)
        if len(row) > 12:
            self.dum9 = parse_token(row[12], int, 0)
    
    
class Sys_switching_dev_data: #only in version 34
    def __init__(self):
        self.i = None
        self.j = None
        self.cktid = '1'
        self.x = None
        self.rate1 = 0.0
        self.rate2 = 0.0
        self.rate3 = 0.0
        self.rate4 = 0.0
        self.rate5 = 0.0
        self.rate6 = 0.0
        self.rate7 = 0.0
        self.rate8 = 0.0
        self.rate9 = 0.0
        self.rate10 = 0.0
        self.rate11 = 0.0
        self.rate12 = 0.0
        self.status = None
        self.nstatus = None
        self.meterd = None
        self.stype = None
        self.name = None     
    
    def read_from_row(self, row, version):
        self.i = parse_token(row[0], int)
        self.j = parse_token(row[0], int)
        self.cktid = parse_token(row[0], str)
        self.x = parse_token(row[0], int)
        self.rate1 = parse_token(row[0], float)
        self.rate2 = parse_token(row[0], float)
        self.rate3 = parse_token(row[0], float)
        self.rate4 = parse_token(row[0], float)
        self.rate5 = parse_token(row[0], float)
        self.rate6 = parse_token(row[0], float)
        self.rate7 = parse_token(row[0], float)
        self.rate8 = parse_token(row[0], float)
        self.rate9 = parse_token(row[0], float)
        self.rate10 = parse_token(row[0], float)
        self.rate11 = parse_token(row[0], float)
        self.rate12 = parse_token(row[0], float)
        self.status = parse_token(row[0], int)
        self.nstatus = parse_token(row[0], int)
        self.meterd = parse_token(row[0], str)
        self.stype = parse_token(row[0], int)
        self.name = parse_token(row[0], str)  
    
    
    
    
   
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
