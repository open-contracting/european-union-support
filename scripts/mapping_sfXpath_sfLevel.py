import sys
import os
from pathlib import Path
import pandas as pd

# This script spreads the index values across all mappings. The objective is that if an index is set once for a given
# xpath, it will be added for every other occurence of this xpath in other files
# This SF xpath-SF level mapping will enable a SF xpath-eForms BT mapping, thus an eFormBT-OCDS mapping

# directory = dir where the SF-OCDS mappings CSV are stored
if len(sys.argv) >= 2:
    directory = sys.argv[1]
else:
    os.chdir('output/mapping/sf')
    directory = os.getcwd()

csvs = Path(directory).glob('*.csv')

# For each CSV, only keep the xpath and index (SF level/section) columns and append it to the df_concat dataframe
df_concat = pd.DataFrame()
for file in csvs:
    df = pd.read_csv(file, usecols=['xpath', 'index'], keep_default_na=False)
    *others, df['file'] = str(file).split('/')
    df_concat = pd.concat([df_concat, df], ignore_index=True)

# Remove duplicate xpath/index pairs and store the result
df_concat.sort_values(by=['index'], inplace=True, ascending=False)
df_concat.drop_duplicates(['xpath'], inplace=True)
df_concat.to_csv(directory + '/shared/concatenated.csv')

# Check xpath are unique
df_concat.set_index('xpath', verify_integrity=True, inplace=True)

# Populate levels in original csvs from concatenated csvs
csvs = Path(directory).glob('*.csv')
for file in csvs:
    df = pd.read_csv(file, keep_default_na=False)
    df = df.merge(df_concat[['index']], how='left', on=['xpath'], suffixes=('_old',''))
    df = df.drop(columns=['index_old'])
    # TODO restructure project tree
    df.to_csv(directory + '/spreadIndex/' + str(file).split('/')[-1])


