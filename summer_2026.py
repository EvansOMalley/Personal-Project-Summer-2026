# -*- coding: utf-8 -*-
#%% Initialization

#%% Necessary Imports

import pandas as pd, numpy as np
from sys import exit

rel_path = "data/Western_Europe_Public_Data_Church_Tax_Added.csv"
manual_rel_path = "manuals/manual.txt"

parent_df = pd.read_csv(rel_path, skipinitialspace=True)
with open(manual_rel_path) as f:
    manual = f.read()

#%% File Parsing

class ord_leg:
    def __init__(self, order: str, legend: dict):
        self.order = order
        self.legend = legend
        
    def ord(self):
        return self.order
    
    def leg(self):
        return self.legend
    
    def __repr__(self):
        return f"{self.order}, {self.legend.keys()[0]}"
    
def parse_next(terminator):
    assert len(terminator) == 1, "Terminator must be one character"
    global s
    global manual
    
    passage = ""
    while manual[s] != terminator:
        passage += manual[s]
        s += 1
    s += 1
        
    return passage


s = 0
legends = {}

while s < len(manual):
    col_legend = {}
    name = parse_next(':')
    order = parse_next('{')
    s += 1
    
    if "[COUNTRY]" in name:
        while manual[s] != '!':
            i = int(parse_next(' '))
            val = parse_next('\n')
            col_legend[i] = val
        s += 1
        
        while manual[s] != '}':
            c = manual[s:s+3]
            s += 5
            
            while manual[s] != '}':
                i = int(parse_next(' '))
                val = parse_next('\n')
                col_legend[i] = val
            s += 2
            
            legends[name.replace("[COUNTRY]", c)] = ord_leg(order, col_legend)
            
    else:
        while manual[s] != '}':
            i = int(parse_next(' '))
            val = parse_next('\n')
            col_legend[i] = val
        s += 1
        
        legends[name] = ord_leg(order, col_legend)

#%% Parent_Cleaning

#%% Restitching

#%% Move QRID column to index
parent_df.index = parent_df["QRID"]
parent_df = parent_df.drop("QRID", axis = 1)

#%% Fix respose layout for Q9

Q9_cols = parent_df.columns.map(lambda x: x[1] == '9')
Q9_cols = parent_df.iloc[:, Q9_cols]

def get_Q9(row: pd.Series):
    i = row[row == 1].index
    if len(i) == 0:
        return np.nan
        
    else:
        return int(i[0][3])

Q9 = Q9_cols.apply(get_Q9, axis = 1)
parent_df.insert(16, "Q9", Q9)
parent_df = parent_df.drop(Q9_cols, axis = 1)
    
#%% Removing QS1... variables becuase they stand for regions and are indecipherable or redacted
# Removing qbornmoverec variable because values are incomprehensible or redacted

QS1_cols = [i for i in parent_df.columns if i.lower()[:3] == "qs1"]
parent_df = parent_df.drop(QS1_cols, axis = 1)
parent_df = parent_df.drop("qbornmoverec", axis = 1)
    
#%% Repair column naming scheme

def title_scheme(title: str):
    # Cumulatively adjusts column titles according to scheme described below
    new_title = title

    # Remove instances of "rec", signifying recoded variables

    if new_title[-3:].lower() == "rec":
        new_title = new_title[:-3]

    # Normalize Capitalization Scheme
    # "country" -> "Country"
    # "QCURREL", "qcurrel" -> "QCurrel"
    
    if new_title[0].lower() != 'q':
        new_title = new_title.title()
        
    else:
        new_title = 'Q' + new_title[1:].title()
    
    # Capitalize suffixes signifying country
    # "QDenomaut" -> "QDenomAUT"
    
    if new_title[-3:].upper() in legends["Country"].leg():
        new_title = new_title[:-3] + new_title[-3:].upper()
    if new_title[-4:-1].upper() in legends["Country"].leg():
        new_title = new_title[:-4] + new_title[-4:-1].upper() + new_title[-1]

    # Some questions are divided into cases a, b, c, etcetera
    # Denotation for this will be separated from the main title and uncapitalized
    # "Q4A", "Q4B" -> "Q4_a", Q4_b"
    # These are dicipherable by last 2 characters of the title

    NumCap = new_title[-1].isupper() and new_title[-2] in "0123456789"
    CapUncap = new_title[-1].islower() and new_title[-2].isupper()
    if NumCap or CapUncap:
        new_title = new_title[:-1] + "_" + new_title[-1].lower()

    # Choice adjustments
    if new_title[:4] == "QPty":
        if new_title[4] == 'a':
            new_title = new_title[:4] + "potvot" + new_title[5:]
        elif new_title[4] == 'b':
            new_title = new_title[:4] + "fvr" + new_title[5:]
        else:
            new_title = new_title[:4] + "cls" + new_title[4:]

    rename_key = {"QCitizen1" : "QCitizen",
                  "QBornc" : "QBornmthr",
                  "QBorne" : "QBornfthr"}

    if new_title in rename_key.keys():
        new_title = rename_key[new_title]
    
    return new_title

parent_df = parent_df.rename(title_scheme, axis = 1)