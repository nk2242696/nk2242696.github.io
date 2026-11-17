# Data Modeling: Small Choices, Billion-Row Consequences

A dashboard says sales were $300. Finance says $100. Both queries run in milliseconds. The problem? Someone repeated a $100 order total across three order lines.

**A careful data model saves twice: fewer bytes now, fewer rebuilds later.**

Data modeling decides what we store and how it relates. Dimensional modeling organizes that data around business events and their context. Here is a practical way to get both right.

## 1. Before columns, finish one sentence

Start with the business question: what are we selling, to whom, and through which channels? Then declare the **grain**:

> One row represents one booked order line, uniquely identified by source system, order ID, and line number.

Grain is the exact meaning of a row, not just a list of keys. "One row per customer and product" is incomplete: the same customer can buy the same product twice. [1]

In our $100 order, line amounts are $20, $30, and $50. Those belong at line grain. The order total belongs in an order-level fact, or needs an explicit allocation rule.

Sales lines, return events, and daily stock balances have different grains. Keep them separate. Joining sales lines directly to multiple return events can multiply rows and inflate revenue; aggregate each side to the intended common grain first.

Keep the lowest useful detail. You can summarize order lines into daily totals; you cannot reconstruct the lines from those totals.

## 2. Separate measurements from context

**Facts** record measurements. **Dimensions** describe who, what, when, and where.

| Table | What belongs here |
|---|---|
| `fact_sales_line` | Grain identifiers, dimension keys, quantity, net amount |
| `dim_product` | Product key, source product ID, name, brand, category |
| `dim_customer` | Customer key, source customer ID, segment, region |
| `dim_date` | Date key, actual date, month, fiscal period, holiday flags |
| `dim_channel` | Channel key and name: web, app, store |

Use warehouse-generated **surrogate keys** to identify dimension rows; retain source IDs for tracing records. Names change and are poor join keys.

Reuse shared definitions of customer, product, and date across sales and returns. These **conformed dimensions** stop teams inventing incompatible versions of "region." [2]

Also define how measures aggregate. Revenue in one reporting currency can be summed. Stock balances cannot be summed across days. Calculate a conversion rate from total conversions divided by total visits, not an unweighted average of daily percentages.

## 3. Choose a shape, not a religion

Normalization reduces repeated data. Denormalization deliberately repeats some data to simplify reads. Star and snowflake schemas apply these choices to analytics:

| Shape | Useful when | Trade-off |
|---|---|---|
| Normalized relational model | Transactional applications need consistent inserts and updates | Analysis may cross many tables |
| Star schema | BI needs facts joined to straightforward dimensions | Product brand and category repeat within the product dimension |
| Snowflake schema | Dimension hierarchies need separate, reusable tables: product to category to department | More joins and navigation |
| Wide denormalized table | A stable report or export benefits from one ready-to-query table | Repeated attributes and harder historical corrections |

A star is already a compromise: separate facts from dimensions, but usually flatten descriptive hierarchies inside each dimension. "Star versus denormalized" is not a clean either/or. [2]

For general BI, start with a star. Build selective wide outputs when measurements justify them. Fewer joins do not automatically mean less total work.

## 4. A byte becomes a billion bytes

Suppose a fact table stores a small channel code. In **SQL Server**, the uncompressed value widths are: [3]

| Type | Range | Bytes per value |
|---|---|---|
| `TINYINT` | 0 to 255 | 1 |
| `INT` | -2,147,483,648 to 2,147,483,647 | 4 |

Replacing `INT` with `TINYINT` saves **3 bytes per row**. At a billion rows, that is **3 GB** of raw value payload; at ten billion, **30 GB**, roughly 28 GiB, for one column.

That is 75% less *for those values*, not 75% off the table or cloud bill. Compression, row overhead, indexes, replicas, and the engine's physical representation change the result. Columnar encoding can make small-valued `INT` columns compact already.

Choose the smallest type that safely fits the **future domain**, including reserved unknown values. SQL Server's `TINYINT` cannot hold `-1`; other engines have different ranges or no `TINYINT`.

Two more guardrails: use appropriately sized `DECIMAL(p,s)` for money, not floating point; keep postal codes as strings because leading zeros matter. Matching join-key types avoids unnecessary conversions.

## 5. A date key is not a date

For November 24, 2026, compare these SQL Server representations, excluding surrounding overhead: [3][4]

| Representation | Value payload |
|---|---|
| `CHAR(8)` containing `'20261124'` | 8 bytes |
| `INT` containing `20261124` | 4 bytes |
| Native `DATE` | 3 bytes |

An integer date key can reduce index and join-key footprint versus text, without string collation work. Converting strings during every join adds avoidable work; parse and validate once when loading.

But **integer is not universally faster**, and it is not smaller than every native date type. Plans, indexes, compression, and data layout matter.

A useful dimensional design keeps `date_key = 20261124` alongside a real `calendar_date` in `dim_date`. Join matching integer keys; use calendar attributes for reporting: [5]

```sql
SELECT d.calendar_date, SUM(f.net_amount) AS net_sales
FROM fact_sales_line AS f
JOIN dim_date AS d ON f.date_key = d.date_key
WHERE d.calendar_date >= CAST('2026-11-01' AS DATE)
  AND d.calendar_date <  CAST('2026-12-01' AS DATE)
GROUP BY d.calendar_date;
```

Do not subtract encoded keys to count days: `20261201 - 20261130 = 71`, not one. An integer also accepts `20260230`; a native date rejects it.

Use native `DATE` for ordinary calendar operations, and retain event timestamps where time matters. Define the reporting timezone before deriving the business date.

## 6. Decide whether history should change

A customer moves from Pune to Delhi in December. Should November's sales move too?

- **Type 1:** overwrite the dimension attribute. Useful for corrections or a deliberate current-state view.
- **Type 2:** create a new dimension row with a new surrogate key and validity interval. Historical facts retain the version valid at their event time. [2]

Joining a fact to a Type 2 dimension by customer ID alone can match both versions. Join its stored version key instead; resolve late-arriving facts using event time.

History is a business decision, not an accidental side effect of an update statement. Without a policy, yesterday's perfectly correct dashboard can change today.

## 7. Make the model prove itself

Before the first dashboard, test these promises:

- The declared grain is unique.
- Dimension join keys are unique; facts have no orphan keys. Represent unknown members explicitly.
- Intended many-to-one joins preserve row counts and totals.
- Reloading a batch does not duplicate facts.
- Currency, timezone, null handling, and metric definitions are documented.

Changing a column later is easy. Changing its meaning after twenty dashboards depend on it is not.

The best model is not the one with the most tables or the fewest joins. It is the one that makes **wrong answers harder to produce**.

## Sources

1. [Kimball Group: grain and fact tables](https://www.kimballgroup.com/2008/11/fact-tables/).
2. [Microsoft: star schemas, dimensions, and historical versions](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema).
3. [SQL Server: integer ranges and storage](https://learn.microsoft.com/en-us/sql/t-sql/data-types/int-bigint-smallint-and-tinyint-transact-sql?view=sql-server-ver17).
4. [SQL Server: native date storage](https://learn.microsoft.com/en-us/sql/t-sql/data-types/date-transact-sql?view=sql-server-ver17).
5. [Kimball Group: calendar date dimensions and integer keys](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/calendar-date-dimension/).
