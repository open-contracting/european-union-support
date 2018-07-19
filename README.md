# TED XSD parser

Download prerequisites:

    mkdir -p source
    cd source

    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/XML schema 2.0.9/Forms_Templates_R209S01.zip'
    unzip Forms_Templates_R209S01.zip
    rm -f Forms_Templates_R209S01.zip
    rm -rf __MACOSX

    curl -O 'ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/TEDFTP_Schema_20180704_TED_publication.zip'
    unzip TEDFTP_Schema_20180704_TED_publication.zip TED_publication_R2.0.9.S03.E01_006-20180608.zip
    rm -f TEDFTP_Schema_20180704_TED_publication.zip
    unzip TED_publication_R2.0.9.S03.E01_006-20180608.zip -d TED_publication_R2.0.9.S03.E01_006
    rm -f TED_publication_R2.0.9.S03.E01_006-20180608.zip
    rm -f TED_publication_R2.0.9.S03.E01_006/{common_prod.xsd,DEVCO.xsd,MOVE.xsd,TED_EXPORT.xsd,xlink.xsd}

    cd ..

Transform all forms into CSV files:

    rake common forms

Transform a specific directory and specific forms into CSV files:

    rake common forms DIRECTORY=source/TED_publication_R2 FORMS=01,02,03,14,20

Annotate the CSV files:

    rake label

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
