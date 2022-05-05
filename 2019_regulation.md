# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

## Create the mapping file

Start with the [fields](https://docs.ted.europa.eu/eforms/0.5.0/fields/index.html) identified by the eForms SDK (creates the file if it doesn't exist):

    ./manage.py update-with-sdk output/mapping/eForms/eforms-guidance.json

Add details from the 2019 regulation's annex:

    ./manage.py update-with-annex output/mapping/eForms/eforms-guidance.json

Add details from the 2015 regulation's guidance:

    ./manage.py update-with-2015-guidance output/mapping/eForms/eforms-guidance.json

## Maintenance

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Reference

* [eForms FAQ](https://docs.ted.europa.eu/home/eforms/FAQ/index.html)
