import pandas as pd
import ast


def spreadGuidance(row1: pd.Series) -> None:
    # We only go through the rows with the same BT as the 'good' row.
    for label2, row2 in df.loc[df['BT'] == row1['BT']].iterrows():
        # We only alter the rows that either have not been touched before (= empty status)
        # or those that have already received the guidance from the same 'good' row
        # (status = {status} spread from notice X)
        # row1 = 'good' row whose data is spread to row2
        if row2['status'] in ['',
                              'done' + ' (spread from notice ' + row1['eformsNotice'] + ')',
                              'issue' + ' (spread from notice ' + row1['eformsNotice'] + ')',
                              'imported from standard forms'] \
                and row1['eformsNotice'] != row2['eformsNotice']:
            df.loc[label2, 'guidance'] = row1['guidance']
            df.loc[label2, 'status'] = row1['status'] + ' (spread from notice ' + row1['eformsNotice'] + ')'
            df.loc[label2, 'comments'] = row1['comments']
        else:
            # This prints mostly when row1 is the same as row2, in which case it can be ignored.
            message = '{bt} ({btName}): data from {notice} (status: {status}) did not spread to {notice2} ' \
                      '(status: {status2}).'
            print(message.format(bt=row1['BT'],
                                 btName=row1['Name'],
                                 notice=row1['eformsNotice'],
                                 status=row1['status'],
                                 notice2=row2['eformsNotice'],
                                 status2=row2['status']))


df = pd.read_json('output/mapping/eForms/eforms-guidance.json', orient='records',
                  dtype={'eformsNotice': str, 'sfNotice': str, 'eforms_xpath': list})
for label, row in df.iterrows():

    # the eforms_xpath list of xpath strings got converted to a single string. The code below prevents it.
    try:
        eforms_xpath_eval = ast.literal_eval(row['eforms_xpath'][0])
        if len(row['eforms_xpath']) == 1 and type(eforms_xpath_eval) == list:
            df.at[label, 'eforms_xpath'] = eforms_xpath_eval
    except SyntaxError:
        pass
    # The guidance of a row with status 'done' is considered good enough to be spread to the same BT on other notices.
    if row['status'] == 'done' or row['status'] == 'issue':
        spreadGuidance(row)
        df.loc[label, 'status'] = row['status'] + ' and spread'
    if row['status'] == '' and len(row['guidance']) > 0:
        df.loc[label, 'status'] = 'imported from standard forms'

df.to_csv('output/mapping/eForms/eforms-guidance.csv', index_label='id')

if type(df['eforms_xpath'][0]) == str:
    df['eforms_xpath'] = df['eforms_xpath'].str.split(',')

df.to_json('output/mapping/eForms/eforms-guidance.json', orient='records', indent=2, lines=False)

# Gives the next guidance row id to work on (optional or mandatory BT)
todonext = df[(df['eformsNotice'].isin(["1", "4", "7", "10", "16", "29"]))
              & ~(df['comments'].str.contains(r'/(73|84|85)$'))
              & ~(df['status'].str.contains('done'))
              # & (df['status'].str.startswith('issue')
              ]
print("Next id to check: " + str(todonext.head(n=1).index[0]))
