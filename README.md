# TED XSD parser

Download prerequisites:

    mkdir -p source

    cd source

    # http://publications.europa.eu/mdr/eprocurement/ted/index.html
    curl -O http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/publication/XML_Labels_Mapping_R209.zip
    unzip XML_Labels_Mapping_R209.zip
    rm -f XML_Labels_Mapping_R209.zip

    # http://publications.europa.eu/mdr/eprocurement/ted/specific_versions_new.html#div2
    curl -O http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/publication/beta/TED_publication_R2.0.9.S03.E01_004-20180322.zip
    unzip TED_publication_R2.0.9.S03.E01_004-20180322.zip -d TED_publication_R2
    rm -f TED_publication_R2.0.9.S03.E01_004-20180322.zip

    rm -f TED_publication_R2/{common_prod.xsd,DEVCO.xsd,MOVE.xsd,TED_EXPORT.xsd,xlink.xsd}

    cd ..

Prepare prerequisites:

    in2csv --write-sheets - "source/XML Labels mapping R2.09.xlsx" > /dev/null

Process all directories and all forms:

    rake common forms

Process one directory and given forms:

    rake common forms DIRECTORY=source/TED_publication_R2 FORMS=01,02,03,14,20

## Reference

* [Overview of XSD files](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview)
* [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure)

`text_ft_multi_lines` is an element that ["can contain several <P> tags"](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.5.Textfieldsizelimitation). In `common_2014.xsd`, it's defined as a sequence of `P` elements (unbounded), and `P` is defined as [mixed content](https://www.w3.org/TR/xmlschema-0/#mixedContent), with optional `FT` elements (unbounded), which are either [superscripts or subscripts](http://simap.ted.europa.eu/documents/10184/45895/esenders_faq_en.pdf/14f88d13-7d5d-4f8f-b6a0-9bcbe7aa9351#page=16). The schema uses `P` elements instead of `CRLF` text.

The following forms restrict the following types:

    F01_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]
    F02_2014: lefti: removes ["RULES_CRITERIA", "RESERVED_ORGANISATIONS_SERVICE_MISSION", "DEPOSIT_GUARANTEE_REQUIRED", "MAIN_FINANCING_CONDITION", "LEGAL_FORM", "QUALIFICATION", "CONDITIONS", "METHODS", "CRITERIA_SELECTION"]

    F01_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT"]
    F03_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]
    F20_2014: complement_info: removes ["RECURRENT_PROCUREMENT", "ESTIMATED_TIMING", "NO_RECURRENT_PROCUREMENT", "EORDERING", "EINVOICING", "EPAYMENT"]

    F02_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F03_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
    F20_2014: complement_info: changes ADDRESS_REVIEW_BODY: [["-", "minOccurs", "0"]]
