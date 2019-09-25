# Support scripts for TED mapping

## Usage

### Download prerequisites

Using the fish shell:

    mkdir -p source
    cd source

    # Get the mapping from label keys to text labels.
    # https://publications.europa.eu/en/web/eu-vocabularies/e-procurement/tedschemas
    curl -o Forms_Labels_R209S01.zip https://publications.europa.eu/documents/3938058/5358176/Forms_Labels_R209.zip/6e5fa3bc-62bf-0b66-0ae2-c1979d445355
    unzip Forms_Labels_R209S01.zip
    in2csv Forms_labels_R209.xlsx > 'Forms labels R2.09.csv'
    rm -f Forms_Labels_R209S01.zip Forms_labels_R209.xlsx

    # Get the template PDFs containing label keys for R2.0.9.
    curl -o Archive.zip 'https://publications.europa.eu/documents/3938058/5358176/Archive.zip/ce7ceb02-94b0-04e8-8b9f-7fb4acf1ccdb'
    unzip Archive.zip -d TED_forms_templates_R2.0.9
    rm -rf Archive.zip TED_forms_templates_R2.0.9/__MACOSX

    # Get the template PDFs containing label keys for R2.0.8.
    mkdir -p TED_forms_templates_R2.0.8
    curl -o TED_forms_templates_R2.08.pdf https://publications.europa.eu/documents/3938058/5358176/2011_09-04_LB_2.pdf/be1e3e03-30e7-34ac-465e-39da20dfc154
    set form 01 02 03 04 05 06 07 08 09 10 11 12 13 15 16 17 18 19
    set l 7 18 26 38 49 58 65 68 72 77 82 88 93 105 111 123 131 138
    set f 1
    for i in (seq 1 18); pdfseparate -f $f -l $l[$i] TED_forms_templates_R2.08.pdf t-%d.pdf; pdfunite t-*.pdf TED_forms_templates_R2.0.8/F{$form[$i]}.pdf; rm -f t-*.pdf; set f (echo "$l[$i] + 1" | bc); end

    # Get the English PDFs.
    # http://simap.ted.europa.eu/standard-forms-for-public-procurement
    mkdir -p English
    for i in 01 02 03 04 05 06 07 08 12 13 14 15 20 21 22 23 24 25; curl -o English/EN_F$i.pdf http://simap.ted.europa.eu/documents/10184/99173/EN_F{$i}.pdf; end
    for i in 16 17 18; curl -o English/EN_F$i.pdf https://simap.ted.europa.eu/documents/10184/49059/sf_{$i}_en.pdf; end
    curl -o English/EN_F19.pdf https://simap.ted.europa.eu/documents/10184/49059/sf_019_en.pdf/179d1c44-05d3-4f35-b25e-bb8d619d9733
    for i in 01 02; curl -o English/EN_T$i.pdf https://simap.ted.europa.eu/documents/10184/49059/t{$i}_en.pdf; end

    # Get the XML schema for R2.0.9.
    curl -o TEDFTP_Schema_20181030_TED_publication.zip https://publications.europa.eu/documents/3938058/5358455/latest_publication_R2.0.9.S03.E01_007-20181030.zip/d3adafe5-cb3a-4ac5-5dca-f4aea09b99a8
    unzip TEDFTP_Schema_20181030_TED_publication.zip TED_publication_R2.0.9.S03.E01_007-20181030.zip
    unzip TED_publication_R2.0.9.S03.E01_007-20181030.zip -d TED_publication_R2.0.9.S03.E01_007
    rm -f TEDFTP_Schema_20181030_TED_publication.zip TED_publication_R2.0.9.S03.E01_007-20181030.zip
    rm -f TED_publication_R2.0.9.S03.E01_007/{common_prod.xsd,DEVCO.xsd,TED_EXPORT.xsd,xlink.xsd}

    # Get the XML schema for R2.0.8.
    curl -o TEDFTP_Schema_20180515_TED_publication.zip https://publications.europa.eu/documents/3938058/5358176/latest_publication_R2.0.8.S04.E01_003-20180515.zip/4aa79bef-bee7-ff35-b7bd-9365bad7f488
    unzip TEDFTP_Schema_20180515_TED_publication.zip TED_publication_R2.0.8.S04.E01_003-20180515.zip
    unzip TED_publication_R2.0.8.S04.E01_003-20180515.zip -d TED_publication_R2.0.8.S04.E01_003
    rm -f TEDFTP_Schema_20180515_TED_publication.zip TED_publication_R2.0.8.S04.E01_003-20180515.zip
    rm -f TED_publication_R2.0.8.S04.E01_003/{common_prod.xsd,EEIG.xsd,OTH_NOT.xsd,TED_EXPORT.xd,TED_EXPORT.xsd,xlink.xsd}

    cd ..

