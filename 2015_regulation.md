# 2015 Regulation

## Usage

### Install dependencies

```
bundle
pip install -r requirements.txt
```

### Download prerequisites

    fish scripts/download.fish

### Create sample XML files

Create sample XML files for each form's schema:

    bundle exec rake sample

For release R2.0.8:

    bundle exec rake sample RELEASE=R2.0.8 FILES=16,17,18,19

See the comments in `sample.rake` to understand why tools like Oxygen are insufficient.

### Map XML elements and attributes to text labels

Create or update files for mapping forms' XPath values to label keys:

    bundle exec rake label:xpath

For release R2.0.8:

    bundle exec rake label:xpath RELEASE=R2.0.8 FILES=F16,F17,F18,F19

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

    # Excludes F16,F17,F18,F19.
    bundle exec rake label:missing FILES=F01,F02,F03,F04,F05,F06,F07,F08,F12,F13,F14,F15,F20,F21,F22,F23,F24,F25

### Copy guidance across forms

Many XPath's are common across forms. Copy guidance across forms:

    bundle exec rake label:copy SOURCE=F01
    bundle exec rake label:copy SOURCE=F02 FILES=F03,F05,F06,F07,F12,F13,F15,F21,F22,F23,F24,F25
    bundle exec rake label:copy SOURCE=F03 FILES=F06,F13,F15,F21,F22,F23,F25
    bundle exec rake label:copy SOURCE=F04 FILES=F05,F06,F07,F08,F12,F13,F15,F21,F22,F23,F24,F25
    bundle exec rake label:copy SOURCE=F06 FILES=F22
    bundle exec rake label:copy SOURCE=F07 FILES=F22
    bundle exec rake label:copy SOURCE=F12 FILES=F13
    bundle exec rake label:copy SOURCE=F21 FILES=F22,F23,F25
    bundle exec rake label:copy SOURCE=F23 FILES=F25
    bundle exec rake label:copy SOURCE=F24 FILES=F25

Then, revert undesired changes to:

* `F12_2014.csv`: `/LEFTI/PARTICULAR_PROFESSION`
* `F20_2014.csv`: `/OBJECT_CONTRACT/OBJECT_DESCR`
* `F23_2014.csv`: `/AWARD_CONTRACT`
* `F25_2014.csv`: `/AWARD_CONTRACT`

Copy guidance across forms with a greater number of uncertain changes:

    bundle exec rake label:copy SOURCE=F03 FILES=F20
    bundle exec rake label:copy SOURCE=F06 FILES=F20
    bundle exec rake label:copy SOURCE=F15 FILES=F23,F25

Then, review and, if appropriate, revert undesired changes to:

* `F20_2014.csv`:
  * `/OBJECT_CONTRACT/OBJECT_DESCR`
  * `/PROCEDURE/NOTICE_NUMBER_OJ`
  * `/AWARD_CONTRACT/CONTRACT_NO`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL/@CURRENCY`
* `F23_2014.csv`
  * `/AWARD_CONTRACT`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS`
