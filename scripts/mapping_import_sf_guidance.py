import pandas as pd

# This script imports the guidance from the output/mapping folder, using the sfLevel as a shared key.
# The guidance is imported into a copy of output/mapping/eForms/BT-sfLevel.csv

# Read the BT-sfLevel mapping (base frame)
df = pd.read_csv('output/mapping/eForms/BT-xpath-sfLevel.csv', keep_default_na=False)

# Rename columns
df['BT'] = df['ID']
df['sfLevel'] = df['Level']

# Remove the BG (Business Group) rows since they don't have xpath and most likely no guidance
df = df[df['BT'].str.contains('BT')]

# Trim BT names
df['Name'] = [x.lstrip(' ') for x in df['Name']]

# df = df[df['Name'].str.contains('Identifier') == False]

# Add the BG levels
df_bg = pd.read_csv('output/mapping/eForms/bg_bt.csv', index_col='BT', keep_default_na=False)
df = df.merge(df_bg, on=['BT'], how='left').sort_values(['eformsNotice', 'BG_lvl1', 'BG_lvl2', 'BG_lvl3', 'BT'])

# Read the concatenated guidance file, and remove the rows that don't have a valid 'index' (sfLevel)
df_sf_concatenated = pd.read_csv('output/mapping/shared/concatenated.csv', keep_default_na=False)
df_sf_concatenated = df_sf_concatenated.loc[(df_sf_concatenated['index'] != '')
                                            & (df_sf_concatenated['index'] != 'no index')]

# Merge the two frames (could it be a join, i.e be based on labels?)
df: pd.DataFrame = df.merge(df_sf_concatenated, how='left', left_on=['sfLevel'], right_on=['index'])
df.drop_duplicates(['BT', 'eformsNotice'], inplace=True)

# Remove unwanted columns
to_remove = [
    'Element',
    'Legal Status',
    'label-key',
    'file',
    'index',
    'name',
    'ID',
    'Level',
    'Description',
    'Repeatable',
    'Datatype',
    'xpath',
    'Form type'
]



for column in df.columns:
    if column in to_remove or 'Unnamed' in column:
        df.drop([column], inplace=True, axis='columns')


# Add new columns
df.loc[df['guidance'].str.len() > 0, 'status'] = 'imported_from_sf'
df['comments'] = ''

to_add = [
    'status',
    'comments'
]

# To csv
df.to_csv('output/mapping/eForms/BT-xpath-sfGuidance.csv', index_label='id')

# Split xpaths:
if type(df['eforms_xpath'][0]) == str:
    df['eforms_xpath'] = df['eforms_xpath'].str.split(';')

# To JSON
df.to_json('output/mapping/eForms/BT-xpath-sfGuidance.json', orient='records', indent=2, lines=False)


