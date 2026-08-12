# Experiment Workflow

## Repository Sequence

Use the existing command and artifact conventions:

```text
prepare -> retrieve -> evaluate -> verify-evidence -> export/analyze
```

The standard data tables are `documents.parquet`, `pages.parquet`, `nodes.parquet`, and `queries.parquet`. Retrieval runs should retain config, run metadata, predictions, metrics, errors, and summary output.

## Baselines And Controls

For page/region research, keep these concepts distinct:

- `BM25-page`: lexical page baseline;
- `Dense-page`: semantic page baseline, with the actual backend recorded;
- `Hybrid-page`: fusion control;
- `Page -> Region`: predicted-page two-stage control;
- `Global-Region`: tests whether page filtering helps;
- `Oracle-Page -> Region`: upper bound for separating page recall error from region ranking error;
- `single-node vs evidence-set`: tests whether joint evidence selection adds value beyond returning more nodes.

When a method combines candidate sources or heuristics, add ablations for the meaningful components, such as slot coverage, structured numeric scan, unit consistency, cover anchors, or redundancy penalty.

## Evaluation

At minimum report page recall, MRR/nDCG where applicable, and region hit. For evidence-centered work also report required-slot coverage, sufficient/partial/insufficient/conflict counts, citation mismatch, and answer support when generation exists. Break down results by question type (numeric, comparison, cover, risk/text) and inspect failures, not only aggregate scores.

## Data Leakage Guard

Retrieval and ranking may use the question and permitted metadata such as answer unit. They must not use the gold answer value, gold node IDs, or gold evidence pages unless the config is explicitly oracle/analysis-only. Keep oracle results separate from ordinary method claims.

## Claim Standard

Every result claim should identify:

```text
dataset/version + query count + retrieval scope + config + model/backend + metric@k + run date
```

Do not combine numbers copied from different dated notes into one “latest” table without checking their run artifacts. If artifacts are ignored or absent, describe the numbers as documented historical results and avoid claiming local reproduction.

## Implementation Acceptance

For a code change, require the smallest relevant test or smoke run. A complete evidence-set feature should expose selected node IDs/text/location, coverage slots, sufficiency status/score, and selection reasons. A complete trustworthy-generation feature must additionally show generated claims, supporting evidence links, citation validation, and a deterministic insufficient/conflict/refusal decision path.