* `F25_2014.csv`:
  * `/AWARD_CONTRACT`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT`
  * `/AWARD_CONTRACT/AWARDED_CONTRACT/CONTRACTORS`

### Check the CSV files

Many label keys are ignored across forms. To pre-populate across forms, run:

    bundle exec rake label:ignore

Note: Running `label:ignore` at a later time might reintroduce values in the `numbers` column that were manually removed.

Report any CSV quoting errors:

    bundle exec rake label:validate

Report any inconsistencies in mappings across forms. Some differences are appropriate; for example, some forms use check boxes instead of radio buttons, and some change the tense of the label from present to past. The XPaths mentioned above are expected to be inconsistent.

    bundle exec rake label:consistent

### Map the T01 and T02 forms

T01 and T02 are particular: both use the same schema (`MOVE.xsd`), and neither has a PDF template. The most efficient process is to:

* Reverse-engineer the label keys from the English PDF:

        bundle exec rake label:reverse

* Create an XPath CSV for `MOVE.xsd`:

        bundle exec rake label:xpath FILES=MOVE

* Copy guidance:

        bundle exec rake label:copy SOURCE=F01 FILES=MOVE
        bundle exec rake label:copy SOURCE=F03 FILES=MOVE
        bundle exec rake label:copy SOURCE=F14 FILES=MOVE

* Manually update some `label-key` values
* Pre-populate `ignore.csv` (see above caveat):

        bundle exec rake label:ignore FILES=MOVE FORM=T01
        bundle exec rake label:ignore FILES=MOVE FORM=T02

* Check for missing items:

        bundle exec rake label:missing FILES=MOVE FORM=T01
        bundle exec rake label:missing FILES=MOVE FORM=T02

* Review and, if appropriate, revert undesired changes to `/AWARD_CONTRACT` and `/AWARD_CONTRACT/AWARDED_CONTRACT/VALUES/VAL_TOTAL/@CURRENCY` in `MOVE.csv`.

### Build tables for OCDS guidance

Re-order rows to more closely match the PDF templates:

    fish scripts/move.fish

You can now generate a table for each form, displaying, for each element and attribute, the index within the PDF ("I.1"), the label (in any language) and the XPath, to which you can then add guidance for OCDS.

    for i in 01 02 03 04 05 06 07 08 12 13 14 15 20 21 22 23 24 25; rake table LANGUAGE=EN FILES=F$i > path/to/european-union/docs/forms/F$i.md; end
    for i in 01 02; rake table LANGUAGE=EN FILES=MOVE FORM=T$i > path/to/european-union/docs/forms/T$i.md; end

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

## Reference

### TED schema

In addition to the resources linked under prerequisites above, there is a [TED eSenders wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender), which contains:

* [XML Schema 2.0.9](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/3.3.+XML+Schema+2.0.9), in particular: [Overview](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/3.3.+XML+Schema+2.0.9#id-3.3.XMLSchema2.0.9-Overview.) and [Form structure](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/3.3.+XML+Schema+2.0.9#id-3.3.XMLSchema2.0.9-2.2.Formstructure)
* [Standard forms guidance](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/2.4.1.+Standard+forms+guidance), in particular: Field explanations ([public link](https://ec.europa.eu/docsroom/documents/24191/attachments/1/translations/en/renditions/native)) (PDF)
* [Instructions for the use of 14](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/2.4.2.+Instructions+for+the+use+of+F14) ([public link](http://simap.ted.europa.eu/documents/10184/166101/Instructions+for+the+use+of+F14_EN.pdf/909e4b38-1871-49a1-a206-7a5976a2d262)) (PDF)
* [FAQ](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/11.+FAQ) (click "Expand all")
* [Contacts](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/7.+Contacts)

The "Tree browser" on the ["Pages" page](https://webgate.ec.europa.eu/fpfis/wikis/collector/pages.action?key=TEDeSender) serves as a table of contents.

The [reception schema files](https://op.europa.eu/en/web/eu-vocabularies/e-procurement/tedschemas) include Excel validation rules, which also maps XML elements to human-readable text. **This is the most useful summary of the TED schema.** It is described in the [wiki](https://webgate.ec.europa.eu/fpfis/wikis/display/TEDeSender/3.3.+XML+Schema+2.0.9#id-3.3.XMLSchema2.0.9-5.Descriptionofvalidationrules). They also contains an XLST validation tool.

The [FTP server](ftp://eu-tenders:eu-tenders-123@ted.europa.eu) has a [document](ftp://eu-tenders:eu-tenders-123@ted.europa.eu/Resources/TED-XML_general_description_v2.0_20160219.pdf) (PDF) describing the structure of the FTP server, of individual resources and of notices (without much detail on the FORM section), and information on mapping forms labels and XML elements in R2.0.9 (essentially asking the user do the work of this repository 🤯). I haven't figured out how to use the "HTML/PDF rendering web service" it describes.

#### Schema notes

The following types have annotations for each enumeration:

* `t_currency_tedschema`
* `t_legal-basis_tedschema`

`text_ft_multi_lines` is an element that ["can contain several `<P>` tags"](https://webgate.ec.europa.eu/fpfis/wikis/pages/viewpage.action?spaceKey=TEDeSender&title=XML+Schema+2.0.9#XMLSchema2.0.9-2.5.Textfieldsizelimitation). In `common_2014.xsd`, it's defined as a sequence of `P` elements (unbounded), and `P` is defined as [mixed content](https://www.w3.org/TR/xmlschema-0/#mixedContent), with optional `FT` elements (unbounded), which are either [superscripts or subscripts](http://simap.ted.europa.eu/documents/10184/45895/esenders_faq_en.pdf/14f88d13-7d5d-4f8f-b6a0-9bcbe7aa9351#page=16). The schema uses `P` elements instead of `CRLF` text.

#### Reception, internal and publication schema

TED has reception, internal and publication schema. We use the publication schema. To find major differences:

* Replace `R2\.0\.9\.S0[A-Z\d.]+` with `R2.0.9.S0X` (no semantic change)
* Replace `Last update ?:[\d/ ]+` with `Last update :` (no semantic change)
* Run `diff -ruw <directoryA> <directoryB>`

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

By March 2017, Data Unlocked (Simon Whitehouse) authored a [draft mapping](https://drive.google.com/drive/folders/0B5qzJROt-jZ0Vm9UNHNMVE5JOHM) to OCDS from a spreadsheet that was among the materials in a [consultation on eForms](http://ec.europa.eu/growth/content/targeted-consultation-eforms-next-generation-public-procurement-standard-forms-0_en) ending January 30, 2017. An [updated version](https://docs.google.com/spreadsheets/d/1W6eJiYEHkuQVSNzHtUdFbsYse0aTfZXtU-XjLRVVSyg/edit) of the [original spreadsheet](https://docs.google.com/spreadsheets/d/11uDaomY1mK-_h9FPW9D1o7D8_z_vR6Z4nxWgqbHc39g/edit?usp=sharing) accompanying the consultation was shared with OCP. This mapping was [reviewed](https://drive.google.com/drive/folders/0B7agx7YesblKS2NxQTdJMEw5Q2s). Some next steps and use cases were discussed at a [workshop in Kiev](https://docs.google.com/document/d/1gBOVMsiSVholLfS4s41bX4FOjLqIustdtKGYtqoAndU/edit#heading=h.v6nxv59w4s43). However, both spreadsheets were abandoned in the latest consultation. [Draft extensions](https://github.com/open-contracting-archive/trade) were authored; these were all reviewed as part of this project, and are mentioned in the `comment` columns of mapping files where relevant.

Other work from 2015 includes [ocds-ted](https://github.com/timgdavies/ocds-ted) by Tim Davies, which has draft extensions and links to a [very early draft mapping](https://docs.google.com/spreadsheets/d/13AMbfIhjg9j-7IsKWJ3-tdnVXWzHdqnARtHpzMownoU/edit#gid=1338855215) based on Publication Office's: XML labels mapping spreadsheet, forms labels spreadsheet, and a subset of possible XPaths in XML data. There is earlier, similar work in a [gist](https://gist.github.com/timgdavies/cc0e571aef7224d5e546), in particular this [documentation](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-1-ocds-to-ted-mapping-documentation-md) and [script](https://gist.github.com/timgdavies/cc0e571aef7224d5e546#file-tedxml-py). These efforts are largely superseded by the later work by Data Unlocked. A copy of the TED schema can be browsed in this repository:

    git clone git@github.com:timgdavies/ocds-ted.git
    jekyll serve
    open http://127.0.0.1:4000/ocds-ted/docs/
