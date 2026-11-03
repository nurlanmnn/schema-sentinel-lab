# 0024: Strengthen deterministic analysis before more generation

On November 3 the user explicitly reprioritized change detection and impact
location before patch generation or fine-tuning. Sponsor suggestions are
uncertain product hypotheses; scope and architecture can change in response to
measured feasibility. The current user request supersedes decision 0021's live
generation priority. Human review and public/unclassified scope remain required.

The target is reliable, measurable behavior within an explicit supported scope,
with uncertainty and unsupported inputs reported honestly. Do not claim perfect
whole-program analysis or infer semantic meaning from protobuf syntax alone.

Priorities:

1. Audit descriptor comparison for silently missed structural/metadata changes,
   identity errors and ambiguous outcomes; add independent adversarial tests.
2. Distinguish proven changed-field references from conservative syntax matches.
   Preserve recall, record binding evidence and uncertainty, and never label a
   syntax match as proven receiver resolution.
3. Broaden component evaluation to at least twenty distinct authored cases with
   independent ground truth, including negatives, version distinctions, aliases,
   imports, dynamic access and unsupported inputs. These component cases do not
   count as twenty validated end-to-end migrations.
4. Strengthen the detector/locator/adapter contract so downstream generation
   cannot silently dismiss proven required references. Keep uncertain sites
   separate; blindly editing every name match is not acceptable.
5. Remove obsolete executable paths, dependencies and instructions after checking
   their callers. Preserve historical experiment evidence and Git history.

Initial retirement removes the diagnostic-prose locator, stale descriptor bins,
and old prototype probe. Current descriptor/Tree-sitter code remains active.
Experimental generator implementations are not automatically dead code: inspect
their tests, demo callers and evaluation role before retiring any strategy.

The known telemetry rename failure motivates a regression: Python line 12 was
located and supplied to the generator, which incorrectly marked the obsolete
access unaffected. Retrieval succeeded there; stronger reference evidence and
post-generation enforcement are still needed. Existing 45/45 known sites on six
small fixtures are regression evidence, not proof of general completeness.
