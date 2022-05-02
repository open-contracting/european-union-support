# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

`Task 5_Support_Standard Forms-eForms mappings_v.3.zip` was received via email from the European Commission.

## Prepopulate 2019 guidance

Extract data from the source files:

    ./manage.py extract-indices-mapping
    ./manage.py extract-xpath-mapping

Extract data from another source file:

    ./manage.py extract-hierarchy

Concatenate guidance for the 2015 regulation:

    ./manage.py extract-2015-guidance

Use the files created to prepopulate guidance for the 2019 regulation:

    ./manage.py prepopulate

From here, you can create copies of the prepopulated files, to add and tailor the guidance for the 2019 regulation.

## Maintenance

`ted-xml-indices.csv` is manually edited. If any XPaths are added to TED-XML, update this file with:

    ./manage.py update-ted-xml-indices

**If any XPath lacks an index, its 2015 guidance cannot be imported by the `prepopulate` command.**

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* The mapping is BT-based and form-based, following the structure of the source files.
* Each source file has a single corresponding command, which extracts data to a tracked file. Corrections to the source file are made here, exclusively. In this way, it is easy to review whether any changes to the final outputs are caused by changes to the source files.

---

## Spreading the guidance of BTs for all notices

In the guidance files (`output/mapping/eForms/eforms-guidance.*`), each row represents the details of the combination of a BT and a notice in which it is
present. The guidance of BT applies for all the notices where it is present, this guidance must consequently be spread every time a BT has its guidance
updated.

The end of the script is tweaked to return the `id` of the next row to tackle (e.g. next with empty guidance), so that you don't need to scroll too much.

Required files:

- `output/mapping/eForms/eforms-guidance.json`

This is done with the following command, updates `eforms-guidance.json` and `output/mapping/eForms/eforms-guidance.csv`:

    python script/mapping_spread_guidance.py

## Updating BT details from the Annex

Required files:

- `output/mapping/eForms/annex.csv`, where the updated BT details come from
- `output/mapping/eForms/eforms-guidance.csv`

This is done with the following command:

    python script/mapping_add_annex_bt_details.py

# Description of the files

- annex.csv: CSV copy of the annex to the eForms directive downloaded at [https://ec.europa.eu/docsroom/documents/43488]
- BT-xpath-sfGuidance.csv and BT-xpath-sfGuidance.json: this is the result of running `mapping_import_sf_guidance.py`. It is a guidance file pre-filled with guidance imported from the standard forms guidance. This is the same as eforms-guidance.csv and eforms-guidance.json, but without the new guidance and the corrections made to the imported guidance.
- common_operations.md: guidance for common operations for eForms to OCDS mapping
- eforms-guidance.csv and eforms-guidance.json: intially produced by `mapping_import_sf_guidance.py`, then filled by hand and with `mapping_spread_guidance.py`. It is the working file to edit the guidance to map eForms BT to OCDS. A CSV copy is generated when `mapping_spread_guidance.py` is run. The CSV copy is not supposed to be edited by hand.
