# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

`Task 5_Support_Standard Forms-eForms mappings_v.3.zip` was received via email from the European Commission.

## Prepopulate with the 2015 guidance

Extract data from the source files:

    ./manage.py extract-indices-mapping
    ./manage.py extract-xpath-mapping

Extract data from another source file:

    ./manage.py extract-hierarchy

Concatenate guidance for the 2015 regulation:

    ./manage.py extract-2015-guidance

Use the files created to prepopulate guidance for the 2019 regulation:

    ./manage.py prepopulate

From here, you can create copies (`eforms-guidance.*`) of the prepopulated files, to add and tailor the guidance for the 2019 regulation.

## Update with the regulation's annex

Add details from the 2019 regulation's annex to the `eforms-guidance.*` files:

    ./manage.py update-with-annex

## Maintenance

`ted-xml-indices.csv` is manually edited. If any XPaths are added to TED-XML, update this file with:

    ./manage.py update-ted-xml-indices

**If any XPath lacks an index, its 2015 guidance cannot be imported by the `prepopulate` command.**

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* The mapping is BT-based and form-based, following the structure of the source files.
* Each source file has a single corresponding command, which extracts data to a tracked file. Corrections to the source file are made here, exclusively. In this way, it is easy to review whether any changes to the final outputs are caused by changes to the source files.
