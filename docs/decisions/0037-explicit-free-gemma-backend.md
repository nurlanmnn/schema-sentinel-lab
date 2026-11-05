# 0037. Add an explicit free Gemma evaluation backend

The user authorized trying Google's free Gemma 4 31B endpoint through OpenRouter.
The selected model and provider are fixed in the cloud adapter. The user must
select the OpenRouter backend explicitly. Authentication uses a local environment
variable or an owner-only key file outside the repository.

The generator reuses the existing prompts, edit resolvers and validation gate.
The report records the transport source hash, request body without credentials,
provider response, usage and elapsed time. Review exports retain the cloud
transport source when relevant.

A three-request telemetry rename trial precedes the eight-case comparison.
The local HTTP checks are synthetic. They establish request and error handling,
and do not count toward model quality or live patch validation rates.

Google's JSON mode provides object output without full schema enforcement.
Disabled reasoning and server-side model implementation differ from the local
Ollama baseline. Record these differences when interpreting a comparison.

No new third-party dependency was introduced.
