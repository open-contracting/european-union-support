import os
from copy import deepcopy
from pathlib import Path
from typing import List

import pandas as pd
# This script concatenates the eForm-SF mapping CSV extracted from the Excel files
# It deduplicates identical rows
# It explodes rows that hold several BT to SF level mappings
# It basically extracts clean processable mapping info from the extracted CSVs
from pandas import Series


def getNoticeNumbers(file: str) -> dict:
    """
    eForms and SF notice numbers based on filename
    """
    base = file.lstrip(directory + '/').split('.')[0].split(" vs ")
    eformsNoticeNumber = base[0].lstrip('eForm')
    sfNoticeNumber = base[1].lstrip('SF')

    return {'eform': eformsNoticeNumber, 'sf': sfNoticeNumber}


def addNoticeNumbers(file: str) -> pd.DataFrame:
    csv = pd.read_csv(file, sep=';',
                      header=0,
                      usecols=[2, 3, 4, 5, 6, 7, 8, 9],
                      names=['ID', 'Name', 'Datatype', 'Repeatable', 'Description', 'Legal Status', 'Level',
                             'Element'],
                      keep_default_na=False)

    noticeNumbers = getNoticeNumbers(file)

    # Add two columns filled with the same values
    csv['eformsNotice'] = noticeNumbers['eform']
    csv['sfNotice'] = noticeNumbers['sf']
    return csv


# directory = 'output/mapping/eForms/eFormsVsStandardForms', where the CSVs extracted from the
# eFormsBT-sfLevel Excel mappings must be stored
rootDir = os.getcwd()
os.chdir(rootDir + '/output/mapping/eForms/eFormsVsStandardForms')
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
df['Element'] = [x.replace('persons;\n(Only in', 'persons; (Only in') for x in df['Element']]

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
            print(row['ID'], row['eformsNotice'], row['sfNotice'], row['Element'], sep=' | ')
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

# Explode notice number in df to have one notice number per row instead of 01,02,03
df['eformsNotice'] = [value.split(',') for value in df['eformsNotice']]
df = df.explode('eformsNotice', ignore_index=True)

# Turn '01' into '1' to enable join with df_noticeMatrix for single-digit notice numbers
df['eformsNotice'] = [str(int(value)) for value in df['eformsNotice']]

# Add form types with join
# Only needed when producing markdown/HTML (publication)
# os.chdir(rootDir + '/output/mapping/eForms')
# df_noticeMatrix = pd.read_csv('forms_noticeTypes.csv', keep_default_na=False,
#                               usecols=['Form type', 'Notice number'], index_col='Notice number',
#                               dtype={'Form type': 'str', 'Notice number': 'str'})
# df = df.join(df_noticeMatrix, how='left', on='eformsNotice')

# Add eForms xpath from output/mapping/eForms/xpath_bt_mapping.csv
# + sort by BT to group them
df_xpath: pd.DataFrame = pd.read_csv('xpath_bt_mapping.csv', keep_default_na=False,
                                     usecols=['bt', 'eforms_xpath', 'name'],
                                     skipinitialspace=True).sort_values('bt')

# We remove the rows that don't have xpath
df_xpath = df_xpath.loc[df_xpath['eforms_xpath'] != '']

# I wish I could squash the xpath without iterating
xpaths = []
grouped_xpath_rows: List[pd.Series] = []
# current_row = pd.Series(data={'bt' : ''}, index=['bt'])
current_row = {'bt': False}
row: Series

for label, row in df_xpath.iterrows():
    # We don't process the few xpath that don't have a related BT, but we keep them
    if row['bt'] != current_row['bt'] and row['bt'] != "":
        # If this is the first row with a BT, xpaths[] will be empty
        if len(xpaths) > 0:
            current_row['eforms_xpath'] = ';'.join(xpaths)
            grouped_xpath_rows.append(current_row)
        # New BT => new current_row, and first xpath in the list
        current_row = row
        xpaths = [row['eforms_xpath']]
        # The point is to replace the scattered xpath rows with one row that have them all for the same BT
        df_xpath.drop(label, inplace=True)
    elif row['bt'] == current_row['bt']:
        # Same BT as previous row (= current_row)? We store the xpath and drop the row
        xpaths.append(row['eforms_xpath'])
        df_xpath.drop(label, inplace=True)
    elif row['bt'] == "":
        # We just give a fake BT to ease further operations (BT must be unique in final df, thus "" doesn't work)
        row['bt'] = "no_BT_" + row['eforms_xpath'].split(':')[-1] + "_" + str(label)
    else:
        # the value of row['bt'] is not what it should be
        raise ValueError

# We add the rows with grouped xpath to the df
df_xpath = df_xpath.append(grouped_xpath_rows, ignore_index=False)

# Check BT are unique
df_xpath.set_index('bt', verify_integrity=True, inplace=True)

# We merge the xpath with the BT data, including the BT absent on either side (outer merge)
df = df.merge(df_xpath, left_on=['ID'], right_on=['bt'], how='outer')

# To csv
df.to_csv('BT-xpath-sfLevel.csv')
