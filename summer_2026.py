#%% Necessary Imports

import pandas as pd, numpy as np
from warnings import simplefilter
simplefilter(action="ignore", category=pd.errors.PerformanceWarning)

rel_path = "Data/Western_Europe_Public_Data_Church_Tax_Added.csv"
codebook_rel_path = "Codebooks/codebook.txt"

parent_df = pd.read_csv(rel_path, skipinitialspace=True)
with open(codebook_rel_path) as f:
    codebook = f.read()

#%% Precursor Structures

class OrdLeg:
    def __init__(self, order: str, legend: dict):
        self.order = order
        self.legend = legend
        
    def ord(self):
        return self.order
    
    def leg(self):
        return self.legend
    
    def values(self):
        return self.legend.values()

    def keys(self):
        return self.legend.keys()

    def items(self):
        return self.legend.items()

    def __repr__(self):
        return f"{self.order}, {self.legend}"

    def __str__(self):
        return f"{self.order}, {self.legend}"

    def __getitem__(self, i):
        return self.legend[i]
#%% File Parsing

def parse_next(terminator):
    assert len(terminator) == 1, "Terminator must be one character"
    global s
    global codebook
    
    passage = ""
    while codebook[s] != terminator:
        passage += codebook[s]
        s += 1
    s += 1
        
    return passage


s = 0
Legends = {}

while s < len(codebook):
    col_legend = {}
    name = parse_next(':')
    order = parse_next('{')
    s += 1
    
    if "[COUNTRY]" in name:
        while codebook[s] != '!':
            i = int(parse_next(' '))
            val = parse_next('\n')
            col_legend[i] = val
        s += 1

        Legends[name.replace("[COUNTRY]", "")] = OrdLeg(order, {})
        
        while codebook[s] != '}':
            c = codebook[s:s+3]
            s += 5
            
            while codebook[s] != '}':
                i = int(parse_next(' '))
                val = parse_next('\n')
                col_legend[i] = val
            s += 2

            Legends[name.replace("[COUNTRY]", c)] = OrdLeg(order, col_legend)
        s += 2
            
    else:
        while codebook[s] != '}':
            i = int(parse_next(' '))
            val = parse_next('\n')
            col_legend[i] = val
        s += 2
        
        Legends[name] = OrdLeg(order, col_legend)

#%% Restitching
parent_df.index = parent_df["QRID"]
parent_df = parent_df.drop("QRID", axis = 1)

Q9_cols = parent_df.columns.map(lambda x: x[1] == "9")
Q9_cols = parent_df.iloc[:, Q9_cols]

def get_Q9(row: pd.Series):
    i = row[row == 1].index
    if len(i) == 0:
        return np.nan
        
    else:
        return int(i[0][3])

parent_df.insert(16, "Q9", Q9_cols.apply(get_Q9, axis = 1))
parent_df = parent_df.drop(Q9_cols, axis = 1)

QS1_cols = [i for i in parent_df.columns if i.lower()[:3] == "qs1"]
parent_df = parent_df.drop(QS1_cols, axis = 1)
parent_df = parent_df.drop("qbornmoverec", axis = 1)

parent_df["QIDEOLOGY"] = parent_df["QIDEOLOGY"].fillna(parent_df["QIDEOLOGYa"]).fillna(parent_df["QIDEOLOGYb"])
parent_df = parent_df.drop(["QIDEOLOGYa", "QIDEOLOGYb"], axis = 1)

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
    
    if new_title[-3:].upper() in Legends["Country"].values():
        new_title = new_title[:-3] + new_title[-3:].upper()
    if new_title[-4:-1].upper() in Legends["Country"].values():
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
                  "QBorne" : "QBornfthr",
                  "QChilda" : "QChild",
                  "QHhch" : "QParent"}

    if new_title in rename_key.keys():
        new_title = rename_key[new_title]
    
    return new_title

parent_df = parent_df.rename(title_scheme, axis = 1)

#%% Further Preparations

def cardinality(title: str):
    if title in Legends:
        return Legends[title].ord()
        
    if title[-2] == '_':
        return Legends[title[:-1]].ord()

    raise NotImplementedError(f"Column {title} inappropriately named")
    
def Cardinate(df: pd.DataFrame, cardinality_arg: str):
    return df.loc[:, df.apply(lambda x: cardinality(x.name)) == cardinality_arg]

def strip_countries(title: str):
    # Code primary lifted from title_scheme function
    if title[-3:] in Legends["Country"].values():
        return title[:-3]
    if title[-5:-2] in Legends["Country"].values():
        return title[:-5] + title[-2:]

    return title
        
survey_order = parent_df.apply(lambda x: strip_countries(x.name)).drop_duplicates().__array__()

def disambiguate(col: pd.Series):
    if col.dtypes == int:
        return col.map(lambda x: Legends[col.name][x])
    else:
        return col

def ambiguate(col: pd.Series):
    if col.dtypes == int:
        return col
    else:
        reverse_legend = {y:x for x,y in Legends[col.name].items()}
        return col.map(lambda x: reverse_legend[x])
    
def Nationate(df: pd.DataFrame):
    country_dfs = {}
    if "Country" not in df:
        df = df.join(parent_df["Country"], how = "left")
    df["Country"] = disambiguate(df["Country"])

    for c in df["Country"].unique():
        country_df = df.copy()
        country_df = country_df.loc[country_df["Country"] == c]
        country_df = country_df.loc[:, country_df.apply(lambda x: any(x.notna()))]
        country_df = country_df.rename(strip_countries, axis = 1)
        country_dfs[c] = country_df.drop("Country", axis = 1)
        
    return country_dfs