### Create sample XML files

Create sample XML files for each form's schema:

    rake sample

Or for specific schema:

    rake sample FILES=F01,F02,F03,F14,F20

Or for a specific release:

    rake sample RELEASE=R2.0.8 FILES=F16,F17,F18,F19

See the comments in `sample.rake` to understand why tools like Oxygen are insufficient.

### Map XML elements and attributes to text labels

Create or update files for mapping forms' XPath values to label keys:

    rake label:xpath

For release R2.0.8:

    rake label:xpath RELEASE=R2.0.8 FILES=F16,F17,F18,F19

You're now ready to map label keys to XPath values. As setup, if you have two monitors, open a form's template PDF and English PDF side-by-side in one monitor, to make it easy to see the text label of each label key in context. In a text editor, open `ignore.csv`, `enumerations.csv` and a form's sample XML and XPath CSV.

Fill in each form's XPath CSV:

1. Fill in the `label-key` column with label keys from the template PDF, referring to the English PDF and sample XML to verify the correspondence. Each *instance* of a label key should occur at most once in the CSV.
1. If the label key is immediately preceded by an index (like `II.1.1`), fill in the `index` column with the index.
1. If an XPath value has no corresponding label key in the PDF, fill in the `comment` column with a rationale, unless it has no label because it's new (`LEGAL_BASIS`) implied (`ADDRESS_CONTRACTING_BODY_ADDITIONAL`) or an index (`@ITEM`), or because its values are labelled instead (`NOTICE`).

Add rows to `omit.csv` as needed. This will omit the label from the guidance:

1. If, like the legal basis (`directive_201424`), it appears after the form name (`notice_pin`, etc.) and before any form elements and has no corresponding editable field in the PDF, then fill in `label-key` with the label key and `numbers` with a pipe-separated list (`|`) of form numbers. Follow the order in the PDF templates.
1. If the label key corresponds to an editable field in the PDF that has a superscript 7 ("mandatory information not to be published"), add it as above.

Add rows to `ignore.csv` as needed. This will include the label without a mapping in the guidance:

1. If a label key has no corresponding editable field in the PDF, it may not have a corresponding XPath value. If so, unless it appears in the footer or endnotes or is a section number (`section_1`, etc.) or form name (`notice_pin`, etc.), fill in `index` with the index as above, `label-key` with the label key, and `numbers` with a pipe-separated list (`|`) of form numbers. Follow the order in the PDF templates.

Fill in `enumerations.csv`:

1. In some cases, a form has label keys for each enumeration value. If so, fill in `xpath` with the XPath to the attribute, `value` with the enumeration value, `label-key` with the label key, and `numbers` with a pipe-separated list (`|`) of form numbers. Follow the order in the PDF templates.

Once completed, run `rake label:missing` to see which XML elements and attributes have no key, and which keys have no XML element or attribute and aren't in `ignore.csv`:

    rake label:missing FILES=F01,F02,F03

