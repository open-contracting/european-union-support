# Support scripts for TED mapping

## Usage

### Download prerequisites

Using the fish shell:

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
    for i in 01 02 03 04 05 06 07 08 12 13 14 15 20 21 22 23 24 25; curl -o English/EN_F$i.pdf http://simap.ted.europa.eu/documents/10184/99173/EN_F$i.pdf; end

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

See the comments in `sample.rake` to understand why tools like Oxygen are insufficient.

### Map XML elements and attributes to text labels

Create or update files for mapping forms' XPath values to label keys:

    rake label:xpath

You're now ready to map label keys to XPath values. As setup, if you have two monitors, open a form's template PDF and English PDF side-by-side in one monitor, to make it easy to see the text label of each label key in context. In a text editor, open `ignore.csv`, `enumerations.csv` and a form's sample XML and XPath CSV.

Fill in each form's XPath CSV:

1. Fill in the `label-key` column with label keys from the template PDF, referring to the English PDF and sample XML to verify the correspondence. Each *instance* of a label key should occur at most once in the CSV.
1. If the label key is immediately preceded by an index (like `II.1.1`), fill in the `index` column with the index.
1. If an XPath value has no corresponding label key in the PDF, fill in the `comment` column with a rationale, unless it has no label because it's new (`LEGAL_BASIS`) implied (`ADDRESS_CONTRACTING_BODY_ADDITIONAL`) or an index (`@ITEM`), or because its values are labelled instead (`NOTICE`).

Add rows to `ignore.csv` as needed:

1. If a label key has no corresponding editable field in the PDF, it may not have a corresponding XPath value. If so, unless it appears in the footer or endnotes or is a section number (`section_1`, etc.), form name (`notice_pin`, etc.) or legal basis (`directive_201424`), fill in `index` with the index as above, `label-key` with the label key, and `numbers` with a pipe-separated list (`|`) of form numbers. Follow the order in the PDF templates.

Fill in `enumerations.csv`:

1. In some cases, a form has label keys for each enumeration value. If so, fill in `xpath` with the XPath to the attribute, `value` with the enumeration value, `label-key` with the label key, and `numbers` with a pipe-separated list (`|`) of form numbers. Follow the order in the PDF templates.

Once completed, run `rake missing` to see which XML elements and attributes have no key, and which keys have no XML element or attribute and aren't in `ignore.csv`:

    rake missing FILES=01,02,03

Many XPath's are common across forms. To copy guidance across forms, run:

    rake label:copy SOURCE=01
    rake label:copy SOURCE=02 FILES=03,05
    rake label:copy SOURCE=03 FILES=06,13,20,25
    rake label:copy SOURCE=04 FILES=05,06,07,21,22,23
    rake label:copy SOURCE=06 FILES=20,22
    rake label:copy SOURCE=07 FILES=22
    rake label:copy SOURCE=21 FILES=22

Report any CSV quoting errors:

    rake label:validate

Report any incoherences in mappings across forms. Note that some forms use check boxes instead of radio buttons, and some change tense from present to past.

    rake label:coherence

### Build tables for OCDS guidance

Before running this task, move the following in XPath CSVs to more closely match the order in the PDF templates:

* F03 only: `LOT_DIVISION` after `SHORT_DESCR`, `NO_AWARDED_TO_GROUP` after `AWARDED_TO_GROUP`, `PT_AWARD_CONTRACT_WITHOUT_CALL` children after all
* `NUTS` after `TOWN`, `NO_LOT_DIVISION` after `LOT_DIVISION`

You can now generate a table for each form, displaying, for each element and attribute, the index within the PDF ("I.1"), the label (in any language) and the XPath, to which you can then add guidance for OCDS.

    for i in 01 02 03; rake table LANGUAGE=EN FILES=$i > path/to/F$i.md; end

## Design

* Label keys are expected to change less frequently than labels. The code therefore focuses on label keys.
* XML schema are expected to change more frequently than the XML they describe (e.g. reordering and refactoring). However, no XML samples provided by the Publication Office or generated from XSD by tools like Oxygen describe the same range of possibilities as described by XML schema. The code therefore generates its own eccentric samples.

## Exploration

Early on, I transformed the XML schema to CSV summaries, both to understand the structure of the schema through implementation, and to get an easy overview of the XML schema, which were otherwise quite referential.

Transform all form schema into CSV files:

    rake legacy:common legacy:forms

Or transform a specific directory and specific form schema:

    rake legacy:common legacy:forms DIRECTORY=source/TED_publication_R2.0.9.S03.E01_006 FILES=01,02,03,14,20

