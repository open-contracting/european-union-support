# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

## Create the mapping file

Start with the [fields](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html) identified by the eForms SDK (creates the file if it doesn't exist):

    ./manage.py update-with-sdk output/mapping/eForms/guidance.yaml

Add details from the 2019 regulation's annex, e.g. if descriptions change:

    ./manage.py update-with-annex output/mapping/eForms/guidance.yaml

Add the XPath from TED XML:

    ./manage.py update-with-xpath output/mapping/eForms/guidance.yaml

Add the guidance for TED XML:

    ./manage.py update-with-ted-guidance output/mapping/eForms/guidance.yaml

Manually fill in in `eForms guidance`, `eForms example`, `OCDS example` and `sdk`.

1. Look up the business term in the [eForms SDK](https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html)
1. Paste the link to the relevant documentation in `sdk`
1. Copy an abbreviated XML sample to `eForms example`
1. Write the `eForms guidance` and `OCDS example`

If the eForms field uses a codelist:

1. Find the authority table in [EU Vocabularies](https://op.europa.eu/en/web/eu-vocabularies/authority-tables)
1. Copy the "Browse content" link for the relevant authority table

## Maintenance

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* Track source files, in order to determine the origin of a change.
* Manage data elements either manually or automatically, but not both, to ease reconciliation.

## Reference

* [eForms SDK](https://docs.ted.europa.eu/eforms/0.6.0/) ([all-in-one](https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html))
* [eForms FAQ](https://docs.ted.europa.eu/home/eforms/FAQ/index.html)