Many XPath's are common across forms. To copy guidance across forms, run:

    rake label:copy SOURCE=F01
    rake label:copy SOURCE=F02 FILES=F03,F05,F06,F07,F12,F13,F15,F21,F22,F23,F24,F25
    rake label:copy SOURCE=F03 FILES=F06,F13,F15,F21,F22,F23,F25
    rake label:copy SOURCE=F04 FILES=F05,F06,F07,F08,F12,F13,F15,F21,F22,F23,F24,F25
    rake label:copy SOURCE=F06 FILES=F22
    rake label:copy SOURCE=F07 FILES=F22
    rake label:copy SOURCE=F12 FILES=F13
    rake label:copy SOURCE=F21 FILES=F22,F23,F25
    rake label:copy SOURCE=F23 FILES=F25
    rake label:copy SOURCE=F24 FILES=F25
    rake label:copy SOURCE=F03 FILES=MOVE
    rake label:copy SOURCE=F14 FILES=MOVE

Review the copied guidance after running:

    rake label:copy SOURCE=F03 FILES=F20
    rake label:copy SOURCE=F06 FILES=F20
    rake label:copy SOURCE=F15 FILES=F23,F25

Many label keys are ignored across forms. To pre-populate across forms, run:

    rake label:ignore

Report any CSV quoting errors:

    rake label:validate

Report any inconsistencies in mappings across forms. Note that some forms use check boxes instead of radio buttons, and some change tense from present to past.

    rake label:consistent

T01 and T02 are particular: both use the same schema (`MOVE.xsd`), and neither has a PDF template. The most efficient process is to: reverse-engineer the label keys from the English PDF; create an XPath CSV for `MOVE.xsd`; copy guidance; manually update some `label-key` values; pre-populate `ignore.csv`; then check for missing items:

    rake label:reverse
    rake label:xpath FILES=MOVE
    rake label:copy SOURCE=F01 FILES=MOVE
    rake label:copy SOURCE=F03 FILES=MOVE
    rake label:copy SOURCE=F14 FILES=MOVE
    rake label:ignore FILES=MOVE FORM=T01
    rake label:ignore FILES=MOVE FORM=T02
    rake label:missing FILES=MOVE FORM=T01
    rake label:missing FILES=MOVE FORM=T02

### Build tables for OCDS guidance

Before running this task, [move](move.fish) the following in XPath CSVs to more closely match the order in the PDF templates.

You can now generate a table for each form, displaying, for each element and attribute, the index within the PDF ("I.1"), the label (in any language) and the XPath, to which you can then add guidance for OCDS.

    for i in 01 02 03 04 05 06 07 08 12 13 14 15 20 21 22 23 24 25; rake table LANGUAGE=EN FILES=F$i > path/to/european-union/docs/F$i.md; end
    for i in 01 02; rake table LANGUAGE=EN FILES=MOVE FORM=T$i > path/to/european-union/docs/T$i.md; end

### Find fields for which to write extensions

Generate a release schema with all extensions applied, except the PPP extension (which removes fields):

    python scripts/patched_release_schema.py > scripts/release-schema-patched.json

Generate a CSV file with all fields from the extended schema, including a column for the extension name:

    ocdskit mapping-sheet --infer-required --extension-field extension scripts/release-schema-patched.json > scripts/mapping-sheet.csv

Print a list of fields for which there are no extensions:

    python scripts/mapped_ocds_fields.py

## Design

* Label keys are expected to change less frequently than labels. The code therefore focuses on label keys.
* XML schema are expected to change more frequently than the XML they describe (e.g. reordering and refactoring). However, no XML samples provided by the Publication Office or generated from XSD by tools like Oxygen describe the same range of possibilities as described by XML schema. The code therefore generates its own eccentric samples.

## Exploration

Early on, I transformed the XML schema to CSV summaries, both to understand the structure of the schema through implementation, and to get an easy overview of the XML schema, which were otherwise quite referential.

