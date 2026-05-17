# Mode: oferta — Full A–G Evaluation

When the candidate pastes an offer (text or URL), ALWAYS deliver all 7 blocks (A–F evaluation + G legitimacy):

## Step 0 — Archetype Detection

Classify the offer into one of the 6 archetypes (see `_shared.md`). If hybrid, indicate the 2 closest. This determines:
- Which proof points to prioritize in Block B
- How to rewrite the summary in Block E
- Which STAR stories to prepare in Block F

## Block A — Role Summary

Table with:
- Detected archetype
- Domain (platform / agentic / LLMOps / ML / enterprise)
- Function (build / consult / manage / deploy)
- Seniority
- Remote (full / hybrid / onsite)
- Team size (if mentioned)
- TL;DR in one sentence

## Block B — CV Match

Read `cv.md`. Build a table mapping each JD requirement to exact lines in the CV.

**Adapted to the archetype:**
- FDE → prioritize fast-delivery and client-facing proof points
- SA → prioritize system design and integrations
- PM → prioritize product discovery and metrics
- LLMOps → prioritize evals, observability, pipelines
- Agentic → prioritize multi-agent, HITL, orchestration
- Transformation → prioritize change management, adoption, scaling

**Gaps section** with a mitigation strategy for each. For each gap:
1. Is it a hard blocker or a nice-to-have?
2. Can the candidate demonstrate adjacent experience?
3. Is there a portfolio project that covers this gap?
4. Concrete mitigation plan (cover-letter sentence, quick project, etc.)

## Block C — Level & Strategy

1. **Detected level** in the JD vs. **the candidate's natural level for that archetype**
2. **"Sell senior without lying" plan:** archetype-specific phrasing, concrete achievements to surface, how to position founder experience as an advantage
3. **"If they downlevel me" plan:** accept if comp is fair, negotiate a 6-month review, set clear promotion criteria

## Block D — Compensation & Demand

Use WebSearch for:
- Current salaries for the role (Glassdoor, Levels.fyi, Blind)
- The company's comp reputation
- Demand trend for the role

Build a table with data and cited sources. If no data, say so — don't invent.

## Block E — Tailoring Plan

| # | Section | Current state | Proposed change | Why |
|---|---------|---------------|-----------------|-----|
| 1 | Summary | ... | ... | ... |
| ... | ... | ... | ... | ... |

Top 5 CV changes + Top 5 LinkedIn changes to maximize the match.

## Block F — Interview Plan

6–10 STAR+R stories mapped to JD requirements (STAR + **Reflection**):

| # | JD requirement | STAR+R story | S | T | A | R | Reflection |
|---|----------------|---------------|---|---|---|---|------------|

The **Reflection** column captures what was learned or what would be done differently. This signals seniority — junior candidates describe what happened, senior candidates extract lessons.

**Story Bank:** If `interview-prep/story-bank.md` exists, check whether any of these stories are already there. If not, append the new ones. Over time this builds a reusable bank of 5–10 master stories that can be adapted to any interview question.

**Selected and framed by the archetype:**
- FDE → emphasize delivery speed and client-facing work
- SA → emphasize architecture decisions
- PM → emphasize discovery and trade-offs
- LLMOps → emphasize metrics, evals, production hardening
- Agentic → emphasize orchestration, error handling, HITL
- Transformation → emphasize adoption and organizational change

Also include:
- 1 recommended case study (which project to present and how)
- Red-flag questions and how to answer them (e.g. "why did you sell your company?", "do you have direct reports?")

## Block G — Posting Legitimacy

Analyze the job posting for signals that indicate whether this is a real, active opening. This helps the user prioritize effort on opportunities most likely to result in a hiring process.

**Ethical framing:** Present observations, not accusations. Every signal has legitimate explanations. The user decides how to weigh them.

### Signals to analyze (in order):

**1. Posting Freshness** (from the Playwright snapshot already captured in Step 0):
- Date posted or "X days ago" — extract from the page
- Apply button state (active / closed / missing / redirects to a generic page)
- If the URL redirected to a generic careers page, note it

