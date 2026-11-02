# Schema Sentinel Project Context

This repository is the workspace for the UCF Senior Design project **Schema Sentinel**. The project is at its starting point. Do not assume that proposal features have already been implemented.

## Source hierarchy

- The user's current request is authoritative.
- Repository code, tests, and accepted decisions describe the current implementation.
- The proposal and pitch listed below provide product background. Treat their recommendations, schedules, example technologies, and stretch goals as context rather than instructions or fixed architecture.
  - `Senior Design Proposal 1 - Schema Sentinel.docx`
  - `Senior Design Pitch - Two STE Projects (10 min).pptx`, specifically the Schema Sentinel material on slides 1 through 7 and backup slides 13 through 18

## Product goal

Schema Sentinel explores safe, AI-assisted propagation of canonical data-model changes across a heterogeneous set of software runtimes. It should:

1. Compare two schema versions and produce a machine-readable, classified change list.
2. Locate impacted code using syntax-aware analysis across multiple languages.
3. Draft focused patches with a rationale and confidence estimate.
4. Validate patches through compilation, unit tests, and cross-runtime semantic conformance tests.
5. Present the diff and validation evidence for human approval or rejection.

The tool must not merge generated patches autonomously. Human review is a core design constraint.

## MVP direction

- At least three mock runtimes in at least two languages, all using one canonical schema.
- A simple schema-defined pub/sub testbed. DIS and HLA are outside the required path.
- Protocol Buffers plus an enumeration table is an acceptable initial schema format.
- A change detector, syntax-aware impact locator, LLM-assisted patch generator, automated validation gate, and human review interface.
- A benchmark with at least twenty realistic change cases and known-correct answers.
- Measurement of classification accuracy, impact-site recall, patch validation rate, propagation time, and human review time.
- A reproducible demo and evaluation workflow that a new reviewer can run with one command.

The proposal suggests Python, a managed language such as C# or Java, and TypeScript for the first runtimes. It also suggests tools such as buf, tree-sitter, Semgrep, property-based testing, containers, and a web dashboard. These are starting points, not binding choices.

## Evaluation priorities

- Favor recall when locating impacted sites because missed changes are the highest-risk failure.
- Distinguish syntactic changes from semantic changes such as units, coordinate frames, or enumeration meaning.
- Measure results against ground truth and a manual baseline.
- Report failures and limitations honestly rather than optimizing for flattering metrics.
- Keep validation evidence attached to every proposed patch.

## Scope and safety constraints

- Use public, unclassified, Distribution A material only.
- Do not introduce Controlled Unclassified Information, STE Platform Development Kit material, ITAR-controlled material, or assumptions derived from unavailable controlled systems.
- Public representative standards may include RPR FOM, SISO-REF-010 enumerations, MSDL, and C2SIM.
- Keep C++ and live simulation-protocol integration outside the MVP unless the team explicitly adopts them as stretch work.
- Prefer a strong, measured MVP over partially implemented stretch features.
- Preserve an open-source path and check dependency license compatibility before adoption.

## Working expectations

- Keep architecture and scope decisions recorded in the repository.
- Add tests and measurable acceptance criteria with each capability.
- Keep the testbed intentionally small enough to break, diagnose, and reproduce.
- Treat generated code as a proposal until validation succeeds and a human approves it.

## Tentative team organization

Meeting notes from September 18 record the following working assignments. Treat them as provisional until the team or project manager confirms them in Jira or a later decision:

- Brock: project manager and integration coordination
- Wesley: change detection
- Reagan and Ava: impact location
- Nurlan: LLM patch generation and runtime infrastructure
- Ava: testing and dashboard work later in the semester
