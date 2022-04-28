# 2019 Regulation (eForms)

## Download prerequisites

    fish scripts/2019_download.fish

`Task 5_Support_Standard Forms-eForms mappings_v.3.zip` was received via email from the European Commission.

## Pre-process prerequisites

    ./manage.py extract_docx
    ./manage.py extract_xlsx

## Concatenate the 2015 guidance

    ./manage.py concatenate

## Importing guidance from SF

Through a BT/SF level mapping, OCDS guidance for eForms can be imported from standard forms.

Required files:

- `output/mapping/eForms/BT-xpath-sfLevel.csv`
- `output/mapping/eForms/bg_bt.csv` (BT/BG mapping extracted from the [eForms annex](https://ec.europa.eu/docsroom/documents/43488))
- `output/mapping/shared/concatenated.csv` (concatenated standard forms OCDS guidance generated above)

This is done with the following command and creates `output/mapping/eForms/BT-xpath-sfGuidance.json`:

```bash
python scripts/mapping_import_sf_guidance.py
```

`output/mapping/eForms/eforms-guidance.csv` and its JSON counterpart contain the OCDS guidance to map eForms XML elements to OCDS data structures.
These files are copies of `BT-xpath-sfGuidance.json` that have later been updated, improved. There is unfortunately no automatic way to import
updated standard form guidance into `eforms-guidance.csv` and `eforms-guidance.json` as 

- some of the imported standard forms guidance has been adapted to the eForms structure and semantics
- there is no way to distinguish the imported guidance that has been left untouched from the imported guidance that has been adapted

Automatically overwriting the guidance that has been imported would consequently lead to the loss of the adapted guidance. The recommended method is
to pick the BTs that had their standard form guidance updated and manually update them in `eforms-guidance.json`, taking into account the
context of eForms and adapt the guidance when necessary. Then, spread the guidance with `scripts/mapping_spread_guidance.py` (see below)

## Spreading the guidance of BTs for all notices

In the guidance files (`output/mapping/eForms/eforms-guidance.*`), each row represents the details of the combination of a BT and a notice in which it is
present. The guidance of BT applies for all the notices where it is present, this guidance must consequently be spread every time a BT has its guidance
updated.

The end of the script is tweaked to return the `id` of the next row to tackle (e.g. next with empty guidance), so that you don't need to scroll too much.

Required files:

- `output/mapping/eForms/eforms-guidance.json`

This is done with the following command, updates `eforms-guidance.json` and `output/mapping/eForms/eforms-guidance.csv`:

```bash
python scripts/mapping_spread_guidance.py
```

## Showing statistics about the progress of the eForms mapping

This script gives an overview of the progress of the mapping. Its output should regularly be added to `output/mapping/eForms/README.md`
to make this progress public.

Required files:

- `output/mapping/eForms/eforms-guidance.csv`

This is done with the following command:

```shell
python scripts/mapping_eforms_stats.py
```

## Updating BT details from the Annex

Required files:

- `output/mapping/eForms/annex.csv`, where the updated BT details come from
- `output/mapping/eForms/eforms-guidance.csv`

This is done with the following command:

```shell
python scripts/mapping_add_annex_bt_details.py
```

## Guidance in JSON

The guidance is easier to edit in JSON format.
