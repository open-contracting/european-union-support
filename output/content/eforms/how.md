# How it works

## Mapping steps

### Populate `.name` in organization references

For each `OrganizationReference` object in your data, get the `Organization` in `parties` whose `.id` is equal to the `.id` of the organization reference and set the organization reference's `.name` to the `.name` of the organization. The following fields are `OrganizationReference` objects:

* `<list of fields>`

### Withhold the publication of information

Some information required by eForms may remain non-public ("unpublished") for a defined period, as described in [withheld publication of information](https://docs.ted.europa.eu/eforms/1.3.2/schema/all-in-one.html#withheldPublicationOfInformationSection). For fields with an associated `efac:FieldsPrivacy` element, wait until the date in `/efbc:PublicationDate` and then:

* [Create a release](operations.md#create-a-release) and add 'previouslyWithheldInformation' to its `.tag` array.
* Perform the mapping for the fields and publish the release.

## What's not included

[Notice types](https://github.com/OP-TED/eForms-SDK/blob/develop/notice-types/notice-types.json) X01 and X02 relate to events outside the lifecycle of a contracting process.

* X01 - Notice containing information relevant to Formation or Completion of the liquidation of a [EEIG](https://en.wikipedia.org/wiki/European_economic_interest_grouping)
* X02 - Notice containing information about Registration, Deletion, Transfer-registration or Transfer-deletion of a European Company or European Cooperative Society

Furthermore, thee following notice types are listed in the regulation's annex but are not described by the eForms SDK.

- E1 - Prior market consultation notice
- E5 - Contract completion notice type

Therefore, fields that are only used in these notice types are omitted from the guidance. They are:

For X01 and/or X02:

- BT-500-Business
- BT-501-Business-European
- BT-501-Business-National
- BT-502-Business
- BT-503-Business
- BT-505-Business
- BT-506-Business
- BT-507-Business
- BT-510(a)-Business
- BT-510(b)-Business
- BT-510(c)-Business
- BT-512-Business
- BT-513-Business
- BT-514-Business
- BT-739-Business
- OPP-100-Business
- OPP-105-Business
- OPP-110-Business
- OPP-111-Business
- OPP-112-Business
- OPP-113-Business-European
- OPP-120-Business
- OPP-121-Business
- OPP-122-Business
- OPP-123-Business
- OPP-130-Business
- OPP-131-Business

For E1:

- BT-800(d)-Lot
- BT-800(t)-Lot

For E5:

- BT-779-Tender
- BT-780-Tender
- BT-781-Lot
- BT-782-Tender
- BT-783-Review
- BT-784-Review
- BT-785-Review
- BT-786-Review
- BT-787-Review
- BT-788-Review
- BT-789-Review
- BT-790-Review
- BT-791-Review
- BT-792-Review
- BT-793-Review
- BT-794-Review
- BT-795-Review
- BT-796-Review
- BT-797-Review
- BT-798-Review
- BT-799-ReviewBody
- OPT-091-ReviewReq
- OPT-092-ReviewBody
- OPT-092-ReviewReq
- OPT-301-ReviewBody
- OPT-301-ReviewReq
