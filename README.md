# dox

Read the docs from your terminal. No browser, no noise, no nonsense.

`dox` fetches technical documentation from the web, strips away the chrome (navbars, sidebars, cookie banners, footers), and gives you clean markdown. It's fast, it caches aggressively, and every command speaks JSON for machines.

```
uvx dox-cli fetch https://docs.python.org/3/library/asyncio.html
```

That's it. You get the docs, in your terminal, ready to read.

## Install

```
# Run directly (nothing to install)
uvx dox-cli fetch <url>

# Or install globally
uv tool install dox-cli
```

## Why dox?

Documentation lives on the web. Your workflow lives in the terminal. Something has to give, and it shouldn't be your focus.

- **You're in a flow state** and need to check a function signature. You don't want to leave the terminal, open a browser, wait for the page, scroll past the navbar, find the section, then context-switch back.
- **Your AI agent** needs to read docs to solve a problem. It can't browse the web, but it can run a CLI. It doesn't need pretty HTML -- it needs clean text.
- **You're on a remote server** with no browser. SSH doesn't have tabs.

`dox` solves all three.

## Commands

### `dox fetch` -- Read a page

Fetches a URL, strips everything that isn't content, returns clean markdown.

```
$ dox fetch https://docs.python.org/3/library/pathlib.html

# pathlib -- Object-oriented filesystem paths

This module offers classes representing filesystem paths with semantics
appropriate for different operating systems...
```

Links are resolved to absolute URLs so they still work. Code blocks are preserved. Images are stripped because they don't belong in a terminal.

### `dox search` -- Find the right page

Search the web scoped to a documentation site. Powered by DuckDuckGo.

```
$ dox search "context managers" --site docs.python.org

1. contextlib -- Utilities for with-statement contexts
   https://docs.python.org/3/library/contextlib.html
   ...

2. With Statement Context Managers
   https://docs.python.org/3/reference/datamodel.html
   ...
```

Pipe results into `dox fetch` to read the top hit. Or use `--json` and let your agent decide.

### `dox excerpt` -- Pull just one section

Don't need the whole page? Pull a single section by heading match.

```
$ dox excerpt https://docs.python.org/3/library/asyncio-task.html "creating tasks"

## Creating Tasks

asyncio.create_task(coro, *, name=None, context=None)
    Wrap the coro coroutine into a Task and schedule its execution...
```

The match is case-insensitive and substring-based. If there's no match, `dox` shows you what sections are available so you can try again.

### `dox toc` -- See what's on a page

Get the heading structure before committing to reading the whole thing.

```
$ dox toc https://click.palletsprojects.com/en/stable/quickstart/

Quickstart
  Basic Concepts - Creating a Command
  Echoing
  Nesting Commands
  Adding Parameters
    ...
```

### `dox links` -- Discover related pages

Extract every link from a page. Useful for crawling a doc site or discovering related topics.

```
$ dox links https://docs.python.org/3/library/asyncio.html

Coroutines and Tasks: https://docs.python.org/3/library/asyncio-task.html
Streams: https://docs.python.org/3/library/asyncio-stream.html
Event Loop: https://docs.python.org/3/library/asyncio-eventloop.html
...
```

### `dox crawl` -- Ingest an entire docs section

Follow links from a starting page, fetch everything in parallel, get it all as one stream of markdown.

```
$ dox crawl https://click.palletsprojects.com/en/stable/quickstart/ --depth 1 --limit 5

Crawling (depth=1, limit=5)
  [1] https://click.palletsprojects.com/en/stable/quickstart/
  [2] https://click.palletsprojects.com/en/stable/commands/
  [3] https://click.palletsprojects.com/en/stable/options/
  ...
Done. 5 pages crawled.
```

By default, crawl stays within the same URL path prefix (so starting from `/en/stable/quickstart/` stays under `/en/stable/`). Use `--any-path` to go site-wide.

```
# Crawl deeper, fetch more
dox crawl https://htmx.org/docs/ --depth 2 --limit 20

# Go site-wide instead of staying under the start path
dox crawl https://htmx.org/docs/ --any-path

# Control parallelism
dox crawl https://htmx.org/docs/ --concurrency 8
```

### `dox cache` -- Manage cached pages

Pages are cached locally in SQLite for 24 hours. Repeated reads are instant.

```
$ dox cache stats
Cached pages: 12
Cache size: 0.3 MB

$ dox cache clear
Cleared 12 cached pages.
```

Bypass the cache anytime with `--no-cache`.

## Chunking

Long pages blow up agent context windows. Use `--max-tokens` to split content into manageable pieces.

**See how a page splits before reading it:**

```
$ dox fetch https://docs.python.org/3/library/asyncio-task.html --max-tokens 2000

Content has ~8500 tokens, split into 5 chunks (max 2000 each):
  chunk 1/5 — ~1980 tokens
  chunk 2/5 — ~1950 tokens
  chunk 3/5 — ~1900 tokens
  chunk 4/5 — ~1820 tokens
  chunk 5/5 — ~850 tokens

Use --chunk N to read a specific chunk.
```

