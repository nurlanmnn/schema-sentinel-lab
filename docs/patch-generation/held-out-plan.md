# Held-out evaluation plan

Status: plan. No held-out case exists yet, and the model has not seen any.

The 6/8 and 7/8 results come from eight cases that shaped the prompt. A
held-out case is one that is written after the lock (decision 0041), sealed
before any model run, and scored once. This plan says how to build those cases
so the result means something to the sponsor.

## Sources, in priority order

1. **Sponsor case studies.** The proposal commits the sponsor to "three to five
   change scenarios … from real experience" in week 3, with program detail
   stripped. None are in the repository. These are the best held-out cases
   because nobody on the team chose them. A request draft is at the end.
2. **Team-authored cases on a new domain.** An `orders` runtime the prompt has
   never seen. Its schemas already exist as locator-only snippets in
   `patchgen/corpus/orders/`; it needs buildable Python, TypeScript and C#
   services plus an oracle.
3. **Team-authored cases on existing domains,** using change kinds that are not
   in the development set.

## Rules

"Written after the lock" is not enough on its own. Everyone building these cases,
including the AI agents, has seen where Gemma fails and could pick or shape
easier cases without meaning to. The rules below move choices that matter to
someone who has not studied the model's failures.

1. **An independent evaluator approves the cases and their requirements first.**
   A teammate who has not reviewed model outputs (or the sponsor) approves the
   case list *and* each case's detailed `intended_behavior` before any
   implementation starts. The list below is a proposal for them to accept,
   change or replace. Record who approved what, and when, in the registry.
2. **Pre-register, and keep the denominator.** Commit the approved list before
   writing code. No adding or swapping cases after seeing model output. A case
   that turns out broken is withdrawn, stays in the denominator, and is reported
   with its reason.
3. **Prove each case is buildable, solvable and discriminating before sealing.**
   - A frozen buildable baseline in all three runtimes, a validation profile, and
     wiring so the live route actually runs it. Adding ids to `HELD_OUT_CASES`
     only labels results; `live_suite` must also accept them.
   - A deterministic reference patch that passes every check end to end. It is
     never sent to the model.
   - **At least three plausible wrong patches** that the checks reject for the
     stated reason. One negative control proves little.
   - Boundary inputs for each case's semantics (see the case list).
4. **Seal and enforce.** Commit `held-out/registry.json` with SHA-256 hashes of
   every fixture, baseline source, ground truth, oracle, reference and wrong
   patch, plus the 0041/0042 fingerprints and hashes of `repair_suite.py` and the
   oracle runners. Push that commit to GitHub before the run, so its timestamp is
   external. The held-out runner must verify the registry at execution and refuse
   any mismatch.
5. **Score once.** One locked one-shot run, then one bounded repair run. Every
   attempt is retained. The first held-out run is the reported score. A rerun
   (for example after a provider outage) is reported separately with its reason,
   never substituted.
6. **No tuning in between.** Changing the prompt, parser, sampling, feedback
   filter or checks after sealing invalidates the held-out claim and needs a new
   decision and a new set of cases.
7. **Repair is reported as conditional.** Repair rounds learn from the case's own
   oracle verdicts, so the headline held-out number is first pass. Repaired
   held-out results are reported as "with validation feedback", consistent with
   decision 0042.

## Pre-registered case list (proposed)

For the independent evaluator to accept, change or replace. Each case must need
runtime edits in all three languages. Cases are labelled honestly:
**new mechanism** means no development or corpus case uses that kind of change;
**transfer** means a known kind on new code or in a new combination. Both are
useful, but they answer different questions and are reported separately.

| Id | Domain | Change | Label | Baseline work and semantics to pin down |
| --- | --- | --- | --- | --- |
| H1 | orders (new) | Remove `currency`; USD-only policy | transfer | Same policy as corpus case `orders-remove-currency`; newly executable, not newly authored |
| H2 | orders (new) | Amount from float dollars to int64 cents | transfer (composition) | Needs a float-dollar baseline (corpus uses cents). Rounding mode, negative amounts, overflow |
| H3 | orders (new) | Add `PARTIALLY_SHIPPED` status that counts as open | transfer | Needs an orders status baseline; resembles corpus `BACKORDERED`. Unknown-value handling |
| H4 | telemetry | Heading from compass degrees to math radians | **new mechanism** | Add heading to baseline. Axis origin, clockwise vs counter-clockwise, wrap at 2π, 0/90/359.9° boundaries |
| H5 | telemetry | Seconds `int64` to `google.protobuf.Timestamp` | **new mechanism** | Add timestamp to baseline; Timestamp codegen in all three languages. UTC only, nanosecond precision, epoch and pre-epoch |
| H6 | inventory | Split `location` into `warehouse` + `bin` | **new mechanism** | Add location to baseline. Separator, missing bin, extra separators |
| H7 | inventory | Rename field and change its JSON key together | transfer (composition) | Recombines existing rename and JSON-key mechanisms |
| H8 | pubsub entity | Add `priority` with a default consumers must honour | transfer | Resembles `inventory-reservation`. Absent vs explicit default |

Two of these (H2 and H4) also get a **minimal-semantics variant**, scored
separately. It says what changed ("amount is now in cents") but not how to
convert it. It must still be unambiguous to a competent engineer. This measures
whether the model works out semantics, which the current cases never test
because `intended_behavior` spells them out. A variant shares code with its
parent case, so the two results are correlated, not independent evidence.

## Review checklist (for the teammate)

- Is `intended_behavior` unambiguous? Could a competent engineer implement it
  without asking a question?
- Does the oracle check exactly what the requirement says, no more and no less?
- Does the requirement or oracle hint at a specific implementation, or favour
  a wording the model has seen?
- Does the reference patch pass, and does each negative control fail for the
  stated reason?
- Is everything public, synthetic and Distribution A?

## What gets reported

Separately, never summed: development first-pass and repaired (6/8, 7/8);
held-out first pass (the headline), split into new-mechanism and transfer cases;
held-out with validation feedback (within one and two rounds); minimal-semantics
variants; withdrawn cases with reasons; failure stage per case. With 8 held-out cases, no significance claim
is made. The result answers whether 6/8 carries over to unseen cases, not what
the true rate is.

## Order of work

1. Send the sponsor request. Ask a teammate who has not looked at model outputs
   to act as the independent evaluator.
2. The evaluator approves the case list and each detailed `intended_behavior`.
   Commit that approval (pre-registration).
3. Harness work: a held-out runner that verifies the registry and lets
   `live_suite` accept sealed held-out ids.
4. H4–H8 on existing domains: baseline additions first, then about 150–250 lines
   each following the existing case pattern, with three wrong patches per case.
5. The `orders` domain runtimes and oracle, then H1–H3.
6. Evaluator review against the checklist, seal, push, then the single locked run.
7. Fold any sponsor cases in as a second sealed set when they arrive.

An independent read-only Codex review of this plan found the selection-bias
gap, overstated novelty for H1/H2/H3/H7/H8, unproven live eligibility, weak
single negative controls, and unenforced seals. The rules and labels above
address each.

## Sponsor request (draft, not sent)

> Hello Mr. Enloe,
>
> The proposal mentions three to five change case studies from real experience
> (the shape of the change, what broke, how it was found and roughly how long it
> took), with program-specific detail removed. We are ready to use them as
> held-out benchmark cases: our patch generator has been frozen, so these cases
> would measure it on changes it was never tuned against. Even short written
> descriptions are enough; we will build the public, synthetic versions
> ourselves. Could you share them, or tell us who to contact?
>
> Thank you,
> Nurlan Mammadli, Schema Sentinel team
