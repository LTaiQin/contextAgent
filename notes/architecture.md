# Architecture Sketch

## High-Level Flow

```text
User message
  -> session intake
  -> task boundary detector
  -> context selector
  -> skill candidate router
  -> agent execution
  -> task memory update
  -> response
```

## Main Components

### 1. Session Intake

Receives messages from the chat app. The chat session is treated as a transport channel, not as the true reasoning context.

### 2. Task Boundary Detector

Classifies the incoming message:

- `continue_task`: belongs to an active task.
- `new_task`: starts an independent task.
- `related_task`: related to an old task but should use only a summary.
- `ambiguous`: needs clarification or conservative isolation.

Possible signals:

- topic shift
- new entities or variables
- explicit references such as "previous", "刚才", "上一个"
- time gap
- skill/domain shift
- user intent shift

### 3. Context Selector

Builds the actual prompt context for the model.

Context layers:

- current message
- active task transcript
- compact task summary
- user profile memory
- project memory
- global system rules

Default rule: include less context unless relevance is clear.

### 4. Skill Candidate Router

Routes only after context isolation. This prevents unrelated old context from pushing the router toward stale skills.

Routing output:

- candidate skills
- confidence
- reason
- required context scope
- whether to ask clarification

### 5. Task Store

Stores task-level state:

```json
{
  "task_id": "task_2026_05_31_001",
  "status": "active",
  "topic": "math problem",
  "summary": "Solving a quadratic equation problem.",
  "messages": [],
  "skills_used": [],
  "local_facts": {},
  "created_at": "...",
  "updated_at": "..."
}
```

### 6. Closure and Summarization

When a task appears complete, archive raw detail and keep only a compact summary.

This reduces future interference and makes long-running chat sessions manageable.

## First Version Policy

A practical first version can be rule-assisted rather than fully learned:

- If domain changes strongly, create a new task.
- If the user says "another question" or starts a new problem, create a new task.
- If the user says "continue", "use the above", or "based on that", continue the active task.
- For math, isolate by default unless the user explicitly links problems.
- Router sees current message plus selected task context, not the full session.

