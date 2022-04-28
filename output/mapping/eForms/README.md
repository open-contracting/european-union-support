# Description of the files

- annex.csv: CSV copy of the annex to the eForms directive downloaded at [https://ec.europa.eu/docsroom/documents/43488]
- bg_bt.csv: for each business term (BT), the business groups (BG) it belongs. This file is used in the script `mapping_import_sf_guidance.py` in order to add this information in the guidance CSV.
- BT-xpath-sfGuidance.csv and BT-xpath-sfGuidance.json: this is the result of running `mapping_import_sf_guidance.py`. It is a guidance file pre-filled with guidance imported from the standard forms guidance. This is the same as eforms-guidance.csv and eforms-guidance.json, but without the new guidance and the corrections made to the imported guidance.
- BT_xpath_corrections.csv: corrections to the official BT to Xpath mapping
- common_operations.md: guidance for common operations for eForms to OCDS mapping
- eforms-guidance.csv and eforms-guidance.json: intially produced by `mapping_import_sf_guidance.py`, then filled by hand and with `mapping_spread_guidance.py`. It is the working file to edit the guidance to map eForms BT to OCDS. A CSV copy is generated when `mapping_spread_guidance.py` is run. The CSV copy is not supposed to be edited by hand.
- forms_noticeTypes.csv: a table that gives, for each eForms notice, its form type, its document type and the related legislation.
- xpath_bt_mapping.csv: handmade mapping table made from the tables in "XPATHs provisional release v. 1.0.docx" published by the EU in May 2020 on their [eForms news](https://simap.ted.europa.eu/en_GB/web/simap/eforms)

# eForms mapping progress   

Tracking of the progress of the guidance that will help implementors to publish OCDS data from eForms data.

The guidance data (WIP) is in [CSV](https://github.com/open-contracting/european-union-support/blob/eForms/output/mapping/eForms/eforms-guidance.csv) and [indented JSON](https://github.com/open-contracting/european-union-support/blob/eForms/output/mapping/eForms/eforms-guidance.json).

Total number of rows (BT + notice number pair): 5103 (100%)


- Ready for review: 4514 (88.45% of total)
    - imported from standard forms guidance: 27 rows (0.529% of total)
    - new guidance: 4487 rows (87.92% of total)
        - per BT legal status
            - Mandatory: 1761 rows (100.0% of all M)
            - Optional: 2217 rows (80.64% of all O)
    - per BT (instead of per BT/notice pair)
        - total number of BT: 260
        - BTs that have guidance ready for review: 214 (82.3%)
        - BTs that are still not ready (no guidance or issue pending): 46 (17.6%)
- With [open issue](https://github.com/open-contracting/european-union-support/labels/eforms): 74 rows (1.450% of total)
  - with guidance: 74 rows
  - without guidance yet: 0 rows
  - per BT legal status
            - Mandatory: 0 rows (0.0% of all M)
            - Optional: 66 rows (2.400% of all O)
- No guidance and no issue (= untouched yet): 515 rows (10.09% of total)

