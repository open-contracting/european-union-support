import pandas as pd

# Read the eForms guidance file
df: pd.DataFrame = pd.read_csv('output/mapping/eForms/eforms-guidance.csv', keep_default_na=False)
df_wIssue = df.loc[df['status'].str.startswith('issue')]

wGuidance = str(len(df.loc[df['guidance'] != ''].index))
manualGuidance = str(len(df.loc[df['status'].str.startswith('done')].index))
wIssue = str(df_wIssue.index.size)
wIssuewGuidance = str(len(df_wIssue.loc[df['guidance'] == ''].index))
wIssuewoGuidance = str(len(df_wIssue.loc[df['guidance'] != ''].index))
importedGuidance = str(len(df.loc[df['status'] == 'imported from standard forms'].index))
totalGuidance = str(len(df.index))
woIssuewoGuidance = str(len(df.loc[(df['guidance'] == '') & (df['status'] == '')].index))
totalM = str(len(df.loc[(df['legal_status'] == 'M')].index))
totalO = str(len(df.loc[(df['legal_status'] == 'O')].index))
doneM = str(len(df.loc[((df['legal_status'] == 'M') & (df['status'].str.startswith('done')))].index))
doneO = str(len(df.loc[(df['legal_status'] == 'O') &
                       (df['status'].str.startswith('done'))].index))
issueM = str(len(df_wIssue.loc[(df['legal_status'] == 'M')].index))
issueO = str(len(df_wIssue.loc[(df['legal_status'] == 'O')].index))
readyReview = int(importedGuidance) + int(manualGuidance)

# Stats per BT (instead of BT/notice pair)
df_bts = df.drop_duplicates(subset='BT')
bts_number = df_bts.index.size
status_done_nb = df_bts[df_bts['status'].str.startswith('done')].index.size
status_not_done_nb = bts_number - status_done_nb

print(f'''# Description of the files

- annex.csv: CSV copy of the annex to the eForms directive downloaded at [https://ec.europa.eu/docsroom/documents/43488]
- bg_bt.csv: for each business term (BT), the business groups (BG) it belongs. This file is used in the script `mapping_import_sf_guidance.py` in order to add this information in the guidance CSV.
- BT-xpath-sfGuidance.csv and BT-xpath-sfGuidance.csv: this is the result of running `mapping_import_sf_guidance.py`. It is a guidance file pre-filled with guidance imported from the standard forms guidance. This is the same as eforms-guidance.csv and eforms-guidance.json, but without the new guidance and the corrections made to the imported guidance.
- BT-xpath-sfLevel.csv: this file is the result of running `mapping_BT_xpath_sfLevel.py`. It is a file that maps business terms with the corresponding eForms Xpath and standard forms levels (index).
- BT_xpath_corrections.csv: corrections to the official BT to Xpath mapping
- common_operations.md: guidance for common operations for eForms to OCDS mapping
- eforms-guidance.json and eforms-guidance.json: intially produced by `mapping_import_sf_guidance.py`, then filled by hand and with `mapping_spread_guidance.py`. It is the working file to edit the guidance to map eForms BT to OCDS. A CSV copy is generated when `mapping_spread_guidance.py` is run. The CSV copy is not supposed to be edited by hand.
- forms_noticeTypes.csv: a table that gives, for each eForms notice, its form type, its document type and the related legislation.
- xpath_bt_mapping.csv: handmade mapping table made from the tables in "XPATHs provisional release v. 1.0.docx" published by the EU in May 2020 on their [eForms news](https://simap.ted.europa.eu/en_GB/web/simap/eforms)

# eForms mapping progress

Tracking of the progress of the guidance that will help implementors to publish OCDS data from eForms data.

The guidance data (WIP) is in [CSV](https://github.com/open-contracting/european-union-support/blob/eForms/output/mapping/eForms/eforms-guidance.csv) and [indented JSON](https://github.com/open-contracting/european-union-support/blob/eForms/output/mapping/eForms/eforms-guidance.json).

Total number of rows (BT + notice number pair): {totalGuidance} (100%)


- Ready for review: {readyReview} ({str(int(readyReview) / int(totalGuidance) * 100)[0:5]}% of total)
    - imported from standard forms guidance: {importedGuidance} rows ({str(int(importedGuidance) / int(totalGuidance) * 100)[0:5]}% of total)
    - new guidance: {manualGuidance} rows ({str(int(manualGuidance) / int(totalGuidance) * 100)[0:5]}% of total)
        - per BT legal status
            - Mandatory: {doneM} rows ({str(int(doneM) / int(totalM) * 100)[0:5]}% of all M)
            - Optional: {doneO} rows ({str(int(doneO) / int(totalO) * 100)[0:5]}% of all O)
    - per BT (instead of per BT/notice pair)
        - total number of BT: {bts_number}
        - BTs that have guidance ready for review: {str(status_done_nb)} ({str((status_done_nb / bts_number) * 100)[0:4]}%)
        - BTs that don't have satisfactory guidance (no guidance or issue pending): {str(status_not_done_nb)} ({str((status_not_done_nb / bts_number) * 100)[0:4]}%)
- With [open issue](https://github.com/open-contracting/european-union-support/labels/eforms): {wIssue} rows ({str(int(wIssue) / int(totalGuidance) * 100)[0:5]}% of total)
  - with guidance: {wIssuewGuidance} rows
  - without guidance yet: {wIssuewoGuidance} rows
  - per BT legal status
            - Mandatory: {issueM} rows ({str(int(issueM) / int(totalM) * 100)[0:5]}% of all M)
            - Optional: {issueO} rows ({str(int(issueO) / int(totalO) * 100)[0:5]}% of all O)
- No guidance and no issue (= untouched yet): {woIssuewoGuidance} rows ({str(int(woIssuewoGuidance) / int(totalGuidance) * 100)[0:5]}% of total)
''')  # noqa: E501
