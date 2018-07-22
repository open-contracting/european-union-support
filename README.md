# TED XSD parser

Download prerequisites (fish shell):

    mkdir -p source
    cd source

    # http://publications.europa.eu/mdr/eprocurement/ted/index.html
    curl -O http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/publication/XML_Labels_Mapping_R209.zip
    unzip XML_Labels_Mapping_R209.zip
    rm -f XML_Labels_Mapping_R209.zip
    in2csv --sheet Labels_EN_FR_DE 'XML Labels mapping R2.09.xlsx' > 'XML Labels mapping R2.09.csv'

    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/XML schema 2.0.9/Forms_Templates_R209S01.zip'
    unzip Forms_Templates_R209S01.zip
    rm -f Forms_Templates_R209S01.zip
    rm -rf __MACOSX
    for i in source/2015-11-03a_TED_forms_templates/*.pdf; pdftotext -layout $i; end

    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/TEDFTP_Schema_20180704_TED_publication.zip'
    unzip TEDFTP_Schema_20180704_TED_publication.zip TED_publication_R2.0.9.S03.E01_006-20180608.zip
    rm -f TEDFTP_Schema_20180704_TED_publication.zip
    unzip TED_publication_R2.0.9.S03.E01_006-20180608.zip -d TED_publication_R2.0.9.S03.E01_006
    rm -f TED_publication_R2.0.9.S03.E01_006-20180608.zip
    rm -f TED_publication_R2.0.9.S03.E01_006/{common_prod.xsd,DEVCO.xsd,MOVE.xsd,TED_EXPORT.xsd,xlink.xsd}

    cd ..

Transform all form schema into CSV files:

    rake common forms

Or transform a specific directory and specific form schema:

    rake common forms DIRECTORY=source/TED_publication_R2.0.9.S03.E01_006 FORMS=01,02,03,14,20

Create sample XML files for each form schema:

    rake sample

Or for specific form schema:

    rake sample FORMS=01,02,03,14,20

Generate files for mapping forms' XPath's to label keys:

    rake label:xpath label:ignore

1. In a multi-monitor setup, open a form's template PDF, English PDF, and XPath CSV.
1. Fill in the `key` column with keys from the template PDF, cross-referencing with the English PDF to determine the correspondence.
1. If a key has no corresponding editable field in the PDF, it may not have a corresponding XML element. If so, add it to `ignore.csv`.
1. Once completed, run `rake missing` to see which XML elements have no key, and which keys have no XML element and aren' in `ignore.csv`.

You can now generate a table for each form, displaying, for each element, the index within the PDF ("I.1"), the label (in any language) and the XPath, to which you can then add guidance for OCDS.

## Reference

* [Overview of XSD files](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview)
* [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure)

`text_ft_multi_lines` is an element that ["can contain several <P> tags"](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.5.Textfieldsizelimitation). In `common_2014.xsd`, it's defined as a sequence of `P` elements (unbounded), and `P` is defined as [mixed content](https://www.w3.org/TR/xmlschema-0/#mixedContent), with optional `FT` elements (unbounded), which are either [superscripts or subscripts](http://simap.ted.europa.eu/documents/10184/45895/esenders_faq_en.pdf/14f88d13-7d5d-4f8f-b6a0-9bcbe7aa9351#page=16). The schema uses `P` elements instead of `CRLF` text.

The following types have annotations for each enumeration:

* `t_currency_tedschema`
* `t_legal-basis_tedschema`

The following forms restrict the following types:

    F01_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]
    F02_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]

    F01_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT"]
    F03_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]
    F20_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]

    F02_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F03_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F20_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
