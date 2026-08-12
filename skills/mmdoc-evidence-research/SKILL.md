---
name: mmdoc-evidence-research
description: Keep work on this repository aligned with the thesis topic "multi-granularity evidence retrieval and trustworthy generation for multimodal long documents". Use when analyzing the opening report, reading project notes, changing retrieval/evidence/verification code, designing experiments, drafting paper content, or deciding the next research task. Prevent scope drift into generic PDF chat, unrelated RAG features, foundation-model training, or unsupported claims about visual retrieval and trustworthy generation.
---

# MMDoc Evidence Research

This skill is the project-specific research compass. It does not replace engineering judgment or invent completed results. It keeps every explanation, code change, experiment, and paper claim tied to the evidence-retrieval research question.

## When To Use

Use this skill for requests involving:

- the opening report, thesis, small paper, research questions, innovation points, or experiment plans;
- `src/mmdocrag`, `configs/experiments`, `tests`, or project `docs`;
- PDF long-document parsing, evidence nodes, page/region retrieval, evidence sets, citations, sufficiency, support, conflicts, or refusal;
- deciding whether a proposed feature belongs in the current research scope.

If the request is unrelated to this project, do not force this skill onto it.

## Operating Rules

1. Read the relevant project files before proposing conclusions. Prefer the current code and dated experiment records over old plans.
2. Separate three states explicitly: implemented in source, recorded as a reproducible result, and planned only.
3. Never call text-only retrieval “multimodal.” Claim visual or multimodal capability only when page/region images, visual representations, or a visual experiment actually exist.
4. Keep the central chain visible:

   `document parsing -> evidence representation -> page retrieval -> region localization -> evidence-set selection -> generation -> verification/refusal`

5. Treat `Evidence Set Region` and evidence sufficiency as the current research core. Baselines are controls, not the contribution by themselves.
6. Do not leak gold answers, gold node IDs, or gold evidence pages into a retriever unless the experiment is explicitly labeled oracle, upper-bound, or analysis-only.
7. For any claimed improvement, identify the dataset version, config, metric, run/result artifact, and comparison baseline. Do not mix numbers from different dated notes.
8. Prefer the smallest experiment that distinguishes competing explanations. Include an ablation or error analysis when a method combines multiple heuristics.
9. Keep changes scoped to the request. Do not add a generic chatbot, unrelated UI, foundation-model pretraining, OCR research, or a large platform refactor without a direct thesis justification.
10. When a requested feature is not implemented, say so plainly and describe the missing acceptance test rather than implying that a schema or placeholder is a working subsystem.

## Workflow

For a research or implementation request:

1. Identify the relevant research question (RQ1 representation, RQ2 page-region coordination, RQ3 multimodal/layout fusion, or RQ4 support/refusal).
2. Inspect the closest code, config, tests, and dated notes. Read `references/research-scope.md` for terminology and boundary decisions; read `references/experiment-workflow.md` for execution and evidence standards.
3. State the current baseline and the smallest change that tests the hypothesis.
4. Implement using existing schemas, CLI, configuration, and output conventions. Add focused tests proportional to risk.
5. Run the narrowest relevant validation available. If the project environment or data is unavailable, report that limitation and do not fabricate results.
6. Summarize: what changed, what is now demonstrated, what remains unimplemented, and which experiment or paper section it supports.

## Response Discipline

Use project terminology consistently: `evidence node`, `evidence set`, `page -> region`, `sufficiency`, `support`, `citation mismatch`, `conflict`, and `unanswerable`. When explaining to the researcher, distinguish a skill from a model: a skill is an instruction bundle that guides the agent; it does not itself improve retrieval quality, train a model, or execute experiments.

## References

- [research-scope.md](references/research-scope.md): thesis purpose, contributions, terminology, and out-of-scope work.
- [experiment-workflow.md](references/experiment-workflow.md): repository workflow, experiment controls, validation, and claim standards.
