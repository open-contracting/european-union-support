# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

`Task 5_Support_Standard Forms-eForms mappings_v.3.zip` was received via email from the European Commission.

## Update with the 2015 guidance

Extract data from the source files, mapping Business Terms (BTs) to form indices and to eForms XPaths:

    ./manage.py extract-indices-mapping
    ./manage.py extract-xpath-mapping

Concatenate guidance for the 2015 regulation:

    ./manage.py extract-2015-guidance

Add details from the output of the above to a file:

    ./manage.py update-with-2015-guidance output/mapping/eForms/eforms-guidance.json

If the file doesn't exist, it is created.

Legend for Level column (copied from source file):

* *new term*: New information available for this notice. There is no matching available between the Standard Form and the corresponding eForms identified
* *new term overall*: New information introduced with eForms overall

## Update with the regulation's annex

Add details from the 2019 regulation's annex to a file:

    ./manage.py update-with-annex output/mapping/eForms/eforms-guidance.json

## Maintenance

`ted-xml-indices.csv` is manually edited. If any XPaths are added to TED-XML, update this file with:

    ./manage.py update-ted-xml-indices

**If any XPath lacks an index, its 2015 guidance cannot be imported by the `prepopulate` command.**

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* The mapping is BT-based and form-based, following the structure of the source files.
* Each source file has a single corresponding command, which extracts data to a tracked file. Corrections to the source file are made by these commands, exclusively. In this way, it is easy to review whether any changes to the final outputs are caused by changes to the source files.
* Manually-edited files start with minimal information. Additional information can then be added automatically from other sources. When other sources change, it is simpler to update a manually-edited file than it is to regenerate an initial version of the manually-edited file and compare changes.
* Columns are not renamed from source files, to reduce human memory load.
