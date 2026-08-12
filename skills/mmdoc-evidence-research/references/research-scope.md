# Research Scope

## Thesis Question

The project studies how to make multimodal long-document RAG evidence-centered, locatable, citable, verifiable, and reproducible. Long-document QA is the validation task; the contribution is the evidence retrieval and trust pipeline, not a new foundation model.

## Contribution Ladder

1. **Evidence representation**: pages, paragraphs, headings, table blocks, table rows, figures, and other document elements become evidence nodes with document/page identity, type, text, location, reading order, hierarchy, source, and confidence.
2. **Minimum sufficient evidence retrieval**: combine page candidates, region candidates, structural signals, question-slot coverage, unit/value consistency, and redundancy control to select a small evidence set rather than only the most similar chunk.
3. **Trust verification**: check pre-generation sufficiency, post-generation claim support, citation consistency, conflicts, and refusal for unanswerable or insufficient cases.

## Key Terms

- **Page retrieval**: coarse candidate page recall.
- **Region localization**: paragraph/table/row/figure evidence-node retrieval.
- **Evidence set**: one or more nodes selected to jointly cover the answer requirements.
- **Sufficiency**: whether the selected set covers required evidence slots.
- **Numeric quadruple**: metric, year, unit, and value.
- **Citation mismatch**: answer or citation points to a page/node that does not support the claimed content.
- **Oracle page -> region**: an upper-bound analysis using gold pages; never present it as a deployable retriever.

## Current Known Boundary

The repository has implemented text/PDF parsing, paragraph/table/table-row nodes, BM25/TF-IDF/dense fallback and optional sentence-transformer retrieval, page/region baselines, evidence-set heuristics, metrics, and rule-based sufficiency checks. A schema field or planned config is not proof that image indexing, visual retrieval, LLM generation, post-generation support verification, conflict handling, or refusal is implemented.

## Out Of Scope Unless Explicitly Justified

- training a new multimodal foundation model;
- making OCR, table recognition, or chart extraction the main contribution;
- presenting a generic PDF chatbot as the research system;
- claiming visual/multimodal gains without image data and a visual baseline;
- comparing only whether an external LLM can answer a single question;
- adding unrelated product features that do not test an evidence hypothesis.
