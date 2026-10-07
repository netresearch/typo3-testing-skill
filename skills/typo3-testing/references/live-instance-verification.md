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
| Click through the backend or frontend, acceptance screenshots, logged in | `typo3-browser` skill: login from its project config without the password in the context, module frame, sudo mode, a few lines of output per step |
| Console errors, network requests, computed CSS, Lighthouse | Chrome DevTools MCP (`browser-testing-with-devtools` skill) |
| Ad-hoc interaction without a TYPO3-aware tool | Playwright MCP; every step returns a page snapshot, and a typed password stays in the transcript |
| A check that must keep passing | A Playwright spec (`e2e-testing.md`) |
| Status code, headers, a redirect | `curl` |

On WSL or another host without a display, both browser MCP servers need
`--headless`, and the Chrome DevTools server also needs
`--chromeArg --no-sandbox`; without them the browser often does not start.

## Backend specifics

- **Module frame.** A backend module renders inside `#typo3-contentIframe`.
  A locator, a text read or an axe scan on the top page does not see its DOM
  (`e2e-testing.md`, *Common Pitfalls*).
- **Sudo mode.** Admin Tools ask for the password again (TYPO3 13.4 and 14.3).
  The dialog is a modal in the **top** document, not inside the module frame:
  `.modal-sudo-mode-verification` holds the form `#verify-sudo-mode` with the
  field `#password`, and the button named `verify` submits it
  (`Build/Sources/TypeScript/backend/security/element/sudo-mode.ts`,
  v13.4.35 and v14.3.7). Fill it from the environment, like the login.
- **Screenshots below the fold.** A full-page screenshot stops at the outer
  frame, so module content below the first viewport is missing. Raise the
  viewport height instead, then check the image height: a file exactly as tall
  as the viewport means the capture was cut. The `typo3-docs` skill
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