Transform all form schema into CSV files:

    rake legacy:common legacy:forms

Or transform a specific directory and specific form schema:

    rake legacy:common legacy:forms DIRECTORY=source/TED_publication_R2.0.9.S03.E01_006 FILES=F01,F02,F03,F14,F20

I also attempted to map elements and attributes in the XML to labels on the forms using the Publication Office's [form label mappings](https://publications.europa.eu/en/web/eu-vocabularies/e-procurement/tedschemas), but the file covers only forms 1-6, doesn't cover all XML elements, doesn't use full XPaths, isn't machine-interpretable, etc.; manual interpretation would require at least the same effort as the above process. The Excel validation rules in the reception schema files map elements and attributes to descriptions, but these are not the same as the labels on the forms.

## Reference

### TED schema

In addition to the resources linked under prerequisites above, there is a [TED eSenders wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender), which contains:

* [XML Schema 2.0.9](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9), in particular: [Overview](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview) and [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure)
* [Standard forms guidance](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Standard+forms+guidance), in particular: Field explanations ([public link](https://ec.europa.eu/docsroom/documents/24191/attachments/1/translations/en/renditions/native)) (PDF)
* [Instructions for the use of 14](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Instructions+for+the+use+of+F14) ([public link](http://simap.ted.europa.eu/documents/10184/166101/Instructions+for+the+use+of+F14_EN.pdf/909e4b38-1871-49a1-a206-7a5976a2d262)) (PDF)
* [FAQ](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/FAQ) (click "Expand all")
* [Contacts](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Contacts)

The "Tree browser" on the ["Pages" page](https://webgate.ec.europa.eu/fpfis/wikis/collector/pages.action?key=TEDeSender) serves as a table of contents.

The [reception schema files](https://publications.europa.eu/en/web/eu-vocabularies/e-procurement/tedschemas) include Excel validation rules, which also maps XML elements to human-readable text. **This is the most useful summary of the TED schema.** It is described in the [wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/XML+Schema+2.0.9#XMLSchema2.0.9-5.Descriptionofvalidationrules). They also contains an XLST validation tool.

The FTP server (ftp://eu-tenders:eu-tenders-123@ted.europa.eu) has a document (ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/TED-XML_general_description_v2%200_20160219.pdf) (PDF) describing the structure of the FTP server, of individual resources and of notices (without much detail on the FORM section), and information on mapping forms labels and XML elements in R2.0.9 (essentially asking the user do the work of this repository 🤯). I haven't figured out how to use the "HTML/PDF rendering web service" it describes.

#### Schema notes

The following types have annotations for each enumeration:

* `t_currency_tedschema`
* `t_legal-basis_tedschema`

`text_ft_multi_lines` is an element that ["can contain several `<P>` tags"](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.5.Textfieldsizelimitation). In `common_2014.xsd`, it's defined as a sequence of `P` elements (unbounded), and `P` is defined as [mixed content](https://www.w3.org/TR/xmlschema-0/#mixedContent), with optional `FT` elements (unbounded), which are either [superscripts or subscripts](http://simap.ted.europa.eu/documents/10184/45895/esenders_faq_en.pdf/14f88d13-7d5d-4f8f-b6a0-9bcbe7aa9351#page=16). The schema uses `P` elements instead of `CRLF` text.

#### Reception, internal and publication schema

TED has reception, internal and publication schema. We use the publication schema. To find major differences:

* Replace `R2\.0\.9\.S0[A-Z\d.]+` with `R2.0.9.S0X` (no semantic change)
* Replace `Last update ?:[\d/ ]+` with `Last update :` (no semantic change)
* Run `diff -ruw <folderA> <folderB>`

The publication schema sometimes has `minOccurs="0"` where the reception and internal schema don't. To ignore that:

* Replace ` minOccurs="0"` with nothing

##### Internal schema

The remaining differences are in `F08_2014.xsd` (comment), `F14_2014.xsd` (choice), `F20_2014.xsd` (`PUBLICATION` attribute), `common_2014.xsd` (import `xlink.xsd`), `nuts_codes.xsd` (irrelevant) and `common_prod.xsd`.

`INTERNAL_OJS.xsd` is only in the internal schema. `TED_EXPORT.xsd` and `xlink.xsd` are only in the publication schema.

##### Reception schema

The remaining differences are in `F14_2014.xsd` (choice), `F20_2014.xsd` (`PUBLICATION` attribute), `common_2014.xsd` (`maxLength` values, `TRANSLATION` enumeration) and `nuts_codes.xsd` (irrelevant).

`TED_ESENDERS.xsd` is only in the reception schema. `common_prod.xsd`, `TED_EXPORT.xsd` and `xlink.xsd` are only in the publication schema.

### Prior work

#### By others

* In DIGIWHIST, TED data is imported, processed, cleaned, and exported as OCDS. There is no usable mapping from import format to export format, due to the many processing and cleaning steps in between.
* In OpenOpps, a subset of TED data is imported, processed, cleaned, and exported as OCDS. There is no complete mapping from TED to OCDS.
* The [OpenTED spreadsheet](https://docs.google.com/spreadsheets/d/1ps3Mgi-rJTaEbpTpm_2oMr8yAinmya74S_QeV4J2y_o/edit#gid=1455892276) is incomplete and may be out-of-date.

#### By OCP

By March 2017, Data Unlocked (Simon Whitehouse) authored a [draft mapping](https://drive.google.com/drive/folders/0B5qzJROt-jZ0Vm9UNHNMVE5JOHM) to OCDS from a spreadsheet that was among the materials in a [consultation on eForms](http://ec.europa.eu/growth/content/targeted-consultation-eforms-next-generation-public-procurement-standard-forms-0_en) ending January 30, 2017. An [updated version](https://docs.google.com/spreadsheets/d/1W6eJiYEHkuQVSNzHtUdFbsYse0aTfZXtU-XjLRVVSyg/edit) of the [original spreadsheet](https://docs.google.com/spreadsheets/d/11uDaomY1mK-_h9FPW9D1o7D8_z_vR6Z4nxWgqbHc39g/edit?usp=sharing) accompanying the consultation was shared with OCP. This mapping was [reviewed](https://drive.google.com/drive/folders/0B7agx7YesblKS2NxQTdJMEw5Q2s). Some next steps and use cases were discussed at a [workshop in Kiev](https://docs.google.com/document/d/1gBOVMsiSVholLfS4s41bX4FOjLqIustdtKGYtqoAndU/edit#heading=h.v6nxv59w4s43). However, both spreadsheets were abandoned in the latest consultation. [Draft extensions](https://github.com/open-contracting-archive/trade) where authored; these were all reviewed as part of this project, and are mentioned in the `comment` columns of mapping files where relevant.

Other work from 2015 includes [ocds-ted](https://github.com/timgdavies/ocds-ted) by Tim Davies, which has draft extensions and links to a [very early draft mapping](https://docs.google.com/spreadsheets/d/13AMbfIhjg9j-7IsKWJ3-tdnVXWzHdqnARtHpzMownoU/edit#gid=1338855215) based on Publication Office's: XML labels mapping spreadsheet, forms labels spreadsheet, and a subset of possible XPaths in XML data. There is earlier, similar work in a [gist](https://gist.github.com/timgdavies/cc0e571aef7224d5e546), in particular this [documentation](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-1-ocds-to-ted-mapping-documentation-md) and [script](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-tedxml-py). These efforts are largely superseded by the later work by Data Unlocked. A copy of the TED schema can be browsed in this repository:

    git clone git@github.com:timgdavies/ocds-ted.git
    jekyll serve
    open http://127.0.0.1:4000/ocds-ted/docs/
