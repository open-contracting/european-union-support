import os

import pandas as pd

# This script adds or updates
# - legal status fields (M or O)
# - BT descriptions
# - BT data type
# to CSV and JSON guidance files.
# It doesn't add missing BT.
# Before running it, make sure eforms-guidance JSON and CSV are synced by running mapping_spread_guidance.py, as this
# script will update eforms-guidance.csv and overwrite eforms-guidance.json with its content.

os.chdir('output/mapping/eForms')

df_annex = pd.read_csv('annex.csv', index_col=['ID'], sep=';', keep_default_na=False)
df_guidance = pd.read_csv('eforms-guidance.csv', keep_default_na=False)

bts_missing_in_annex = []

for label, row in df_guidance.iterrows():
    bt = row['BT']
    try:
        df_guidance.at[label, 'legal_status'] = df_annex.at[bt, str(row['eformsNotice'])]
        df_guidance.at[label, 'bt_description'] = df_annex.at[bt, 'Description']
        df_guidance.at[label, 'bt_datatype'] = df_annex.at[bt, 'Data type']
    except KeyError:
        if bt not in bts_missing_in_annex:
            print(bt + " doesn't exist in annex")
            bts_missing_in_annex.append(bt)

df_guidance = df_guidance[['id', 'Name', 'eformsNotice', 'sfNotice', 'legal_status', 'eforms_xpath', 'BT',
                           'bt_description', 'bt_datatype', 'sfLevel', 'guidance', 'status', 'comments']]

# To csv
df_guidance.to_csv('eforms-guidance.csv', index_label='id')

if type(df_guidance['eforms_xpath'][0]) == str:
    df_guidance['eforms_xpath'] = df_guidance['eforms_xpath'].str.split(';')

df_guidance.to_json('eforms-guidance.json', orient='records', indent=2, lines=False)