I also attempted to map elements and attributes in the XML to labels on the forms using the Publication Office's [form label mappings](http://publications.europa.eu/mdr/eprocurement/ted/index.html), but the file covers only forms 1-6, doesn't cover all XML elements, doesn't use full XPaths, isn't machine-interpretable, etc.; manual interpretation would require at least the same effort as the above process. The [forms validation rules](http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/reception/latest/Forms_validation_rules_R2.0.9.S03_006-20180608.xlsx) map elements and attributes to descriptions, but these are not the same as the labels on the forms.

## Reference

### Laws

* [Directive 2014/24](https://eur-lex.europa.eu/eli/dir/2014/24/oj) on public procurement
* [Commission Implementing Regulation 2015/1986](https://eur-lex.europa.eu/eli/reg_impl/2015/1986/oj) establishing standard forms for the publication of notices in the field of public procurement
* [Council Directive 89/665](https://eur-lex.europa.eu/eli/dir/1989/665/oj) on the coordination of the laws, regulations and administrative provisions relating to the application of review procedures to the award of public supply and public works contracts

### TED schema

In addition to the resources linked under prerequisites above, there is a [TED eSenders wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender), which contains:

* [XML Schema 2.0.9](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9), in particular: [Overview](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.1.Overview) and [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.2.Formstructure)
* [Standard forms guidance](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Standard+forms+guidance), with **"Field explanations"** that can inform field definitions in OCDS extensions (PDF)
* [Instructions for the use of 14](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Instructions+for+the+use+of+F14) (PDF)
* [FAQ](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/FAQ) (click "Expand all")
* [Contacts](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/Contacts)

The "Tree browser" on the ["Pages" page](https://webgate.ec.europa.eu/fpfis/wikis/collector/pages.action?key=TEDeSender) serves as a table of contents.

In the [Metadata Registry](http://publications.europa.eu/mdr/eprocurement/ted/), the [reception schema](http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/reception/latest/) contains [validation rules](http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/reception/latest/Forms_validation_rules_R2.0.9.S03_006-20180608.xlsx) (Excel), which also maps XML elements to human-readable text. **This is the most useful summary of the TED schema.** It is described in the [wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/XML+Schema+2.0.9#XMLSchema2.0.9-5.Descriptionofvalidationrules). It also contains a [validation tool](http://publications.europa.eu/mdr/resource/eprocurement/ted/R2.0.9/reception/latest/XSLT_validation_tool_R2.0.9.S03_022-20180608.zip) with XSLT rules.

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

By March 2017, Data Unlocked (Simon Whitehouse) authored a [draft mapping](https://drive.google.com/drive/folders/0B5qzJROt-jZ0Vm9UNHNMVE5JOHM) to OCDS from a spreadsheet that was among the materials in a [consultation on eForms](http://ec.europa.eu/growth/content/targeted-consultation-eforms-next-generation-public-procurement-standard-forms-0_en) ending January 30, 2017. An [updated version](https://docs.google.com/spreadsheets/d/1W6eJiYEHkuQVSNzHtUdFbsYse0aTfZXtU-XjLRVVSyg/edit) of the [original spreadsheet](https://docs.google.com/spreadsheets/d/11uDaomY1mK-_h9FPW9D1o7D8_z_vR6Z4nxWgqbHc39g/edit?usp=sharing) accompanying the consultation was shared with OCP. This mapping was [reviewed](https://drive.google.com/drive/folders/0B7agx7YesblKS2NxQTdJMEw5Q2s). Some next steps and use cases were discussed at a [workshop in Kiev](https://docs.google.com/document/d/1gBOVMsiSVholLfS4s41bX4FOjLqIustdtKGYtqoAndU/edit#heading=h.v6nxv59w4s43). However, both spreadsheets were abandoned in the latest consultation.

Other work from 2015 includes [ocds-ted](https://github.com/timgdavies/ocds-ted) by Tim Davies, which has draft extensions and links to a [very early draft mapping](https://docs.google.com/spreadsheets/d/13AMbfIhjg9j-7IsKWJ3-tdnVXWzHdqnARtHpzMownoU/edit#gid=1338855215) based on Publication Office's: XML labels mapping spreadsheet, forms labels spreadsheet, and a subset of possible XPaths in XML data. There is earlier, similar work in a [gist](https://gist.github.com/timgdavies/cc0e571aef7224d5e546), in particular this [documentation](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-1-ocds-to-ted-mapping-documentation-md) and [script](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-tedxml-py). These efforts are largely superseded by the later work by Data Unlocked. A copy of the TED schema can be browsed in this repository:

    git clone git@github.com:timgdavies/ocds-ted.git
    jekyll serve
    open http://127.0.0.1:4000/ocds-ted/docs/
