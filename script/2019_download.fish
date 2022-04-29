mkdir -p source
cd source

# https://simap.ted.europa.eu/en_GB/web/simap/eforms

# 2020-05-20 version 1.0 of the mapping between eForms components and Business Terms
curl -sS -o 'XPATHs provisional release v. 1.0.docx' https://simap.ted.europa.eu/documents/10184/320101/XPATHs+provisional+release+v.+1.0/f74a6976-af15-4bad-99ce-9a4684b60dba

# 2022-04-13 mapping in Excel
curl -sS -o TED-XML-to-eForms-mapping-OP-public-20220404.xlsx https://simap.ted.europa.eu/documents/10184/320101/TED-XML-to-eForms-mapping-OP-public-20220404/a0fed751-76cb-491b-957d-96985fdc82a4

# https://ec.europa.eu/growth/single-market/public-procurement/digital-procurement/eforms_en

curl -sS -o CELEX_32019R1780_EN_ANNEX_TABLE2_Extended.xlsx https://ec.europa.eu/docsroom/documents/43488/attachments/1/translations/en/renditions/native
