# Artifact standard

Every artifact this system writes — ticket descriptions, comments, plans, review
verdicts, handoff reports — follows the rules below. Source:
https://noslopgrenade.com/ ("use AI to make things clearer, not longer").

The reader is a busy engineer who will act on this in the next five minutes.
Write for them.

## The rules

1. **Judgment first.** Open with the decision, the answer, or the status in one
   sentence. Never open with restated context, a preamble, or "I analyzed the
   codebase and found several things worth considering."
2. **Clearer, not longer.** If a sentence does not change what the reader does,
   delete it. A ticket description that fits in 15 lines must not be 60.
3. **No wall of text.** Nothing pasted that a human would not have written by
   hand. If the content genuinely needs 40 lines, it needs a table or a list,
   not paragraphs.
4. **Leave room for pushback.** State open questions as open questions. Do not
   bury a decision that needs challenging inside a confident essay.
5. **Every claim is sourced or flagged.** `file.ts:120`, a Linear id, a metric
   query, a URL. If it is unverified, write `[assumption]` or `[unverified]`
   inline. Never state a guess in the same voice as a measurement.
6. **No filler vocabulary.** Cut: "comprehensive", "robust", "seamless",
   "leverage", "delve", "it's worth noting that", "in today's fast-paced",
   "significantly enhances". Cut emoji unless the reader asked for them.
7. **No invented facts.** No fabricated line numbers, metrics, ticket ids, or
   quotes. Absent information is reported as absent.
8. **English only**, in every artifact and every inter-agent message, regardless
   of the language the human used.

## Ticket description shape

```
<One sentence: what this ticket delivers.>

**Why now:** <one line, or delete the section>

**Scope**
- <concrete change, with file/repo path>
- <concrete change>

**Out of scope:** <one line — prevents the scope fight later>

**Contract**
| In | Out |
|---|---|
| <what it consumes> | <what it produces> |

**Done when**
- [ ] <observable, checkable — not "works well">
- [ ] <observable>

**Open questions**
- <question> — owner: <who decides>
```

Delete any section that would be empty. An empty section is noise.

## Comment shape (progress, review, verdict)

```
<Verdict or status in one sentence.>

<2-6 lines of the evidence that supports it, with paths/ids.>

<Next action, and who owns it.>
```

## Self-check before writing

- Could the first sentence stand alone as the whole message? If not, rewrite it.
- Is any sentence there to look thorough rather than to be read? Cut it.
- Did I mark every unverified claim?
