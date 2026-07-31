# Comparative Analysis of the LLM-Generated Zerodha Dashboards

**Review date:** 23 July 2026  
**Scope:** Current contents of `/Users/mchanglani/Documents/Zerodha_dashboards`  
**Candidates:** Gemini, Claude Code (`opus1`), Copilot Opus (`opus2`), Codex, and Antigravity

## Executive summary

There is no single winner across every dimension:

- **Codex is the best small, maintainable foundation.** It has the cleanest ratio of useful functionality to code, uses the correct separate Kite mutual-fund API, persists snapshots, and has clear module boundaries. Its family history chart and “first buy date” feature are materially incorrect, however, and it has no tests or application authentication.
- **Claude Code has the broadest and most production-shaped design.** It is the only candidate with a substantial relational model, migrations, authentication, encryption, a componentized frontend, and a large test suite. The current backend nevertheless cannot start: it has missing dependencies, two conflicting `auth_bp` definitions, and registers the same blueprint twice. Its Indian mutual-fund and purchase-date claims are also not implemented.
- **Copilot Opus produces the strongest ready-to-show demo.** It ran successfully and has the richest visual presentation, responsive layouts, sorting, filtering, family toggles, and dedicated mutual-fund and fixed-deposit pages. It is not safe or financially reliable enough for real use: APIs are unauthenticated, several analytics are fabricated or mislabeled, a bank stock is classified as a mutual fund, and matured FDs continue compounding past maturity.
- **Antigravity has the most modern React aesthetic and useful Excel-import ideas.** Its server-side session design can leak data between concurrent users, uploaded portfolios are globally readable/overwriteable, several screens silently mix live and mock data, and the interface has almost no mobile or accessibility treatment.
- **Gemini is the best rapid prototype.** In only 310 lines it creates a useful set of charts and filters with sensible basic P&L calculations. Its claimed 12-hour automation is only a passive Streamlit cache, its request-token flow cannot survive normal Kite token lifecycles, and it does not actually fetch Coin mutual funds.

The scores below assess the **current artifacts**, not the inherent capability of the underlying models. They should not be treated as a scientific LLM benchmark: the prompts, generation time, tool access, and amount of later human/agent iteration were not controlled.

| Current artifact | Requirement fit (20) | Financial correctness (20) | UX and visual design (15) | Architecture (15) | Security (15) | Reliability/testing (10) | Accessibility/responsive (5) | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Codex | 15 | 11 | 9 | 13 | 7 | 6 | 3 | **64** |
| Claude Code / opus1 | 16 | 11 | 12 | 11 | 7 | 3 | 3 | **63** |
| Gemini | 11 | 10 | 11 | 8 | 7 | 5 | 3 | **55** |
| Copilot Opus / opus2 | 15 | 6 | 14 | 7 | 2 | 6 | 2.5 | **52.5** |
| Antigravity output | 14 | 7 | 13 | 8 | 2 | 4 | 1.5 | **49.5** |

These totals are intentionally close where tradeoffs differ. For example, Claude Code is far more complete than Codex, but its current backend is unusable; Opus2 is much more polished than Gemini, but its financial claims are less trustworthy.

## Attribution and fairness caveat

Repository history identifies the original additions as:

- `a5d392a`: “Added Gemini dashboard”
- `b6b7573`: “Added Claude code dashboard”
- `3e1f697`: “Added Copilot opus dashboard”
- `6a015f3`: “Added Codex dashboard”
- `2e30362`: “Added ANTIGRAVITY dashboard”

The repository does not identify Antigravity’s underlying model, so this report calls it the **Antigravity output**, not a specific LLM.

The Claude Code directory was subsequently expanded by many commits, especially the bank-balances work. Its current 23,184 source lines are therefore not a like-for-like one-shot output beside Gemini’s 310 lines or Codex’s 692. This report evaluates what exists now and flags that attribution limitation instead of crediting every later change to the initial generation.

## Methodology

The review covered:

- Repository history and attribution
- Architecture and dependency manifests
- All first-party Python, JavaScript, JSX, Vue, CSS, and HTML source
- Authentication, credential handling, file uploads, data ownership, and API exposure
- Zerodha/Kite data semantics and financial calculations
- UI structure, responsive rules, accessibility hooks, and demo/live-data labeling
- Builds, compilation, linting, tests, and local runtime behavior where available

Current first-party size, excluding dependencies, build artifacts, worktrees, and caches:

| Candidate | Source files | Source lines | Test files | Documentation files |
|---|---:|---:|---:|---:|
| Antigravity | 14 | 1,822 | 0 | 1 |
| Gemini | 2 | 310 | 0 | 0 |
| Claude Code / opus1 | 109 | 23,184 | 13 | 22 |
| Copilot Opus / opus2 | 6 | 4,875 | 0 | 0 |
| Codex | 8 | 692 | 0 | 1 |

