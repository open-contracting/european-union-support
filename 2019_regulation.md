# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

## Create the mapping file

Start with the [fields](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html) identified by the eForms SDK (creates the file if it doesn't exist):

    ./manage.py update-with-sdk output/mapping/eForms/guidance.json

Add details from the 2019 regulation's annex, e.g. if descriptions change:

    ./manage.py update-with-annex output/mapping/eForms/guidance.json

Add the XPath from TED XML:

    ./manage.py update-with-xpath output/mapping/eForms/guidance.json

Add the guidance for TED XML:

    ./manage.py update-with-ted-guidance output/mapping/eForms/guidance.json

## Maintenance

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* Track source files, in order to determine the origin of a change.
* Manage data elements either manually or automatically, but not both, to ease reconciliation.

## Reference

* [eForms FAQ](https://docs.ted.europa.eu/home/eforms/FAQ/index.html)
