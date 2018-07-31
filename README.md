# TED XSD parser

## Usage

### Download prerequisites

Download prerequisites (fish shell):

    mkdir -p source
    cd source

    # Get the mapping from label keys to text labels.
    # http://publications.europa.eu/mdr/eprocurement/ted/index.html
    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/XML schema 2.0.9/Forms_Labels_R209S01.zip'
    unzip Forms_Labels_R209S01.zip
    in2csv 'Forms labels R2.09.xlsx' > 'Forms labels R2.09.csv'
    rm -f Forms_Labels_R209S01.zip 'Forms labels R2.09.xlsx'

    # Get the template PDFs containing label keys.
    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/XML schema 2.0.9/Forms_Templates_R209S01.zip'
    unzip Forms_Templates_R209S01.zip
    rm -rf Forms_Templates_R209S01.zip __MACOSX

    # Get the English PDFs.
    # http://simap.ted.europa.eu/standard-forms-for-public-procurement
    mkdir -p English
    for i in 01 02 03 14 20; curl -o English/EN_F$i.pdf http://simap.ted.europa.eu/documents/10184/99173/EN_F$i.pdf; end

    # Get the XML schema.
    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/TEDFTP_Schema_20180704_TED_publication.zip'
    unzip TEDFTP_Schema_20180704_TED_publication.zip TED_publication_R2.0.9.S03.E01_006-20180608.zip
    unzip TED_publication_R2.0.9.S03.E01_006-20180608.zip -d TED_publication_R2.0.9.S03.E01_006
    rm -f TEDFTP_Schema_20180704_TED_publication.zip TED_publication_R2.0.9.S03.E01_006-20180608.zip
    rm -f TED_publication_R2.0.9.S03.E01_006/{common_prod.xsd,DEVCO.xsd,MOVE.xsd,TED_EXPORT.xsd,xlink.xsd}

    cd ..

### Create sample XML files

Create sample XML files for each form schema:

    rake sample

Or for specific form schema:

    rake sample FILES=01,02,03,14,20

### Map XML elements and attributes to text labels

Generate files for mapping forms' XPath values to label keys:

    rake label:xpath label:ignore

You're now ready to map label keys to XPath values. As setup, if you have two monitors, open a form's template PDF and English PDF side-by-side in one monitor, to make it easy to see the text label of each label key in context. In a text editor, open `ignore.csv`, `enumerations.csv`, `attributes.csv` and a form's sample XML and XPath CSV.

Fill in each form's XPath CSV:

1. Fill in the `label-key` column with label keys from the template PDF, referring to the English PDF and sample XML to verify the correspondence. Each instance of a label key should occur at most once in the CSV.
1. If the label key is immediately preceded by an index (like `II.1.1`), fill in the `index` column with the index.
1. If an XPath value has no corresponding label key in the PDF, fill in the `comment` column with a rationale.

Add rows to `ignore.csv` as needed:

1. If a label key has no corresponding editable field in the PDF, it may not have a corresponding XPath value. If so, add it to `ignore.csv`.
1. If the label key is immediately preceded by an index (like `II.1.1`), fill in the `index` column with the index.

Fill in `enumerations.csv`:

* In some cases, a form has label keys for each enumeration value. If so, fill in `xpath` with the XPath to the attribute, `value` with the enumeration value, and `label-key` with the label key.

Once completed, run `rake missing` to see which XML elements and attributes have no key, and which keys have no XML element or attribute and aren't in `ignore.csv`.

You can now generate a table for each form, displaying, for each element and attribute, the index within the PDF ("I.1"), the label (in any language) and the XPath, to which you can then add guidance for OCDS.

## Design

The code focuses on XML schema and label keys.

* Label keys are expected to change less frequently than labels.
* No XML samples describe the same range of possibilities described by XML schema.
* XML schema are expected to change more frequently than the XML they describe (e.g. reordering and refactoring).

## Exploration

Early on, I transformed the XML schema to CSV summaries, both to understand the structure of the schema through implementation, and to get an easy overview of the XML schema, which were otherwise quite referential.

Transform all form schema into CSV files:

    rake legacy:common legacy:forms

Or transform a specific directory and specific form schema:

    rake legacy:common legacy:forms DIRECTORY=source/TED_publication_R2.0.9.S03.E01_006 FILES=01,02,03,14,20

## Reference

* [Overview of XSD files](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview)
* [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure)

`text_ft_multi_lines` is an element that ["can contain several <P> tags"](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.5.Textfieldsizelimitation). In `common_2014.xsd`, it's defined as a sequence of `P` elements (unbounded), and `P` is defined as [mixed content](https://www.w3.org/TR/xmlschema-0/#mixedContent), with optional `FT` elements (unbounded), which are either [superscripts or subscripts](http://simap.ted.europa.eu/documents/10184/45895/esenders_faq_en.pdf/14f88d13-7d5d-4f8f-b6a0-9bcbe7aa9351#page=16). The schema uses `P` elements instead of `CRLF` text.

The following types have annotations for each enumeration:

* `t_currency_tedschema`
* `t_legal-basis_tedschema`

The following forms restrict the following types (non-exhaustive):

    F01_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]
    F02_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]

    F01_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT"]
    F03_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]
    F20_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]

    F02_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F03_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F20_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
