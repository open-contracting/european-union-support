mkdir -p source
cd source

# https://op.europa.eu/en/web/eu-vocabularies/e-procurement/tedschemas

# Get the mapping from label keys to text labels.
curl -sS -o Forms_labels_R209.xlsx https://op.europa.eu/documents/3938058/9351229/Forms_Labels_R209.xlsx/ff1f70e3-7aad-1648-d564-559c49ee70c4
in2csv Forms_labels_R209.xlsx > 'Forms labels R2.09.csv'
rm -f Forms_labels_R209.xlsx

# Get the template PDFs containing label keys for R2.0.9.
curl -sS -o Archive.zip https://op.europa.eu/documents/3938058/5358176/Archive.zip/ce7ceb02-94b0-04e8-8b9f-7fb4acf1ccdb
unzip -q Archive.zip -d TED_forms_templates_R2.0.9
rm -rf Archive.zip TED_forms_templates_R2.0.9/__MACOSX

# Get the template PDFs containing label keys for R2.0.8.
mkdir -p TED_forms_templates_R2.0.8
curl -sS -o TED_forms_templates_R2.08.pdf https://op.europa.eu/documents/3938058/5358176/2011_09-04_LB_2.pdf/be1e3e03-30e7-34ac-465e-39da20dfc154
set form 01 02 03 04 05 06 07 08 09 10 11 12 13 15 16 17 18 19
# First page.
set f 1
# Last page.
set l 7 18 26 38 49 58 65 68 72 77 82 88 93 105 111 123 131 138
for i in (seq 1 18)
    pdfseparate -f $f -l $l[$i] TED_forms_templates_R2.08.pdf t-%d.pdf
    pdfunite t-*.pdf TED_forms_templates_R2.0.8/F{$form[$i]}.pdf
    rm -f t-*.pdf
    set f (echo "$l[$i] + 1" | bc)
end
rm -f TED_forms_templates_R2.08.pdf

# http://simap.ted.europa.eu/standard-forms-for-public-procurement

# Get the English PDFs.
mkdir -p English
for i in 01 02 03 04 05 06 07 08 12 13 14 15 20 21 22 23 24 25
    curl -sS -o English/EN_F$i.pdf https://ted.europa.eu/documents/d/ted/en_f{$i}
end
for i in 16 17 18
    curl -sS -o English/EN_F$i.pdf https://simap.ted.europa.eu/documents/10184/49059/sf_0{$i}_en.pdf
end
curl -sS -o English/EN_F19.pdf https://simap.ted.europa.eu/documents/10184/49059/sf_019_en.pdf/179d1c44-05d3-4f35-b25e-bb8d619d9733
for i in 01 02
    curl -sS -o English/EN_T$i.pdf https://simap.ted.europa.eu/documents/10184/49059/t{$i}_en.pdf
end

# Get the XML schema for R2.0.9.
curl -sS -o TED_publication_R2.0.9.zip https://op.europa.eu/documents/3938058/9351229/TED_publication_R2.0.9.S05.E01_001-20210730.zip/0fc38de3-a2ae-a239-0885-4017d12f8a22
unzip -q TED_publication_R2.0.9.zip -d TED_publication_R2.0.9
rm -f TED_publication_R2.0.9.zip TED_publication_R2.0.9/{common_prod.xsd,TED_EXPORT.xsd,xlink.xsd}

# Get the XML schema for R2.0.8.
curl -sS -o TED_publication_R2.0.8.zip https://op.europa.eu/documents/3938058/8012911/TED_publication_R2.0.8.S05.E01_002-20201027.zip/78530eed-1879-d8c1-df16-e4bcf8d54ea0
unzip -q TED_publication_R2.0.8.zip -d TED_publication_R2.0.8
rm -f TED_publication_R2.0.8.zip TED_publication_R2.0.8/{common_prod.xsd,EEIG.xsd,OTH_NOT.xsd,TED_EXPORT.xd,TED_EXPORT.xsd,xlink.xsd}
