# Threat Alert System

A workflow that ingests cybersecurity news, decides whether each article matters to a client, scores the relevant ones with several expert classifiers, and sends a threat alert when the average score is above a configurable threshold.

Built with Python and LangGraph.

## How it works

```text
ingest → dedup → enrich ─(one branch per article)→ process_article → deliver
```

| Step | What it does |
|---|---|
| `ingest` | Reads every configured RSS feed. A failing feed is logged and skipped. |
| `dedup` | Drops articles already processed and limits the batch to control cost. |
| `enrich` | Extracts CVE IDs with a regex and stores the full article. |
| `process_article` | Runs in parallel, one branch per article, with limited concurrency. |
| `deliver` | Saves alerts, sends them, and marks articles as processed. |

Each article goes through these stages:

1. **Quick relevance:** a small model compares the title and summary with the client's tech stack and answers yes, no or unsure.
2. **Deep relevance:** only for unsure articles, a larger model reads the full client description and article text, and answers yes or no.
3. **Experts:** three independent classifiers each return a score from 0 to 10.
   - **Severity:** the intrinsic technical impact.
   - **Urgency:** evidence of attacker activity right now.
   - **Exposure:** how directly the threat touches this client.
4. **Decision:** if the average is above the threshold, a larger model writes the alert. It does not decide whether to alert.

## Design decisions

- **Relevance is a gate, not part of the average.** A severe threat that cannot affect the client should not alert.
- **Cost control.** Deduplication, a batch limit and a cheap first filter run before the more expensive steps. The larger model only runs when needed.
- **Failures are classified conservatively.** Only a model refusal or invalid output is permanent. Any other failure leaves the article unprocessed, so it is retried on the next run.
- **Delivery is at-least-once.** An alert is saved before it is sent, and unsent alerts are retried without new model calls. A crash after sending could repeat an alert, which is better than losing one.
- **A refused draft still alerts.** If the model will not write the alert, a plain fallback alert is sent.
- **Article text is untrusted.** Prompts mark it as data and responses are constrained to a schema. This reduces prompt injection risk but does not remove it.

## Running it

You need an Anthropic API key. Slack is optional; alerts always go to the console.

```bash
cp .env.example .env    # then fill in your values
```

**With uv:**

```bash
uv sync
uv run threatalert
uv run threatalert --config path/to/config.yaml
```

Run it from the project root so the default config path resolves.

**With Docker:**

```bash
docker compose run --rm threatalert
```

The database lives in a Docker volume, so processed articles are remembered between runs.

**Tests,** which need no network or API key:

```bash
uv run pytest
```

Each run processes the new articles once and exits. To run it on a schedule, use cron or a similar scheduler.

## Configuration

Everything is in `config/config.yaml`: threshold, feeds, active experts, client profile, models per role, concurrency and batch size. Secrets are only read from `.env`.

The relevance filter treats `tech_stack` as the client's complete inventory, so its accuracy depends on keeping that list up to date.

## Project structure

```text
src/threatalert/
├── main.py         Entry point: builds the pieces and runs the graph
├── graph.py        LangGraph workflow and per-article analysis
├── config.py       Loads and validates the YAML config
├── models.py       Data models
├── ingestion/      News sources
├── dedup.py        Filters articles already processed
├── store.py        SQLite storage
├── text.py         CVE extraction and HTML cleaning
├── llm.py          Model client with one model per role
├── prefilter.py    Two-stage relevance gate
├── experts/        Expert classifiers
├── scoring.py      Average score
├── alerting.py     Threshold, alert drafting and formatting
└── notifiers.py    Console and Slack delivery
```

**To extend it:**
- **Add a feed:** add it to `feeds` in the config.
- **Add an expert:** create a class in `experts/`, register it in `EXPERTS` in `main.py` and allow its name in `config.py`.
- **Add a source type:** subclass `Source` in `ingestion/`.
- **Add a channel:** subclass `Notifier` in `notifiers.py`.

## What I would improve with more time

- A labelled set of articles to measure the relevance filter, since a wrong discard goes unnoticed.
- Full article text for experts and for feeds without content, respecting each site's terms and crawl limits.
- A retry limit for articles that keep failing.
- Multiple clients, reusing the global severity and urgency scores.
- Configurable expert weights, and grouping articles about the same story.
- Postgres instead of SQLite for concurrent access.
