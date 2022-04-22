# Common operations

To avoid repetition in the guidance, we refer and link to the following common operations.

## Create a release

1. Set [`id`](https://standard.open-contracting.org/latest/en/schema/identifiers/#release-id) to the notice number (`/*/cbc:ID`).
1. Set `initiationType` to 'tender'.
1. Set `ocid` as described below.

The notice's `ocid` will either be a new `ocid`, or the same `ocid` as the previous publication concerning this procedure. The notice's `ocid` will be a new `ocid` if one of the following is true:

* The notice is the first publication concerning the procedure.
* The previous publication is a prior information notice or a periodic indicative notice  (PIN) that has multiple `/*/cac:ProcurementProjectLot` elements, it potentially lead to the launch of several procedures, each with its own `ocid`.
* The notice is a contract award notice (CAN) for an award within a framework agreement or dynamic purchasing system.

If none is true, then set the notice's `ocid` to be the same as the previous publication's `ocid`. Otherwise, set the notice's [`ocid`](https://standard.open-contracting.org/latest/en/schema/identifiers/#contracting-process-identifier-ocid) by prepending your [OCID prefix](https://standard.open-contracting.org/latest/en/guidance/build/#register-an-ocid-prefix) to a unique identifier of your choice (e.g. a [version 4 UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier) or a suitable system-internal identifier).

If the notice is a contract award notice for an award within a framework agreement or dynamic purchasing system, you must also add a `RelatedProcess` object to the `relatedProcesses` array, set its `.id` to '1', add 'framework' to its `.relationship` array, set its `.scheme` to 'ocid', and set its `.identifier` to the `ocid` of the procedure that set up the framework agreement or dynamic purchasing system.

## Reference a previous publication

If the *Previous publication concerning this procedure* is neither a prior information notice nor a periodic indicative notice (PIN), or if the PIN has a single `/*/cac:ProcurementProjectLot` (*Object*) element, then discard `/*/cbc:ID`. In this case, the *previous publication concerning this procedure* is the OCDS release with the same `ocid` as this release and with the nearest earlier `date` to this release.

Otherwise, if the *Previous publication concerning this procedure* is a prior information notice or periodic indicative notice that has multiple `/*/cac:ProcurementProjectLot` (*Object*) elements, add a `RelatedProcess` object to the `relatedProcesses` array, set its `.id` to '1', add 'planning' to its `.relationship` array, set its `.scheme` to 'eu-oj' (or to a scheme of your choice if outside the EU), and map `/*/cbc:ID` to `.identifier`.

## Add a party

Add an `Organization` object to the `parties` array, and set its `.id` (string). **A party's `.id` needs to be consistent across all notices.** It is recommended to implement a register of organization identifiers to assign consistent identifiers. For more information, [see the OCDS documentation](https://standard.open-contracting.org/latest/en/schema/identifiers/#organization-ids).

## Add a bids statistic

Add a `BidsStatistic` object to the `bids.statistics` array, and set its `.id` (string) sequentially across all notices for this procedure. For example, if a first F03 notice for a given procedure has nine bids statistics, it uses `id`'s '1' through '9'. A second F03 notice for the same procedure then uses `id`'s '10' and up, etc.

## Convert a date to ISO format

[OCDS dates](https://standard.open-contracting.org/latest/en/schema/reference/#date) must be formatted according to ISO 8601 and include a time component.

If a time component is missing from a date, use 'T23:59:59Z' for end dates and 'T00:00:00Z' for other dates.

If a timezone component is present in the date (e.g. '+02:00'), preserve it. Otherwise, use the UTC timezone indicate 'Z'.

The final value would be '2020-10-21T23:59:59Z' or '2020-10-21T00:00:00Z'.

## Lot identifiers

eForms relies in the structure of the XML document to imply the related lot. For a given XML element, retrieving the corresponding lot identifier (if any) can done with the following Xpath:

```text
ancestor::cac:ProcurementProjectLot/cac:ID
```

## Groups of lots

 ## Procedure type

The possible values for BT-105 Procedure type ([official code list](https://op.europa.eu/en/web/eu-vocabularies/concept-scheme/-/resource?uri=http://publications.europa.eu/resource/authority/procurement-procedure-type#)) and the corresponding guidance in OCDS:

| Procedure type code | OCDS guidance `|
|---------------|-------------------|
| Competitive dialog (`comp-dial`)              | Set `tender.procurementMethod` to 'selective', and set `tender.procurementMethodDetails` to 'Competitive dialogue' |
| Competitive tendering (`comp-tend`)           |                   |
| Innovation partnership (`innovation`)         | Set `tender.procurementMethod` to 'selective', and set `tender.procurementMethodDetails` to 'Innovation partnership' |
| Negotiated with prior publication of a call for competition / competitive with negotiation (`neg-w-call`)    | Set `tender.procurementMethod` to 'selective', and set `tender.procurementMethodDetails` to 'Negotiated with prior publication of a call for competition / competitive with negotiation'                   |
| Negotiated without prior call for competition (`neg-wo-call`)   |                   |
| Open (`open`)          |  Set `tender.procurementMethod` to 'open', and set `tender.procurementMethodDetails` to 'Open procedure' | 
| Other multiple stage procedure (`oth-mult`)   |                   |
| Other single stage procedure (`oth-single`)   |  |
| Restricted (`restricted`)                     | Set `tender.procurementMethod` to 'selective', and set `tender.procurementMethodDetails` to 'Restricted procedure' |

## Get a translation

No guidance yet.