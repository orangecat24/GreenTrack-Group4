# GreenTrack working instructions

- Use Python FastAPI for the API and React with TypeScript and Vite for the SPA.
- Prefer simple components and small, readable modules over extra frameworks.
- Write generous educational comments explaining purpose and non-obvious logic.
  Give Python modules, classes, and functions useful docstrings.
- After every task, explain the result in junior-friendly language, including
  how to run it, what was checked, and how the important pieces connect.
- Record substantial changes, decisions and teammate handoffs in repository
  Markdown, with links from the relevant README/handoff. PR descriptions may
  supplement these records but must not be their only location. Distinguish
  teammate-reported AWS status from independently verified deployment results.
- Do not use Django, Next.js, or Redux.
- Mock mode must not make real AWS or AI calls, require credentials, or claim
  that live integrations are connected. Label synthetic data and placeholders.
- Preserve existing work. Do not inspect credentials or expose secret values.
- Do not commit or push unless the user explicitly instructs you to do so.
