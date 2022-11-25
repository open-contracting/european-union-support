# 2019 Regulation (eForms)

## Download source files

    fish script/2019_download.fish

## Create the mapping file

Start with the [fields](https://docs.ted.europa.eu/eforms/latest/fields/index.html) identified by the eForms SDK (creates the file if it doesn't exist):

    ./manage.py update-with-sdk output/mapping/eforms/guidance.yaml

Add details from the 2019 regulation's annex, e.g. if descriptions change:

    ./manage.py update-with-annex output/mapping/eforms/guidance.yaml

Add the XPath from TED XML:

    ./manage.py update-with-xpath output/mapping/eforms/guidance.yaml

Add the guidance for TED XML:

    ./manage.py update-with-ted-guidance output/mapping/eforms/guidance.yaml

Note: This last command reports unmerged rows. As such, it's possible that some [TED guidance](https://standard.open-contracting.org/profiles/eu/latest/en/forms/) is missing from the YAML file.

### Data dictionary

Key | Source | Description | Notes
-- | -- | -- | --
id | [eForms SDK](https://docs.ted.europa.eu/eforms/latest/fields/index.html#_field_properties) | Identifier of the field. |
parentNodeId | eForms SDK | Identifier of the node (XML element) that contains the field. |
name | eForms SDK | Short name of the field. |
btId | eForms SDK | Identifier of the business term to which the field corresponds. |
xpathAbsolute | eForms SDK | Location of the field in an XML notice, as an absolute XPath. | Should appear in the `eForms example`.
type | eForms SDK | Technical data type of the field. | Should match the OCDS field's type.
idScheme | eForms SDK | Indicates the identifier scheme for this `id` field.
idSchemes | eForms SDK | Indicates the identifier schemes for this `id-ref` field.
[repeatable](https://docs.ted.europa.eu/eforms/latest/fields/index.html#_dynamic_properties) | eForms SDK | Indicates if the field can appear more than once inside its container. | Simplified to the boolean (removed `severity`).
mandatory | eForms SDK | Indicates whether or not a field is required to have a value. | Simplified to the boolean (`true` if required on one or more forms).
codeList | eForms SDK | Identifier of the code list from which the field value must belong. Applicable only for fields of type "code" or "internal-code" | Simplified to the codelist (removed `severity`, `value.type`, `value.parentId`).
pattern | eForms SDK | Indicates that the value of the field must match a specific regular expression pattern. | Simplied to the pattern (removed `severity`).
assert | eForms SDK | Gives an assertion, as a boolean EFX expression, that is expected to evaluate to "true". |
inChangeNotice | eForms SDK | Indicates whether the values of the field can be modified in a change notice, compared to the notice being changed (the original notice). |
privacy | eForms SDK | The information necessary for the mechanism by which the field can be withheld from publication for a defined period. |
Description | [Regulation annex](https://ec.europa.eu/growth/single-market/public-procurement/digital-procurement/eforms_en) | The description of the business term. |
Business groups | Regulation annex | The business groups to which the business term belongs, from top down. | eForms has a hierarchy of BGs. Use [business-groups.csv](https://github.com/open-contracting/european-union-support/blob/main/output/mapping/eforms/business-groups.csv) to look up the hierarchy and descriptions for each group.
TED Xpath | [SIMAP](https://simap.ted.europa.eu/en_GB/web/simap/eforms) (13/04/2022) | The TED XPaths matching the eForms field. |
TED guidance | EU profile | The original guidance for the TED XPaths. |

`eForms guidance`, `eForms example`, `OCDS example`, and `sdk` are manually edited as described below.

### Removed metadata

The following keys from the fields metadata are removed.

Key | Description | Reason
-- | -- | --
xpathRelative | Location of the field in an XML notice, relative to its parent node. | Substring of `xpathAbsolute`.
legalType | Data type of the business term, as indicated in the eForms Regulation. | Redundant with `type`.
maxLength | Maximum number of characters allowed in the value of the field, optional. | The only fields with a maxLength less than 400 are identifiers, phone numbers and percentages.
forbidden | Indicates whether or not the field can be used in specific notice types. | It isn't informative to know which forms a field can't appear on.

The correspondence between `legalType` and `type` is:

`legalType` | `type` | Notes
-- | -- | --
`IDENTIFIER` | `id`, `id-ref` | `code` exceptionally used for BT-195 and BT-5011.
`INDICATOR` | `indicator`, `code` | Overlaps semantically with `CODE`.
`CODE` | `code` | `id` and `text-multilingual` exceptionally used for other versions of BT-01.
`TEXT` | `text`, `text-multilingual`, `phone`, `email` | `id` exceptionally used for BT-22 and for part of BT-09. `code` exceptionally used for code version of BT-67.
`DATE` | `date`, `time` |
`URL` | `url` |
`VALUE` | `amount` |
`NUMBER` | `number`, `integer` | `code` exceptionally used for the withheld publication of BT-712.
`DURATION` | `measure` |

## Fill in the mapping file

Manually fill in in `eForms guidance`, `eForms example`, `OCDS example` and `sdk`.

1. Look up the business term in the [eForms SDK](https://docs.ted.europa.eu/eforms/latest/schema/all-in-one.html)
1. Paste the link to the relevant documentation in `sdk`
1. Copy an abbreviated XML sample to `eForms example`
1. Write the `eForms guidance` and `OCDS example`

When writing the eForms guidance:

* Check for [open issues](https://github.com/open-contracting/european-union-support/issues) for the business term
* If the eForms field uses a codelist:

  1. Find the authority table in [EU Vocabularies](https://op.europa.eu/en/web/eu-vocabularies/authority-tables)
  1. Copy the "Browse content" link for the relevant authority table

* If a mapping has multiple steps, consider using a numbered list.
* If a mapping requires the creation of a new field, you don't need to create the field yet. Extensions can be updated once the mapping is completed and reviewed.
* To see the relationship between elements and the overall structure of the notices, you can check the [XML notice examples](https://github.com/OP-TED/eForms-SDK/tree/develop/examples/notices). The examples suffixed with '_maximal' contain all possible elements and are annotated with the business term identifier for each element.
* If the guidance involves mapping only the element specified in `xpathAbsolute`, it is sufficient to write 'Map to `<OCDS field>`' without explicitly referencing the element. If the guidance involves mapping several elements or attributes, reference the element specified in `xpathAbsolute` by its name, e.g. 'Map `cbc:ID` to `<OCDS field>`'.
* To reference other XML elements, use [XML Path Language (XPath)](https://www.w3.org/TR/1999/REC-xpath-19991116/). In particular:
  * Do not wrap the XPath in angle brackets (`<` and `>`)
  * Fully reference the XPath in relation to the element specified in `xpathAbsolute`, using `ancestor::` etc. as needed
  * Use `/` as the delimiter between elements
  * Use `element[@attribute_name]` to reference XML attributes
  * Don't prefix the XPath with the word 'XPath' unless it isn't clear from the context that the reference is to an XPath

## Maintenance

To lint the file, get the EU profile's patched release schema:

    curl -O https://standard.open-contracting.org/profiles/eu/latest/en/_static/patched/release-schema.json

Then, run:

    ./manage.py lint output/mapping/eforms/guidance.yaml

To update the progress of the guidance for the 2019 regulation, run:

    ./manage.py statistics

### Upgrade SDK version

1. Run:

        fish script/2019_download.fish
        ./manage.py update-with-sdk --verbose output/mapping/eForms/guidance.yaml
        ./manage.py update-with-annex output/mapping/eforms/guidance.yaml
        ./manage.py update-with-ted-guidance output/mapping/eforms/guidance.yaml

1. Find and replace `eforms/<old-version>` with `eforms/<new-version>`
1. Replace the older version with the new version following `sdk_regex.sub` in `manage.py`
1. Run `./manage.py lint output/mapping/eforms/guidance.yaml`

## Design

* Track source files, in order to determine the origin of a change.
* Manage data elements either manually or automatically, but not both, to ease reconciliation.

## Reference

### eForms

* [SDK](https://docs.ted.europa.eu/eforms/latest/) ([all-in-one](https://docs.ted.europa.eu/eforms/latest/schema/all-in-one.html))
* [FAQ](https://docs.ted.europa.eu/home/eforms/FAQ/index.html)
* [Examples](https://github.com/OP-TED/eForms-SDK/tree/main/examples)

The Publications Office has also started work on a [TED XML Data Converter](https://github.com/OP-TED/ted-xml-data-converter). However, as of 2022-07-07, it is incomplete (it covers only F05, F12, F21, F22, F23, F24) and has not been updated since its first publication on 2022-05-20. Thus, it is not being used as an authoritative source (e.g. it could have been used in the "Add the XPath from TED XML" step). It does include a useful table of [XML elements that can't be converted from TED to eForms](https://github.com/OP-TED/ted-xml-data-converter/blob/main/ted-elements-not-convertible.md). **Note:** Development has resumed: [0.4.0](https://github.com/OP-TED/ted-xml-data-converter/releases/tag/0.4.0), [0.5.0](https://github.com/OP-TED/ted-xml-data-converter/releases/tag/0.5.0).

### OCDS

* [OCDS for EU profile](https://standard.open-contracting.org/profiles/eu/latest/en/forms/)
* [OCDS Extensions Field and Code Search](https://open-contracting.github.io/editor-tools/)