**2. Description Quality** (from the JD text):
- Does it name specific technologies, frameworks, tools?
- Does it mention team size, reporting structure, or org context?
- Are the requirements realistic? (years of experience vs. technology age)
- Is there a clear scope for the first 6–12 months?
- Is salary/compensation mentioned?
- What ratio of the JD is role-specific vs. generic boilerplate?
- Any internal contradictions? (entry-level title + staff-level requirements, etc.)

**3. Company Hiring Signals** (2–3 WebSearch queries, combine with Block D research):
- Search: `"{company}" layoffs {year}` — note date, scale, departments
- Search: `"{company}" hiring freeze {year}` — note any announcements
- If layoffs are found: are they in the same department as this role?

**4. Reposting Detection** (from scan-history.tsv):
- Check whether the same company + similar role title appeared before with a different URL
- Note how many times and over what period

**5. Role Market Context** (qualitative, no additional queries):
- Is this a common role that typically fills in 4–6 weeks?
- Does the role make sense for this company's business?
- Is the seniority level one that legitimately takes longer to fill?

### Output format:

**Assessment:** One of three tiers:
- **High Confidence** — Multiple signals suggest a real, active opening
- **Proceed with Caution** — Mixed signals worth noting
- **Suspicious** — Multiple ghost-job indicators, investigate before investing time

**Signals table:** Each observed signal with its finding and weight (Positive / Neutral / Concerning).

**Context Notes:** Any caveats (niche role, government job, evergreen position, etc.) that explain potentially concerning signals.

### Edge case handling:
- **Government / academic postings:** Longer timelines are standard. Adjust thresholds (60–90 days is normal).
- **Evergreen / continuous hire postings:** If the JD explicitly says "ongoing" or "rolling," note it as context — this is not a ghost job, it is a pipeline role.
- **Niche / executive roles:** Staff+, VP, Director, or highly specialized roles legitimately stay open for months. Adjust age thresholds accordingly.
- **Startup / pre-revenue:** Early-stage companies may have vague JDs because the role is genuinely undefined. Weight description vagueness less heavily.
- **No date available:** If posting age cannot be determined and no other signals are concerning, default to "Proceed with Caution" with a note that limited data was available. NEVER default to "Suspicious" without evidence.
- **Recruiter-sourced (no public posting):** Freshness signals are unavailable. Note that active recruiter contact is itself a positive legitimacy signal.

---

## Post-evaluation

**ALWAYS** after generating blocks A–G:

### 1. Save the report .md

Save the full evaluation to `reports/{###}-{company-slug}-{YYYY-MM-DD}.md`.

- `{###}` = next sequential number (3 digits, zero-padded)
- `{company-slug}` = company name in lowercase, no spaces (use hyphens)
- `{YYYY-MM-DD}` = current date

**Report format:**

```markdown
# Evaluation: {Company} — {Role}

**Date:** {YYYY-MM-DD}
**Archetype:** {detected}
**Score:** {X/5}
**Legitimacy:** {High Confidence | Proceed with Caution | Suspicious}
**PDF:** {path or pending}

---

## A) Role Summary
(full content of Block A)

## B) CV Match
(full content of Block B)

## C) Level & Strategy
(full content of Block C)

## D) Compensation & Demand
(full content of Block D)

## E) Tailoring Plan
(full content of Block E)

## F) Interview Plan
(full content of Block F)

## G) Posting Legitimacy
(full content of Block G)

## H) Draft Application Answers
(only if score >= 4.5 — draft answers for the application form)

---

## Extracted keywords
(list of 15–20 JD keywords for ATS optimization)
```

### 2. Log it in the tracker

**ALWAYS** log to `data/applications.md`:
- Next sequential number
- Current date
- Company
- Role
- Score: match average (1–5)
- Status: `Evaluated`
- PDF: ❌ (or ✅ if auto-pipeline generated a PDF)
- Report: relative link to the report .md (e.g. `[001](reports/001-company-2026-01-01.md)`)

**Tracker format:**

```markdown
| # | Date | Company | Role | Score | Status | PDF | Report |
```
