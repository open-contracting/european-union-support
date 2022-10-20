mkdir -p source
cd source

# https://simap.ted.europa.eu/en_GB/web/simap/eforms

# 2022-04-13 "This mapping in Excel" updates "eForms documentation v. 1.1 and XPATHs provisional release v. 1.0 (25/05/2020)".
curl -sS -o TED-XML-to-eForms-mapping-OP-public-20220404.xlsx https://simap.ted.europa.eu/documents/10184/320101/TED-XML-to-eForms-mapping-OP-public-20220404/a0fed751-76cb-491b-957d-96985fdc82a4

# https://ec.europa.eu/growth/single-market/public-procurement/digital-procurement/eforms_en

curl -sS -o CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx https://ec.europa.eu/docsroom/documents/43488/attachments/1/translations/en/renditions/native

# https://github.com/OP-TED/eForms-SDK/blob/main/fields/fields.json

curl -sS -O https://raw.githubusercontent.com/OP-TED/eForms-SDK/1.2.1/fields/fields.json
