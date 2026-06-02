# Problem Framing

## Background

For ordinary users, an agent is likely to be connected to an existing chat application. That means many different requests happen in the same conversation thread:

- daily questions
- math problems
- writing tasks
- planning tasks
- coding tasks
- tool or skill calls
- follow-up corrections

A single long session is convenient for the user but risky for the agent. The session history becomes a mixed bag of unrelated facts, assumptions, temporary variables, partial answers, and tool choices.

## Context Conflict

Context conflict happens when information from an earlier task changes the model's behavior on a later task even though it should not.

Typical cases:

- Topic leakage: a prior life-advice discussion affects the tone or assumptions of a later math answer.
- Variable leakage: symbols from one math problem are reused in another.
- Constraint leakage: "use Python" or "be brief" from one task accidentally applies to another.
- Entity leakage: names, dates, or preferences from one task are assumed to apply elsewhere.
- Tool leakage: the agent keeps favoring a previously useful skill or tool.

## Skill Router Pressure

When many skills are installed, the router has two separate burdens:

1. Intent selection: which skill, if any, is relevant to this message?
2. Context selection: which previous turns should be visible to the router?

If the router sees the full mixed chat history, it may overfit to stale context and choose the wrong skill.

## Math-Specific Risk

Multiple math problems in one session are a clean example:

- Problem 1 defines `x` and `y`.
- Problem 2 also uses `x`, but with a different meaning.
- Problem 3 asks "use the previous result", but it may refer to the immediately previous problem, not all previous math in the session.

Without task boundaries, the model has to infer boundaries implicitly. That works sometimes, but it is not reliable enough for a general agent product.

## Target Outcome

The target is an agent runtime where each user message is processed with a deliberate context policy:

- what task this belongs to
- which prior messages are relevant
- which memories are allowed
- which skills are candidates
- when the task should be closed or summarized

