# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

## Create the mapping file

Start with the [fields](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html) identified by the eForms SDK (creates the file if it doesn't exist):

    ./manage.py update-with-sdk output/mapping/eforms/guidance.yaml

Add details from the 2019 regulation's annex, e.g. if descriptions change:

    ./manage.py update-with-annex output/mapping/eforms/guidance.yaml

Add the XPath from TED XML:

    ./manage.py update-with-xpath output/mapping/eforms/guidance.yaml

Add the guidance for TED XML:

    ./manage.py update-with-ted-guidance output/mapping/eforms/guidance.yaml

Note: This last command reports unmerged rows. As such, it's possible that some TED guidance is missing from the YAML file.

### Data dictionary

Key | Source | Description | Notes
-- | -- | -- | --
id | [eForms SDK](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_field_properties) | Identifier of the field. |
parentNodeId | eForms SDK | Identifier of the node (XML element) that contains the field. |
name | eForms SDK | Short name of the field. |
btId | eForms SDK | Identifier of the business term to which the field corresponds. |
xpathAbsolute | eForms SDK | Location of the field in an XML notice, as an absolute XPath. |
xpathRelative | eForms SDK | Location of the field in an XML notice, relative to its parent node. | Removed.
type | eForms SDK | Technical data type of the field. |
legalType | eForms SDK | Data type of the business term, as indicated in the eForms Regulation. |
maxLength | eForms SDK | Maximum number of characters allowed in the value of the field, optional. | Removed.
[repeatable](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_repeatable) | eForms SDK | Indicates if the field can appear more than once inside its container. | Simplified to the boolean (removed `severity`).
[forbidden](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_forbidden) | eForms SDK | Indicates whether or not the field can be used in specific notice types. | Removed.
[mandatory](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_mandatory) | eForms SDK | Indicates whether or not a field is required to have a value. | Simplified to the boolean (`true` if required on one or more forms).
[codeList](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_codelist) | eForms SDK | Identifier of the code list from which the field value must belong. Applicable only for fields of type "code" or "internal-code" |
[pattern](https://docs.ted.europa.eu/eforms/0.6.0/fields/index.html#_pattern) | eForms SDK | Indicates that the value of the field must match a specific regular expression pattern. | Simplied to the pattern (removed `severity`).
Description | [2019 regulation annex](https://ec.europa.eu/growth/single-market/public-procurement/digital-procurement/eforms_en) | The description of the business term. |
Business groups | 2019 regulation annex | The business groups to which the business term belongs, from top down. |
TED Xpath | [SIMAP](https://simap.ted.europa.eu/en_GB/web/simap/eforms) (13/04/2022) | The TED XPaths matching the eForms field. |
TED guidance | EU profile | The original guidance for the TED XPaths. |

`eForms guidance`, `eForms example`, `OCDS example`, and `sdk` are manually edited as described below.

## Fill in the mapping file

Manually fill in in `eForms guidance`, `eForms example`, `OCDS example` and `sdk`.

1. Look up the business term in the [eForms SDK](https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html)
1. Paste the link to the relevant documentation in `sdk`
1. Copy an abbreviated XML sample to `eForms example`
1. Write the `eForms guidance` and `OCDS example`

When writing the eForms guidance:

* If the eForms field uses a codelist:

  1. Find the authority table in [EU Vocabularies](https://op.europa.eu/en/web/eu-vocabularies/authority-tables)
  1. Copy the "Browse content" link for the relevant authority table

* If a mapping has multiple steps, consider using a numbered list.

## Maintenance

To lint the file, run:

    ./manage.py lint output/mapping/eforms/guidance.yaml

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

## Design

* Track source files, in order to determine the origin of a change.
* Manage data elements either manually or automatically, but not both, to ease reconciliation.

## Reference

* [eForms SDK](https://docs.ted.europa.eu/eforms/0.6.0/) ([all-in-one](https://docs.ted.europa.eu/eforms/0.6.0/schema/all-in-one.html))
* [eForms FAQ](https://docs.ted.europa.eu/home/eforms/FAQ/index.html)

Useful links for authoring mappings:

* [OCDS for EU profile](https://standard.open-contracting.org/profiles/eu/latest/en/forms/)
* [OCDS Extensions Field and Code Search](https://open-contracting.github.io/editor-tools/)
