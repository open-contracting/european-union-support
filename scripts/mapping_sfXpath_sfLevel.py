import sys
import os
import time
from pathlib import Path
import pandas as pd

# This script spreads the index values across all mappings.
# The objective is that if an index is set once for a given
# xpath, it will be added for every other occurence of
# this xpath in other files
# This SF xpath-SF level mapping will enable a SF xpath-eForms
# BT mapping, thus an eFormBT-OCDS mapping

# directory = dir where the SF-OCDS mappings CSV are stored
if len(sys.argv) >= 2:
    directory = sys.argv[1]
else:
    os.chdir('output/mapping')
    directory = os.getcwd()

csvs = Path(directory).glob('*.csv')

identifiers = pd.read_csv('eForms/standard-form-element-identifiers.csv')

# The list of CSVs is built in order to have them sorted by last modification time
# This enable the index values that are edited last to be applied to all other CSVs, instead of the first
# occurrence in alphabetical order of file names (F01, F02, etc.)
csvsTime = []

for file in csvs:
    lastModified = time.ctime(os.path.getmtime(file))
    fileObj = {'path': file, 'time': lastModified}
    csvsTime.append(fileObj)

csvsTime = sorted(csvsTime, key=lambda item: item['time'], reverse=True)

# For each CSV, only keep the xpath and index (SF level/section) columns and append it to the df_concat dataframe
df_concat = pd.DataFrame()
for file in csvsTime:
    df = pd.read_csv(file['path'], usecols=[
                 'xpath', 'guidance', 'label-key']
                 , keep_default_na=False)
    df = pd.merge(df, identifiers, 'left', on='xpath')
    *others, df['file'] = str(file['path']).split('/')
    df_concat = pd.concat([df_concat, df], ignore_index=True)

# Store the results so that other scripts can reuse it
df_concat.to_csv(directory + '/shared/concatenated.csv', columns=['xpath', 'label-key', 'index', 'guidance', 'file'])

# Remove duplicate xpath/index pairs
# df_concat.sort_values(by=['index'], inplace=True, ascending=False)
df_concat.drop_duplicates(['xpath', 'label-key'],
                          ignore_index=True, keep='first', inplace=True)

# Check xpath are unique
# df_concat.set_index('xpath', verify_integrity=True, inplace=True)

# Populate levels in original csvs from concatenated csvs
# csvs = Path(directory).glob('*.csv')
# for file in csvs:
#     df = pd.read_csv(file, keep_default_na=False)
#     df = df.merge(df_concat, how='left', on=[
#                   'xpath', 'label-key'], suffixes=('_old', ''))
#     df = df.drop(columns=['index_old'])
#     df = df[['xpath', 'label-key', 'index', 'comment', 'guidance']]
#     df.to_csv(str(file), index=False)
