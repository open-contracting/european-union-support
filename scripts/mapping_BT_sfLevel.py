import sys
import os
import pandas as pd
from copy import deepcopy
from pathlib import Path
from typing import List

# This script concatenates the eForm-SF mapping CSV extracted from the Excel files
# It deduplicates identical rows
# It explodes rows that hold several BT to SF level mappings
# It basically extracts clean processable mapping info from the extracted CSVs

def getNoticeNumbers(file: str) -> dict:
    """
    eForms and SF notice numbers based on filename
    """
    base = file.lstrip(directory + '/').split('.')[0].split(" vs ")
    eFormNoticeNumber = base[0].lstrip('eForm')
    sfNoticeNumber = base[1].lstrip('SF')

    return {'eform': eFormNoticeNumber, 'sf': sfNoticeNumber}


def addNoticeNumbers(file: str) -> pd.DataFrame:
    csv = pd.read_csv(file, sep=';',
                      header=0,
                      usecols=[2, 3, 4, 5, 6, 7, 8, 9],
                      names=['ID', 'Name', 'Datatype', 'Repeatable', 'Description', 'Legal Status', 'Level',
                             'Element'],
                      keep_default_na=False)

    noticeNumbers = getNoticeNumbers(file)

    csv['eformNotice'] = noticeNumbers['eform']
    csv['sfNotice'] = noticeNumbers['sf']
    return csv

# directory = dir where the CSVs extracted from the eFormsBT-sfLevel Excel mappings are stored
if len(sys.argv) >= 2:
    directory = sys.argv[1]
else:
    os.chdir('output/mapping/eForms/eFormsVsStandardForms')
    directory = os.getcwd()

path = Path(directory).glob('*.csv')
csvs = [addNoticeNumbers(str(file)) for file in path]

# Concat [csv]
df = pd.concat(csvs, ignore_index=True)

# Filter out empty Level since it has no mapping info
df = df[df.Level != '']

# Remove trailing newlines
df['Level'] = [x.rstrip('\n') for x in df['Level']]
df['Element'] = [x.rstrip('\n') for x in df['Element']]

# Remove breaking \n
df['Element'] = [x.replace('persons;\n(Only in','persons; (Only in') for x in df['Element']]

# Explode rows that hold several SF levels
# Could be replaced with a comprehension list for better perf
exploded_rows: List[pd.Series] = []
for label, row in df.iterrows():
    if '\n' not in row['Level']:
        continue
    levels: List = row['Level'].split('\n')
    if '\n' in row['Element']:
        elements: List = row['Element'].split('\n')

        # Remove empty lines (double \n)
        if '' in elements:
            elements.remove('')

        # Check that the same number of levels and elements returned
        try:
            assert (len(levels) == len(elements))
        except AssertionError as error:
            print('Error: levels and element mismatch', error, sep=' ')
            print(row['ID'], row['eformNotice'], row['sfNotice'], row['Element'], sep=' | ')
            print(len(levels), ' ', len(elements))
    else:
        # Certain Element don't have \n because they match all the Levels
        elements = [row['Element']] * len(levels)

    # Instantiate the rows that will be exploded
    new_rows: List[pd.Series] = []

    # For each level/element couple, copy the current row
    for t in zip(levels, elements):
        new_row = deepcopy(row)
        new_row['Level'], new_row['Element'] = t
        new_rows.append(new_row)

    # Update the big list of new rows
    exploded_rows += new_rows

    # We remove the row with the \n...
    df.drop(label, inplace=True)

# ...and add the new rows instead
df = df.append(exploded_rows, ignore_index=False)
df.to_csv(directory + '/../BT-sfLevel.csv')