Validation performed:

- All Python candidates passed bytecode compilation.
- Claude Code’s Vue frontend built successfully: 453 modules transformed and a production bundle emitted.
- Claude Code’s backend test run stopped during collection because its local environment lacks `flask_jwt_extended`. Further startup probing found an undeclared `finnhub` dependency and then confirmed a fatal duplicate-blueprint registration.
- Claude Code contains 202 Python tests, but they could not be rerun against the current tree. Its stored pytest cache shows one prior failure, which is historical evidence only.
- Claude Code’s backend produced 445 flake8 findings. Most are formatting issues, but the results also include two undefined `logger` references, redefinitions, and unused code.
- Opus2 started successfully. Its three pages and four inspected portfolio APIs all returned HTTP 200.
- Antigravity’s server JavaScript passed `node --check`; its frontend build and lint commands could not run because dependencies are not installed in that directory.
- Gemini’s demo generator and Codex’s SQLite history logic were executed directly with isolated data.
- No real brokerage credentials were used. This avoided accessing or modifying an actual portfolio.
- Visual judgments are based on the served HTML plus complete CSS/component inspection. No browser screenshot or formal assistive-technology audit was available.

The Kite-specific conclusions were checked against official documentation:

- `/portfolio/holdings` is for long-term equity delivery holdings, while mutual funds have a distinct `/mf/holdings` endpoint: [portfolio documentation](https://kite.trade/docs/connect/v3/portfolio/) and [mutual-fund documentation](https://kite.trade/docs/connect/v3/mutual-funds/).
- `kite.trades()` returns executions for the current day, not a historical tradebook: [orders and trades documentation](https://kite.trade/docs/connect/v3/orders/).
- Quote `ohlc.high` and `ohlc.low` are today’s high and low, not 52-week values: [market quote documentation](https://kite.trade/docs/connect/v3/market-quotes/).
- A `request_token` is a one-time, minutes-lived exchange token; an ordinary access token expires at 6 AM the next day: [authentication documentation](https://kite.trade/docs/connect/v3/user/).

## Requirement-level comparison

The apparent core goal is a family dashboard covering Indian stocks and mutual funds, aggregate and per-account P&L, decision-support views, buy dates, and a 12-hour refresh.

Legend: **Yes**, **Partial**, **No**, or **Demo**.

| Capability | Gemini | Claude Code | Copilot Opus | Codex | Antigravity |
|---|---|---|---|---|---|
| Multiple family accounts | Yes, environment prefixes | Partial; global accounts plus later user model | Yes, config list | Yes, aliases | Partial; one live account, others imported |
| Equity via Kite | Yes | Yes | Yes | Yes | Yes |
| Coin mutual funds via `/mf/holdings` | **No** | **No** | No in live fetch; ETFs inferred from equity | **Yes** | Yes |
| Aggregate family summary | Yes | Yes | Yes | Yes | Yes, but mixes live and mock |
| Account filtering/comparison | Yes | Yes | Yes | Comparison only | Yes |
| Persistent snapshots/history | No | Yes | Cached current JSON only | Yes | No |
| True 12-hour background sync | No; passive cache | Yes in process | Yes in process | Yes in process | No |
| Reliable first-buy date | No | No for Indian equity | Demo-only | No; today’s trades only | No |
| Demo mode | Yes | No clear integrated demo | Yes, explicitly labeled | No | Yes, often implicit |
| App authentication | No | Partial/inconsistent | No | No | Weak Kite session only |
| Automated tests | No | **202 tests** | No | No | No |
| Production build verified | Not applicable here | Frontend only | Server runtime verified | Not applicable here | No dependencies installed |

## 1. Gemini

**Directory:** `zerodha-dashboard-gemini`  
**Stack:** Streamlit, Pandas, Plotly, KiteConnect  
**Size:** 310 source lines

### Strengths

1. **Excellent prototype efficiency.** Two files produce a usable overview, four distinct visualizations, account and asset filters, symbol search, P&L formatting, and a detailed holdings table.

2. **Good basic financial arithmetic.** Invested value, current value, absolute P&L, and P&L percentage are derived transparently and guard against division by zero (`data_fetcher.py:58-65`).

3. **High information density.** The account donut, holding treemap, gain/loss chart, and asset/account sunburst reveal different portfolio relationships without requiring navigation (`app.py:105-147`).

4. **Useful exploratory controls.** Family member, instrument type, and symbol filters make the prototype immediately interactive (`app.py:92-101`).

5. **Graceful first-run experience.** Missing credentials fall back to demo data instead of leaving the page blank.

6. **Honest partial disclosure.** The footer acknowledges that exact buy dates generally require tradebook data (`app.py:173`), even though the implementation still labels another field as buy date.

### Weaknesses

1. **The “automated 12-hour pull” claim is false.** `@st.cache_data(ttl=43200)` only invalidates data when a user causes the function to run again. It does not schedule a background pull, persist a snapshot, or collect history while nobody visits the app (`app.py:46-51`).

2. **The login design fails after the short request-token window.** Every cache miss calls `generate_session()` using the configured `REQ_TOKEN` (`data_fetcher.py:24-33`). Kite documents that a request token is one-time and lives only a few minutes. The generated access token is not persisted, so later refreshes will normally fail.

3. **Coin mutual funds are not fetched.** The implementation only calls `kite.holdings()` and guesses that symbols containing `-G` or `BE` are mutual funds (`data_fetcher.py:56-77`). Kite provides mutual funds separately through `/mf/holdings`. The heuristic can misclassify equities/ETFs and omit actual Coin funds.

4. **“Buy Date” is semantically wrong.** `authorised_date` relates to holdings authorization, not the original purchase. The fallback mock has realistic-looking dates, which makes the live/mock difference easy to miss (`data_fetcher.py:67-85`).

5. **Demo results are unstable.** Random quantities, holdings, prices, and dates are regenerated on a cold cache. Two direct calls in this review returned 20 versus 18 rows and total current values of roughly ₹9.15M versus ₹10.66M. This is undesirable for screenshots, tests, and decision-support comparisons.

6. **Filters do not update the headline metrics.** The four summary cards are calculated from the complete dataframe before sidebar filters are applied. A user selecting one family member sees that member’s charts beneath whole-family totals.

7. **Top/bottom sets can overlap.** With fewer than ten filtered holdings, concatenating the first five and last five can duplicate instruments.

8. **Search is unintentionally regex-based.** `str.contains(search_symbol.upper())` treats user input as a regular expression and does not specify `na=False`.

9. **No historical or risk context.** There are no snapshots, cash-flow adjustments, concentration warnings, benchmark comparisons, or stale-data age checks.

10. **No app-level privacy boundary.** Anyone who can reach the Streamlit service can see all configured family holdings. Environment-based secrets are reasonable for a local prototype, but not sufficient authorization.

11. **No tests or dedicated documentation.** The code compiles, but calculation behavior, Kite response handling, and UI state are unverified.

12. **Accessibility depends heavily on framework defaults.** Plotly and Streamlit provide some baseline behavior, but the custom `unsafe_allow_html` metric cards add no semantic metric structure and use red/green as a primary state cue.

### Best use

A personal, local, throwaway prototype for discovering which charts are useful. It is not a sound base for unattended synchronization or accurate family wealth records without redesigning authentication, mutual-fund ingestion, and persistence.

## 2. Claude Code / opus1

**Directory:** `zerodha-dashboard-opus1`  
**Stack:** Flask, SQLAlchemy, APScheduler, Vue 3, Pinia, Chart.js  
**Current size:** 23,184 source lines, 202 Python tests, 22 documentation files

### Strengths

1. **The strongest product architecture.** It has a real application factory, route/service/model separation, a normalized database, migrations, frontend state stores, reusable components, and a dedicated API client.

2. **By far the broadest feature set.** Current screens cover overview, Indian stocks, mutual funds, US stocks, fixed deposits, bank balances, statements, transactions, analytics, accounts, login, and registration.

3. **Persistent portfolio model.** Snapshots, holdings, time series, sector allocations, historical prices, accounts, and credentials have explicit data models rather than being inferred from one JSON blob.

4. **Best security intent.** Zerodha credentials are Fernet-encrypted before storage (`routes/accounts.py:60-84`), and the later bank-account features use JWT authentication and ownership checks.

5. **Strongest test investment.** There are 202 test functions covering users, JWT flows, bank accounts, statements, PDF parsing, categories, transactions, categorization, and analytics. No other candidate has an automated test suite.

6. **Good frontend engineering.** The Vue build completed successfully, components are reasonably decomposed, API errors are centralized, routes are lazy-loaded, and most major views contain mobile breakpoints.

7. **Good operational intent.** The scheduler prevents overlapping runs with `max_instances=1`, creates snapshots, and continues past a failed individual account (`scheduler_service.py:39-107`).

8. **Best documentation volume.** Setup, feature summaries, quick starts, design notes, and a self-review make the intended behavior discoverable.

9. **The bank statement workflow is ambitious and well modeled.** Upload, parse, review, approve, categorize, learn templates, and analyze transactions form a coherent workflow rather than a visual mock.

### Weaknesses

#### Critical runtime defects

1. **The current backend cannot start.** The local environment first fails on missing `flask_jwt_extended`; after temporarily stubbing missing imports, startup fails on undeclared `finnhub`, then missing `pdfplumber`, and finally on a deterministic blueprint error.

2. **`auth.py` defines `auth_bp` twice.** Lines 14 and 190 create different blueprints with the same name. The second assignment discards the module reference to registration, login, profile, and logout routes.

3. **The application registers `auth_bp` twice.** `app/__init__.py:54` and `:57` register the same final blueprint, producing:

   `ValueError: The name 'auth' is already registered for this blueprint`

   Removing only the duplicate registration would still leave the first set of user-auth routes stranded on the overwritten blueprint.

4. **The route package repeats the auth import and export.** `routes/__init__.py:6,9,15,18` reflects a merge-style assembly error that linting correctly reports.

5. **The dependency manifest is incomplete.** `finnhub_service.py` imports `finnhub`, but `backend/requirements.txt` does not declare `finnhub-python`.

#### Data and financial correctness

6. **The mutual-fund feature is not connected to mutual-fund data.** `KiteService.get_holdings()` only calls `kite.holdings()` and marks every result `instrument_type='equity'` (`kite_service.py:61-104`). There is no `/mf/holdings` ingestion anywhere in the backend. The mutual-fund tab will therefore be empty for normal synced data.

7. **Indian equity buy dates are never populated.** The model has `purchase_date`, but searches found assignments only in the US-stock and fixed-deposit import services. The principal Zerodha sync never supplies it.

8. **Correlation analysis has no ingestion path.** A `HistoricalPrice` model and correlation query exist, but no application service creates `HistoricalPrice` records. Correlation will return an empty matrix unless the database is populated externally.

9. **The heatmap period is cosmetic.** `generate_heatmap_data()` comments that it “would typically fetch historical snapshots” and simply returns current holding values regardless of requested week/month/quarter/year (`analytics_service.py:219-248`).

10. **Return and risk metrics are not cash-flow adjusted.** They treat changes in total portfolio value as investment return. Deposits, withdrawals, buys, sells, and adding an account can be mistaken for performance.

11. **Sector classification is a tiny hard-coded map.** Unrecognized instruments become “Other,” so real diversified portfolios will have misleading allocation data (`scheduler_service.py:224-249`).

12. **Mutual-fund claims in README and project summaries exceed implementation.** This is a recurring LLM weakness: comprehensive documentation was generated from intended architecture, not verified behavior.

#### Security and privacy

13. **Authentication is inconsistent across product areas.** Bank endpoints use `@jwt_required()`, but Zerodha accounts, holdings, sync, analytics, US upload, and FD upload routes do not. The frontend requiring login does not protect the backend.

14. **Zerodha accounts are not scoped in route queries.** The `Account` model has a nullable `user_id`, but `routes/accounts.py` reads and mutates accounts globally. Any API client that can reach the service can list or alter all family accounts and trigger syncs.

15. **Default secrets are unsafe outside development.** Flask and JWT fall back to `dev-secret-key-change-in-production` (`config.py:12,45`) with no production startup guard.

16. **JWTs are stored in `localStorage`.** This is simple but exposes bearer tokens to any successful frontend XSS. The UI also has several non-semantic clickable controls.

#### Quality and UX gaps

17. **Tests exist but current integration is not green.** The test command cannot collect in the present environment, and the fatal startup merge happened despite the suite. This suggests CI or a clean-install smoke test is missing.

18. **Linting reports 445 findings.** Most are line-length/style issues, but important findings include two undefined `logger` references in `transaction_service.py`, repeated definitions, bare exceptions, and unused variables.

19. **Frontend tests are absent.** The Vue production build passes, but critical login, routing, upload, and review workflows have no component or end-to-end coverage.

20. **The visual design is competent but conventional.** The light cards, blue primary actions, tables, and sidebar are consistent and responsive, but less polished and distinctive than Opus2 or Antigravity.

21. **Accessibility is partial.** Form-heavy views often have labels and focus styles, which is better than the other custom frontends. However, icon-only close/edit/delete controls lack accessible names, the user menu is a clickable `div` without keyboard semantics, notifications lack `aria-live`, and several filters lack labels.

22. **The scope is sprawling.** The original dashboard was about portfolio analysis; the current tree also implements bank PDF processing and transaction intelligence. This increases maintenance and makes it harder to know which features are truly complete.

### Best use

The best source of reusable schema, frontend component patterns, bank workflow models, and test cases. It should not be selected as the running baseline until startup, route ownership, dependency, MF ingestion, and current CI failures are fixed.

## 3. Copilot Opus / opus2

**Directory:** `zerodha-dashboard-opus2`  
**Stack:** Flask, server-rendered HTML, vanilla JavaScript, Chart.js  
**Size:** 4,875 source lines across six large source files

### Strengths

1. **Best demo presentation.** It has a cohesive dark financial-dashboard theme, high information density, polished cards, badges, tables, charts, hover states, and transitions.

2. **Rich interaction without a frontend framework.** Family/member toggles, search, sorting, filters, chart tooltips, refresh, drill-down rows, and dedicated asset pages are all implemented in vanilla JavaScript.

3. **Good responsive intent.** All three templates include desktop, tablet, and mobile media queries.

4. **Strong first-run experience.** The checked-in demo dataset makes the entire product immediately explorable, and the pages visibly display a “DEMO DATA” badge.

5. **Broad product thinking.** It includes family portfolio totals, sector views, account comparisons, top movers, mutual-fund purchase tranches, CAGR fields, fixed-deposit progress, net worth, and live Kite login.

6. **Operationally runnable.** The app started successfully, and `/`, `/mutual-funds`, `/fixed-deposits`, `/api/portfolio`, `/api/mutual-funds`, `/api/fixed-deposits`, and `/api/holdings/Primary` all returned HTTP 200.

7. **A useful cache fallback.** It can continue showing the last JSON snapshot when Kite is unavailable.

### Weaknesses

#### Critical data-integrity problems

1. **A real bank equity is classified as a mutual fund.** The MF detector accepts any symbol starting with `ICICI` (`app.py:271-277`). In the running demo, `/api/mutual-funds` returned `ICICIBANK` among six “funds.”

2. **“52-week high/low” is actually today’s high/low.** `data_fetcher.py:99-101` maps quote `ohlc.high/low` into `week_52_high/low`. Official Kite documentation defines those fields as the current day’s extremes.

3. **Forecasted CAGR values are hard-coded, unsourced predictions.** `app.py:279-297` presents symbol-specific forward returns as “Zerodha / analyst consensus,” but they are constants with no data source. These should never drive investment decisions.

4. **The “2Y CAGR” computation is mislabeled.** For holdings older than two years it raises the entire holding-period return to `1/2`, not the return over the latest two-year window (`app.py:359-365`). For holdings younger than two years it is simply since-purchase CAGR.

5. **Matured fixed deposits continue compounding past maturity.** Current value is based on elapsed time since investment with no maturity cap (`app.py:466-484`). At review time four matured demo FDs had current values higher than their own maturity values; for example one showed approximately ₹533K current versus ₹511K at maturity.

6. **The demo cache is stale indefinitely without credentials.** The served snapshot’s `fetched_at` was 3 March 2026 even though review occurred on 23 July 2026. The app does not regenerate demo data when an old cache already exists.

7. **Most “mutual funds” are actually exchange-traded ETFs inferred from equity holdings.** The live fetch does not call `mf_holdings()`. A manually maintained symbol list and suffix/prefix patterns cannot replace the Coin holdings endpoint.

8. **Fixed deposits are demo-only.** There is no upload, CRUD, or bank source for real FDs. Live Kite refreshes cannot populate them.

9. **Day-change percentage uses current value as denominator.** A more conventional portfolio daily return uses prior close value; the current denominator slightly understates positive changes.

10. **No real historical portfolio series.** One JSON snapshot is cached, so there is no audited performance history despite the analytical presentation.

#### Security and engineering

11. **All portfolio APIs are unauthenticated.** The review retrieved full portfolio analytics and member holdings without a session. The server binds to `0.0.0.0` in debug mode (`config.py:39`, `app.py:627`).

12. **The refresh endpoint is unauthenticated.** Any reachable caller can trigger API work and disk writes with `POST /api/refresh`.

13. **Kite callback tokens are process-local.** Login updates `config.FAMILY_MEMBERS[0]` in memory and is lost on restart (`app.py:602-615`). Multi-member authentication is not implemented.

14. **Predictable development secrets.** Flask defaults to `zerodha-dashboard-secret-key-change-me`.

15. **Remote/config values are inserted with `innerHTML`.** Member names, holdings, and other API-derived values are interpolated into HTML and even inline `onclick` strings. A malicious or malformed imported/config value can become an XSS vector.

16. **No authorization boundary between family members.** `/api/holdings/<member_name>` exposes any named member to any caller.

17. **Thread races are possible.** A background thread, request handlers, and refresh endpoint mutate `_cached_data`, `_last_refresh`, and the JSON file without a lock.

18. **The architecture is monolithic.** Three HTML files duplicate large CSS/JavaScript blocks, `app.py` mixes routes with analytics, and `data_fetcher.py` mixes real ingestion with a large hand-authored demo.

19. **No automated tests, dependency lock for Python, or README.** `requirements.txt` uses broad minimum versions, so future installs can drift.

20. **Accessibility is weak.** There are almost no ARIA attributes or explicit labels for search and icon controls; interactive table headers and dynamically generated buttons lack robust keyboard semantics. Color carries much of the gain/loss meaning.

### Best use

A design and interaction reference for a demo or stakeholder walkthrough. Its HTML/CSS should be reused only after separating presentation from data provenance and replacing the financial logic, authentication, and DOM construction.

## 4. Codex

**Directory:** `zerodha-family-dashboard-codex`  
**Stack:** Streamlit, Pandas, Plotly, SQLite, APScheduler  
**Size:** 692 source lines

### Strengths

1. **Best compact architecture.** Configuration, Kite client, synchronization, persistence, analytics, and scheduling are separated into small modules with clear responsibilities.

2. **Correct equity/MF API separation.** It calls `client.holdings()` and `client.mf_holdings()` independently (`zerodha_client.py:14-20`) and normalizes them separately.

3. **Real persistence.** Equity snapshots, MF snapshots, trades, and sync runs are stored in SQLite with primary keys and parameterized SQL.

4. **Useful operational transparency.** The dashboard exposes recent sync logs, includes success/failure status, and has a manual sync action.

5. **No deceptive demo.** If accounts are not configured or no holdings are available, it shows explicit error/empty states instead of silently substituting invented wealth.

6. **Good basic analytics.** Family summary, asset allocation, account profit comparison, winners, losers, holdings details, and a trend chart form a sensible minimum product.

7. **Reasonable configuration model.** Explicit aliases avoid Gemini’s environment-prefix guesswork, and credentials stay out of source.

8. **Good numerical normalization.** Dataframe numeric coercion and zero guards reduce crashes from incomplete API values.

9. **Compilation and isolated datastore behavior were easy to validate.** The small codebase is understandable enough to audit directly.

### Weaknesses

1. **The family history chart is wrong.** Each account receives a slightly different timestamp during sequential sync (`sync_service.py:27-33`). `get_portfolio_history()` groups only by exact `ts` (`data_store.py:181-193`). It therefore produces one point per account, not one family total per sync.

   An isolated two-account test produced points of ₹330 and ₹500. The intended synchronized family value was ₹830. This can create false jumps that look like portfolio performance.

2. **“First buy date” cannot work as claimed.** The sync calls `kite.trades()` (`zerodha_client.py:23-26`), and the official API returns only the day’s trades. Long-held positions will normally have no historical buy record. A tradebook import or another historical source is required.

3. **Silent data loss is reported as success.** `fetch_mf_holdings()` and `fetch_trades()` catch every exception and return empty lists. The sync then records a successful message such as “0 MF, 0 trades” instead of a partial-failure status.

4. **No batch/sync identifier.** Timestamps are being used both as event time and aggregation identity. A dedicated `sync_run_id` shared across accounts and asset types would fix history semantics and improve auditing.

5. **No cash-flow-adjusted performance.** Like other candidates, changes in holdings or contributed capital can distort the trend and winner/loser interpretation.

6. **Scheduler topology is fragile.** APScheduler starts inside the cached Streamlit runtime. Multiple application processes or replicas would each schedule the same job, and there is no distributed lock.

7. **No application authentication.** Anyone who can reach the Streamlit service can view the family portfolio and manually trigger brokerage API calls.

8. **Credentials are plain environment variables.** This is acceptable for a local tool but there is no encrypted credential store, rotation UI, or per-user ownership.

9. **No tests.** The most important history bug would have been caught by a two-account synchronization test.

10. **No package metadata or lock file.** The project relies on manipulating `sys.path` in `app.py` rather than being installable as a normal package, and requirements use unbounded minimum versions.

11. **Limited exploration controls.** There is no account selector, asset filter, date range, search, sortable presentation, or concentration analysis in the Streamlit view.

12. **Visual styling is functional, not refined.** The dark gradient and Plotly views are coherent, but broad CSS rules force text colors on all `div`, `span`, and `label` elements, which can interfere with Streamlit component states.

13. **Accessibility still relies on Streamlit/Plotly defaults.** The four main charts do not have textual equivalents beyond the holdings table, and gain/loss color treatment is not explicitly supplemented everywhere.

### Best use

The best starting backend/data pipeline for a disciplined rewrite. Before adoption, add a shared sync-run ID, tradebook import, partial-failure semantics, authentication, tests, and a more capable UI.

## 5. Antigravity output

**Directory:** `zerodha-dashboard-antigravity`  
**Stack:** React 19, React Router, Recharts, Express, KiteConnect, Multer, SheetJS  
**Size:** 1,822 source lines  
**Attribution note:** The repository identifies Antigravity as the generation environment, not the underlying model.

### Strengths

1. **Most modern visual language.** The dark glass panels, typography, gradients, icons, asset navigation, and restrained animations look more like a contemporary wealth product than a framework demo.

2. **Clear page organization.** Overview, Zerodha, US stocks, and fixed deposits are separate routes with a persistent sidebar and family selector.

3. **Useful family-import concept.** One member can connect to Kite while other members upload holdings spreadsheets. This is pragmatic when not every family member has an API subscription.

4. **The XLSX parser tries to tolerate Zerodha exports.** It scans for delayed header rows, handles equity and MF sheets, detects column variants, and rejects files with no recognized holdings.

5. **Live price enrichment is a good idea.** Imported equity holdings can use the authenticated member’s Kite session to refresh LTP.

6. **React rendering avoids the direct `innerHTML` XSS pattern seen in Opus2’s frontend.**

7. **Tables handle wide datasets with horizontal scrolling.** Numeric formatting is readable and P&L calculations are transparent.

8. **The server source is syntactically valid.**

### Weaknesses

#### Critical security and privacy problems

1. **A single global `KiteConnect` client is shared by every session.** Each request mutates its access token (`server/index.js:41-43,296-301`). Concurrent users can race, causing one user’s request to execute with another user’s token and potentially return the wrong portfolio.

2. **Session IDs use `Math.random()` and a short substring.** This is not a cryptographically secure session identifier (`server/index.js:263-266`).

3. **Request logging prints cookies.** Session IDs are written to logs on every request (`server/index.js:33-37`). The callback also logs the request token.

4. **Imported family portfolios have no ownership.** `importedHoldings` is a global object keyed by caller-controlled member name. Upload and retrieval endpoints are unauthenticated, so callers can overwrite or read another caller’s imported data.

5. **Uploads have no size or MIME limits.** Multer accepts arbitrary files into local storage before parsing. Large or crafted workbooks can exhaust CPU, memory, or disk.

6. **Sensitive sample identity data is hard-coded.** Family names and personal-looking profile values appear in client mock data and server demo data. Even if fictional, this is poor privacy hygiene for a reusable template.

#### Data and product correctness

7. **The overview silently mixes live and fake assets.** Live/imported Zerodha positions are combined with hard-coded US stocks and FDs (`Dashboard.jsx:47-81`). The total net worth can therefore look authoritative while being partly fictional.

8. **The daily change is an estimate built from mismatched concepts.** It applies a percentage to invested value rather than prior-close value and then always adds half a mock daily change (`Dashboard.jsx:103-112`).

9. **The mutual-fund card uses a hard-coded `0.4` day change.** Even when real MF holdings load, the displayed daily change is fake (`Zerodha.jsx:312-317`).

10. **Mock prices change on every module load.** `Math.random()` perturbs all mock assets, hurting reproducibility.

11. **The FX rate is fixed at ₹83.50 per USD.** There is no date/source label or refresh mechanism.

12. **Matured FDs are labeled “Maturing Soon.”** The status test checks only whether maturity is less than 90 days away; negative durations also pass (`FixedDeposits.jsx:34-55`).

13. **No 12-hour sync, snapshot history, or durable import store.** Sessions and imported holdings disappear on restart.

14. **Only one hard-coded member can authenticate with Kite.** The UI decides that `currentMember === 'meher'` gets API connection while other fixed IDs get spreadsheet import.

15. **Excel P&L percentage is mapped to “day change.”** The parser searches for unrealized P&L percentage columns and stores that value in `dayChange` (`server/index.js:121-143`).

16. **All imported equity symbols are queried on NSE.** BSE-only holdings are not retried despite a comment suggesting otherwise (`server/index.js:210-229`).

#### Reliability and UX

17. **No tests and no meaningful README.** The README is the untouched Vite template.

18. **The frontend cannot currently build in-place.** `npm run build` and `npm run lint` fail because `vite` and `eslint` are not installed. A package lock exists, so this is an environment/readiness issue rather than proof of invalid React.

19. **There are no responsive layout rules in the active stylesheet.** The 280px sidebar, desktop topbar, and two-column overview remain fixed on narrow screens. The only media query is in an unused starter `App.css`.

20. **Accessibility is the weakest of the five.** Icon-only buttons lack accessible names, the member selector lacks a label, there is no mobile navigation, focus states are sparse, motion has no active reduced-motion handling, and asset state depends heavily on color.

21. **Components contain extensive inline styles and duplicated table code.** This makes them harder to theme, test, and evolve.

### Best use

A visual and interaction prototype, plus a source of ideas for family spreadsheet import. Do not reuse the session or upload architecture. Rebuild those pieces around per-user clients, cryptographic sessions, authenticated storage, strict upload limits, and explicit data provenance.

## Cross-cutting LLM patterns

### What the generated dashboards do well

1. **Rapid breadth.** Every candidate turns a short financial-dashboard concept into a recognizable product with summary metrics and useful views.

2. **Good visual intuition.** Asset allocation, account contribution, winner/loser tables, treemaps, and trends are generally appropriate dashboard choices.

3. **Reasonable first-run empathy.** Most candidates anticipate missing credentials and provide either a demo or explicit empty state.

4. **Clear basic P&L math.** The common invested/current/P&L calculations are understandable and usually guarded against zero denominators.

5. **Modularization scales with task ambition.** Codex and Claude Code show strong separation of concerns when asked to move beyond a visual mock.

### Recurring weaknesses

1. **Claims are generated before data provenance is verified.** Examples include “52-week” values from daily OHLC, fabricated forward CAGR, “first buy dates” from today’s trades, and mutual-fund screens without `/mf/holdings`.

2. **A timer-like API is mistaken for automation.** Gemini’s cache TTL is not a scheduler; in-process schedulers in the other candidates are not robust multi-process job systems.

3. **Demo and live data are mixed.** Opus2 labels its demo clearly, but Antigravity blends mock US/FD values with live Indian holdings, and Gemini’s realistic random data changes silently.

4. **Financial performance ignores cash flows.** None of the candidates implements time-weighted return, money-weighted return/XIRR, or a robust treatment of contributions, withdrawals, buys, and sells.

5. **Authentication is treated as a frontend feature.** Several implementations hide views behind UI state while leaving APIs global or unauthenticated.

6. **Generated documentation overstates completion.** Claude Code’s README is the clearest example: it describes MF support, correlation, heatmaps, and security more fully than the code supports.

7. **Tests are either absent or fail to protect integration.** Four candidates have no tests; Claude Code has many tests but lacks a passing clean-start smoke test.

8. **Accessibility is an afterthought.** Responsive CSS appears more often than semantic labeling, keyboard behavior, screen-reader announcements, reduced motion, or non-color status cues.

## Recommended synthesis

If the goal is one production-quality family wealth dashboard, the best path is not to select one directory unchanged:

1. **Start with Codex’s small data-layer boundaries** and separate equity/MF normalization.
2. **Adopt Claude Code’s relational schema, migrations, component organization, ownership model for bank data, and test cases.**
3. **Use Opus2’s visual hierarchy and interaction patterns**, but discard its financial forecasting and DOM interpolation.
4. **Use Antigravity’s family Excel-import UX**, rebuilt with authenticated, durable storage and strict parser isolation.
5. **Reuse Gemini’s treemap and sunburst ideas** as optional exploratory views.

### Required remediation order

1. **Define a canonical, provenance-aware data model.** Every number should include source, account, asset class, valuation timestamp, currency, and whether it is live, imported, estimated, or demo.

2. **Implement Kite semantics correctly.**
   - Separate `/portfolio/holdings` and `/mf/holdings`.
   - Use the daily login/access-token lifecycle intentionally.
   - Import historical tradebooks for first-buy dates.
   - Use historical candles for multi-period high/low and return analysis.

3. **Create atomic family sync runs.** Assign one `sync_run_id` to all account fetches and aggregate history by that ID, while preserving partial failures.

4. **Remove invented decision signals.** Eliminate unsourced CAGR forecasts, fake day changes, stale FX constants presented as current, and inferred MF classification.

5. **Secure every API and data object.**
   - Server-side user ownership checks on accounts, holdings, uploads, sync, analytics, and statements
   - Cryptographically secure sessions or carefully managed JWT cookies
   - Encryption for brokerage credentials
   - No secrets, cookies, request tokens, or raw holdings in logs
   - File size/type limits and isolated parsing

6. **Use financially meaningful performance metrics.** Add XIRR/money-weighted and time-weighted returns, distinguish realized/unrealized P&L, track cash flows, and label benchmark assumptions.

7. **Add tests before adding more charts.**
   - Clean-install/startup smoke test
   - Two-account atomic sync and history aggregation
   - Equity versus MF endpoint normalization
   - Token expiry and partial API failure
   - Matured FD valuation cap
   - Authorization/ownership tests for every route
   - Import parser fuzz/size tests
   - Frontend login, filtering, upload, and stale/demo-label tests

8. **Perform a real accessibility pass.** Add semantic labels, keyboard-accessible menus/modals/tables, focus management, `aria-live` notifications, reduced-motion support, non-color cues, and mobile navigation.

## Final verdict

- **Best foundation to continue engineering:** Codex, after correcting sync history and buy-date logic.
- **Best source of enterprise-shaped components and tests:** Claude Code, after a focused stabilization sprint.
- **Best visual reference:** Copilot Opus.
- **Best spreadsheet-import concept and modern React styling:** Antigravity.
- **Best minimal exploratory prototype:** Gemini.

None of the five should currently be trusted for real investment decisions or exposed to a network without remediation. The most important lesson is that visual completeness is a poor proxy for financial correctness: the two most polished candidates contain the most consequential misleading analytics.
