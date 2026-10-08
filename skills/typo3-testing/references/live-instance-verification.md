<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
<!-- SPDX-FileCopyrightText: Netresearch DTT GmbH -->

# Verifying a Change on a Running Instance

A green suite proves the code paths the tests reach. It does not show the page.
A backend module, a content element's backend preview or a rendered frontend
page is confirmed only after somebody looked at it in a running TYPO3 instance.
This file says when that look is owed, which tool takes it, and what the report
carries. It does not replace a committed test: a check that has to stay belongs
in `e2e-testing.md` as a Playwright spec.

## When the look is owed

- A template, a backend module, a content element or its backend preview changed.
- A bug report describes what a person sees, and the fix is declared done.
- A ticket is handed over for acceptance and needs a screenshot as evidence.

## Rules

1. **The real running instance, never a hand-built harness.** A local DDEV or
   Compose instance, or a staging system. Name the instance and its TYPO3
   version next to each screenshot.
2. **The final state.** Look after the cache flush, the deploy or the asset
   build that the change needs. A look taken before any of these describes the
   old page.
3. **Realistic data.** An empty list, a one-word title or a page without content
   hides overflow and wrapping defects. Measure the failure signal
   (`scrollWidth > clientWidth`, a console error, an HTTP status), not "it
   rendered".
4. **Read only on shared or production instances.** Creating records, scheduler
   tasks or users needs the human's go first, and the report says the database
   is shared.
5. **No password in the context.** A password typed through a browser tool
   lands in the transcript. Fill it from an environment variable inside a
   script, or log in by script and hand over only the session (a Playwright
   `storageState` file, a session cookie).

## Which tool

| Need | Tool |
|---|---|
| Click through the backend or frontend, acceptance screenshots, logged in | A scripted browser that fills the password from the environment and prints a few lines per step; at Netresearch the `typo3-browser` skill from the internal marketplace, where installed |
| Console errors, network requests, computed CSS, Lighthouse | Chrome DevTools MCP (`browser-testing-with-devtools` skill) |
| Ad-hoc interaction without a TYPO3-aware tool | Playwright MCP; every step returns a page snapshot, and a typed password stays in the transcript |
| No Playwright and no browser MCP (npm blocked) | A Node.js runner on the Chrome DevTools Protocol (`e2e-testing.md`, *Ad-hoc Browser Check Without Playwright (CDP Fallback)*) |
| A check that must keep passing | A Playwright spec (`e2e-testing.md`) |
| Status code, headers, a redirect | `curl` |

On WSL or another host without a display, start both browser MCP servers with
`--headless`. Pass Chrome flags to the Chrome DevTools server joined with `=`
(`--chrome-arg=--no-sandbox`): a separate `--chromeArg --no-sandbox` is parsed
as an empty flag list (chrome-devtools-mcp 1.10.1).

## Backend specifics

- **Module frame.** A backend module renders inside `#typo3-contentIframe`.
  A locator, a text read or an axe scan on the top page does not see its DOM
  (`e2e-testing.md`, *Common Pitfalls*).
- **Sudo mode.** The four maintenance modules (Maintenance, Settings, Upgrade,
  Environment; *Admin Tools* in TYPO3 12 and 13, *System* in 14) ask for the
  password again, and only a system maintainer reaches them. The dialog is a
  modal in the **top** document, not inside the module frame; it appears
  asynchronously. Selectors and a wait that handles both cases:
  `e2e-testing.md`, *Common Pitfalls*. Fill it from the environment, like the
  login.
- **Screenshots below the fold.** A full-page screenshot stops at the outer
  frame, so module content below the first viewport is missing. Raise the
  viewport height to at least the module document's `scrollHeight` (read inside
  `#typo3-contentIframe`) plus the backend header. Compare the image height with
  the height you meant to capture, not with the viewport: a viewport screenshot
  is always exactly as tall as the viewport. The `typo3-docs` skill
  (`references/screenshots.md`) owns the screenshot rules.

## Typical checks

- **Content element backend preview.** Open the Page module on a page that
  holds the element. The preview renders inside the module frame. Check that it
  shows the element's content, no raw Fluid (`{f:` or `{data.`) and no
  exception, then take a screenshot with a raised viewport.
- **Backend module.** HTTP 200, no console error, every view of the module
  opened once (`backend-module-render-verification.md`).
- **Frontend page.** No console error, no failed asset request, the change
  visible with realistic content, in each language the change touches.

## The report

State the URL, the instance (local, staging, production) with its TYPO3
version, what was checked, the measured result and the screenshot path. A
check that could not run is reported as not run, with the reason.