**Read a specific chunk:**

```
$ dox fetch https://docs.python.org/3/library/asyncio-task.html --max-tokens 2000 --chunk 1
```

**JSON output includes chunk metadata** so agents know where they are:

```json
{
  "url": "https://docs.python.org/3/library/asyncio-task.html",
  "title": "Coroutines and Tasks",
  "chunk": 1,
  "total_chunks": 5,
  "tokens": 1980,
  "content": "# Coroutines and Tasks\n\n..."
}
```

Chunks split at section headings first, then paragraph boundaries, then line boundaries as a last resort. Content is never cut mid-sentence.

Works on `fetch`, `excerpt`, and `crawl`. For `crawl`, all pages are merged into one document before chunking, so an agent can page through an entire doc site in fixed-size pieces.

## Built for agents

Every command supports `--json` for structured, parseable output. This is the killer feature.

An AI agent working on your codebase can:

1. **Search** for the right docs page: `dox search "retry logic" --site docs.aiohttp.org --json`
2. **Scan** the table of contents: `dox toc <url> --json`
3. **Extract** just the section it needs: `dox excerpt <url> "retry" --json`
4. **Crawl** an entire library's docs: `dox crawl <url> --depth 2 --limit 20 --json`
5. **Page through** large results without blowing the context window: `--max-tokens 4000 --chunk 1`

A few shell commands, zero browser automation, minimal tokens consumed. The agent gets exactly the information it needs and nothing else.

### JSON output examples

```json
// dox fetch <url> --json
{
  "url": "https://docs.python.org/3/library/asyncio.html",
  "title": "asyncio -- Asynchronous I/O",
  "content": "# asyncio -- Asynchronous I/O\n\nasyncio is a library to write..."
}

// dox search "asyncio" --site docs.python.org --json
{
  "query": "asyncio",
  "site": "docs.python.org",
  "results": [
    {
      "title": "asyncio -- Asynchronous I/O",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "snippet": "asyncio is a library to write concurrent code..."
    }
  ]
}

// dox toc <url> --json
{
  "url": "...",
  "title": "...",
  "headings": [
    {"level": 1, "text": "asyncio", "anchor": "asyncio", "link": "...#asyncio"}
  ]
}

// dox crawl <url> --depth 1 --limit 3 --json
{
  "url": "...",
  "depth": 1,
  "pages_crawled": 3,
  "pages": [
    {"url": "...", "title": "...", "content": "..."},
    {"url": "...", "title": "...", "content": "..."},
    {"url": "...", "title": "...", "content": "..."}
  ]
}

// dox fetch <url> --max-tokens 2000 --json (chunk index)
{
  "total_tokens": 8500,
  "max_tokens": 2000,
  "total_chunks": 5,
  "chunks": [
    {"chunk": 1, "tokens": 1980},
    {"chunk": 2, "tokens": 1950}
  ]
}

// dox fetch <url> --max-tokens 2000 --chunk 1 --json
{
  "url": "...",
  "title": "...",
  "chunk": 1,
  "total_chunks": 5,
  "tokens": 1980,
  "content": "..."
}
```

### MCP / tool-use integration

`dox` commands map directly to tool definitions. Each command has clear inputs (URL, query, section name), structured outputs (JSON), and predictable behavior. No interactive prompts, no pagination, no surprises.

```yaml
# Example tool definitions for an agent framework
- name: read_docs
  command: dox fetch {{url}} --max-tokens 4000 --chunk {{chunk}} --json
  description: Fetch a documentation page (chunked to fit context window)

- name: search_docs
  command: dox search "{{query}}" --site {{site}} --json
  description: Search for documentation pages

- name: read_docs_section
  command: dox excerpt {{url}} "{{section}}" --json
  description: Read a specific section from a documentation page

- name: crawl_docs
  command: dox crawl {{url}} --depth {{depth}} --limit {{limit}} --json
  description: Crawl a documentation site and return all pages

- name: crawl_docs_chunked
  command: dox crawl {{url}} --depth 1 --limit 10 --max-tokens 4000 --chunk {{chunk}} --json
  description: Crawl docs and page through results in fixed-size chunks
```

## Design decisions

- **Markdown, not HTML.** Terminals render markdown. Agents consume markdown. HTML is for browsers.
- **Aggressive caching.** Documentation doesn't change every minute. Cache by default, bypass on demand.
- **Substring heading match.** You shouldn't need to know the exact heading text. "install" matches "Installation Guide".
- **Section-aware chunking.** Splits at headings and paragraph boundaries, never mid-sentence. Agents get coherent pieces, not arbitrary byte slices.
- **Parallel crawling.** Fetches multiple pages concurrently with configurable parallelism. Stays within the same docs section by default so you don't accidentally crawl an entire domain.
- **No JavaScript rendering.** Most documentation sites work fine without JS. This keeps `dox` fast and dependency-light. If a site requires JS to render content, `dox` isn't the right tool.
- **No API keys.** Search uses DuckDuckGo's HTML endpoint. No accounts, no rate limits, no configuration.

## License

MIT
