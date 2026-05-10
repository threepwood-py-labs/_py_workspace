# Workspace Ideas Backlog

Consolidated from the former top-level `YEAHHHHHH.md`.
This is an intentionally speculative backlog of cross-app ideas and experiments.

---

## many-panelz-explorer

### Quality of Life
- **Batch rename with live preview** — regex/template-based rename (e.g. `{name}_{date}`, `01_{name}`) with a side-by-side before/after table before committing
- **Inline file tagging** — add emoji or short text tags to files/folders, stored in a sidecar `.mpe-tags` file, visible as colored dots in the file list
- **Jump-to-letter** — type a letter while the file list is focused to jump to first matching filename (like classic Explorer)
- **Pinned folders sidebar** — a narrow collapsible left strip of pinned folder shortcuts, drag-to-reorder, one click to navigate any panel
- **Smart "Open With" history** — track which app was last used to open each extension, surface it as the top item in the context menu
- **Undo/redo stack for file ops** — show a small toast after copy/move/delete with an Undo button (5-second window)

### Panel & Tab Enhancements
- **Dual-panel sync mode** — lock two panels so they mirror each other's navigation; great for compare/diff workflows
- **Tab color labels** — right-click a tab to assign a color, useful for "this tab is the source, that one is the destination"
- **Drag tab between panels** — drag a tab out of one panel strip into another
- **Tab thumbnails on hover** — tiny folder icon + path tooltip on hover instead of just the folder name
- **"New tab here" from context menu** — open a subfolder in a new tab without navigating away from the current one

### Power Features
- **Folder size column** — on-demand recursive size calculation per row, runs in background, fills in as it completes
- **Duplicate finder shortcut** — right-click selected files → "Find duplicates in this panel" — opens video-duperz or a lightweight hash-compare view
- **Compare folders** — select two folders across panels, highlight files present in one but not the other (like WinMerge folder compare)
- **Quick filter bar** — Ctrl+F activates a live name filter above the file list, hides non-matching rows, Esc clears
- **Checkboxes selection mode** — toggle a mode where every row shows a checkbox, enabling selection without holding Ctrl
- **"Drop zone" panel** — designate one panel as a drop target; files dropped anywhere on the window go there

### Integrations
- **git-statuz integration** — if a folder is a git repo, show branch name + dirty indicator in the tab title
- **Send to many-panelz-explorer** — Windows Shell "Send To" extension to open any folder in a new tab
- **Custom toolbar scripts** — bind a Python script to a toolbar button; selected files are passed as arguments

---

## arr-helper-ui

### Sonarr UI
- **Bulk season monitor/unmonitor** — select multiple seasons across multiple series and toggle monitored in one click
- **"Missing episodes" quick view** — a flat list of all unmonitored + missing episodes across all series, sortable by age
- **Quality upgrade indicator** — highlight episodes where a better quality is available to download (cutoff not met)
- **Series poster grid view** — toggle between tree view and a poster grid (artwork from Sonarr API) for visual browsing
- **Activity feed tab** — live-updating Sonarr queue/history feed showing recent downloads, failures, and grabs
- **Episode notes** — attach a short personal note to any episode ("watched with X", "skipped — recap episode")
- **Watched progress bar** — if Plex/Jellyfin integration is added, show a watched % bar per series

### Media Checker
- **Scheduled check mode** — built-in scheduler (cron-style) so it runs automatically without Windows Task Scheduler
- **Language policy editor** — GUI to configure which audio/subtitle combos are required (not hardcoded to English)
- **Check result dashboard** — persistent history of checker runs: when it ran, how many files checked, how many failed, what was deleted
- **"Simulate" dry-run with diff** — show exactly what would be deleted/searched without doing it, formatted as a readable report
- **Notification support** — Windows toast notification when the checker finishes or finds failures

### Shared
- **Dark/light theme toggle** — inherit from threep-commons theming when that gets built out
- **Connection profile switcher** — quickly switch between multiple Sonarr/Radarr server profiles (home, remote, VPN)

---

## git-statuz

### Viewing
- **Blame view** — click any file to see per-line git blame with author + commit SHA, colored by age
- **File history timeline** — visual bar chart of commits touching a selected file over time
- **Branch comparison** — pick two branches, see the diff summary (files changed, insertions, deletions)
- **Stash browser** — list stashes with message/date, preview diff, pop/drop from UI
- **Tag list panel** — show all tags with date, tagger, and linked commit; open in history
- **Search commits** — Ctrl+F to filter history by message, author, or file path

### Actions (cautious expansion)
- **Stage/unstage from UI** — checkbox column in status tree to stage/unstage individual files
- **One-click discard** — right-click an unstaged file → Discard Changes (with confirmation)
- **Commit panel** — simple commit message box + commit button for staged files; keep it minimal
- **Branch switcher** — dropdown of local branches, click to checkout (with dirty-check warning)

### UX
- **Keyboard navigation for everything** — full keyboard flow: Tab between panels, Enter to open diff, arrow keys in tree
- **"Open in terminal here"** — right-click repo root → open PowerShell/terminal at that path
- **Recent repos as jump list** — Windows taskbar jump list populated with recent repositories
- **Auto-refresh on file change** — watch repo `.git/index` for changes and auto-refresh status without manual refresh
- **Side-by-side diff view** — optional split diff (old left / new right) instead of unified diff

---

## mp3gain-gui-py

### File Handling
- **Drag and drop folders** — drag a whole music folder into the window, auto-expand to all MP3s recursively
- **Playlist import** — load an M3U/M3U8 playlist to populate the file list automatically
- **File format expansion** — FLAC via metaflac, Ogg Vorbis via vorbisgain, MP4/M4A via aacgain (optional backends)
- **Persistent file list** — remember the last loaded file list between sessions (opt-in)
- **Exclude patterns** — ignore files matching a glob (e.g. skip `*_intro.mp3`)

### Analysis & Gain
- **Target level configurator** — slider/spinner in settings to change the ReplayGain target (default 89 dB, allow 85–95)
- **Clipping warning column** — flag files where applying gain would cause clipping, show recommended safe gain
- **Gain history per file** — store a log of what gain was applied and when, viewable per file
- **Pre-gain EBU R128 check** — compute integrated loudness (LUFS) alongside ReplayGain for broadcast compliance
- **Album grouping by folder** — auto-detect album groups by parent folder for album-mode analysis

### UX
- **Progress ETA** — when processing large batches, show estimated time remaining based on current throughput
- **Sound preview** — double-click a file to play a short preview using the system audio player
- **Export report** — save analysis results as CSV (filename, track gain, album gain, clipping risk)
- **Color-coded gain column** — green if gain is near target, yellow if mild, red if clipping risk

---

## pdf-search-downloader-ui

### Search
- **Multi-query batch mode** — paste a list of search terms (one per line), run them all sequentially overnight
- **Search history panel** — persistent log of past searches with result counts and download stats
- **Advanced query builder** — GUI for site:, daterange:, filetype: combinations without typing raw search syntax
- **Domain whitelist/blacklist** — only download from trusted domains or skip known spam/redirect farms
- **Language filter per query** — set a different language/market per query in batch mode

### Download Management
- **Download queue with retry** — automatic retry (configurable attempts + delay) for failed downloads
- **Duplicate smart merge** — when the same PDF is found at multiple URLs, keep the best one (largest filesize wins)
- **Pre-download PDF preview** — fetch the first page of a PDF URL and show a thumbnail before queueing for download
- **Filename templating** — configure downloaded filename patterns: `{query}_{domain}_{date}.pdf`
- **Post-download OCR tagging** — run tesseract on downloaded PDFs in background and store extracted text in SQLite for local search

### UX
- **Session save/resume** — save an in-progress search session to disk, resume after restart
- **Result review mode** — show results as cards with URL + domain before auto-downloading, let user approve/reject
- **Notification when batch finishes** — Windows toast with download count + any failures
- **Stats dashboard** — total PDFs downloaded, by domain, by query, over time — simple bar charts

---

## prowlarr-ui

### Search
- **Search history with re-run** — every search is logged; one click to re-run a previous search
- **Saved advanced filters** — save complex filter combinations (category + indexer + size range + age) as named presets
- **Size range filter** — min/max file size filter in the results table
- **Age filter** — "only show releases from the last N days" slider
- **Language/group filters** — filter by release group or language tag parsed from release title
- **Negative keywords** — exclude releases containing certain words (e.g. exclude "CAM", "HDCAM")

### Results
- **Release comparison mode** — select multiple releases for the same title, see them side by side (quality, size, seeders, indexer)
- **Auto-select best** — "grab best quality" button that picks the top result by quality score automatically
- **Magnet preview** — hover a result to see parsed quality details without clicking
- **Result grouping by parsed title** — auto-group results that resolve to the same movie/show title (like prowlarr's native grouping)

### Integrations
- **Send to qBittorrent directly** — add a "Send to qBiremo" action that pushes the magnet/torrent to qbiremo-enhanced via its API
- **Send to Sonarr/Radarr** — "Add to Sonarr" / "Add to Radarr" context menu actions for TV/movie releases
- **Everything integration for more than dupes** — show local path alongside dupe detection (where is this already on disk?)
- **Webhook on grab** — fire a configurable webhook when a release is grabbed (for logging, notification, automation)

### UX
- **Keyboard macro for common flows** — press a single key sequence to search → filter → grab top result
- **Compact/dense result rows** — toggle between normal and ultra-compact row height for power users

---

## qbiremo-enhanced

### Torrent Management
- **Auto-rules engine** — "if torrent matches X (name pattern, category, tag, tracker) then do Y (move, tag, set limit, remove seed ratio)" — like autobrr rules but inside the client
- **Seed ratio profiles** — named profiles (e.g. "public trackers: stop at 2.0", "private: seed forever") assignable per category/tracker
- **Torrent notes** — attach a free-text note to any torrent, visible in the details tab
- **Bulk metadata edit** — select multiple torrents and change category, tags, save path, or limits in one operation
- **Content pre-view before add** — when adding a torrent file, show the file tree with sizes before confirming

### Analytics & Reporting
- **Per-tracker stats** — uploaded/downloaded totals per tracker over time, ratio graph
- **Top uploaders leaderboard** — which trackers/categories contributed most to your ratio this month
- **Disk usage breakdown** — pie chart of disk usage by category/save path
- **Download speed heatmap** — 24h × 7d grid showing when your speeds are fastest (helps schedule batch downloads)
- **Session export** — export a CSV of all completed torrents with hashes, sizes, trackers, completion dates

### UX
- **Global speed limit schedule** — set time-of-day speed profiles (e.g. unlimited at night, 1 MB/s during work hours)
- **Tray icon with mini-stats** — hover the tray icon to see current DL/UL speed + active torrent count
- **Notification on torrent complete** — Windows toast when a monitored torrent finishes
- **Quick-add from clipboard** — detect magnet links in clipboard and show a "Add torrent?" toast automatically
- **Rename torrent display name** — rename the display name of a torrent in the UI without touching the save path

---

## video-duperz

### Detection
- **Audio fingerprinting** — use fpcalc (Chromaprint) to detect duplicates that differ in video quality but share the same audio track
- **Scene-hash mode** — instead of evenly spaced frames, sample at detected scene changes for more accurate comparison
- **Partial duplicate detection** — find videos that are clips/segments of a longer file (one is a subset of the other)
- **Custom similarity fine-tuning** — per-scan slider for threshold instead of only three named profiles
- **Multi-pass mode** — first pass finds obvious dupes fast, second pass runs deeper analysis only on borderline matches

### Decision Making
- **Side-by-side video preview** — play both videos in a split mini-player before deciding which to keep
- **AI-assisted keep recommendation** — use a simple ML scorer (resolution × bitrate × codec × HDR weight) with user-configurable weights
- **"Trust me" auto-clean mode** — for clear-cut duplicates (score > 0.95), auto-select keep candidate and queue for deletion without manual review
- **Group actions by rule** — "for all groups where one file is in folder X and the other in folder Y, keep the X one"
- **Soft-delete recycle** — move dupes to a quarantine folder instead of deleting; run a cleanup job after N days

### UX
- **Scan comparison across runs** — show new duplicates found since last scan (delta view)
- **Progress notifications** — Windows toast when a long scan finishes
- **Saved decision profiles** — "always keep highest resolution", "always keep newest", etc. — one-click apply to all groups
- **Export to Radarr/Sonarr** — if a dupe matches a library entry, flag it for arr-helper-ui to handle

---

## web-pagez-to-pdf

### Capture
- **URL-to-capture mode** — type/paste a URL, the app opens it in a controlled headless browser and auto-captures (the CDP roadmap item, built out fully)
- **Batch URL capture** — paste a list of URLs, capture them all overnight into a single export or separate files
- **Scheduled capture** — capture the same page every day/week at a set time (great for archiving dashboards or reports)
- **Browser extension companion** — a tiny browser extension with a "Capture with web-pagez-to-pdf" button that sends the current URL to the desktop app
- **Region capture** — draw a rectangle on screen to capture only that region instead of the full window

### Editor
- **Annotation tools** — draw arrows, boxes, highlight regions, add text labels on captured pages before export
- **Page reorder drag-and-drop** — drag pages in the session queue to reorder before export
- **Merge sessions** — combine multiple sessions into one export in any order
- **Auto-crop whitespace** — detect and strip uniform-color borders (white margins) from captured screenshots automatically
- **Watermark/stamp** — add a configurable text or image watermark to exported PDFs (e.g. "CONFIDENTIAL", date stamp)

### Export
- **Export to OneNote/Notion** — send pages directly to a OneNote section or Notion page via API
- **Compress before export** — optional JPEG compression pass for images embedded in PDF to reduce file size
- **OCR layer in PDF** — run tesseract on exported pages and embed a searchable text layer in the PDF output
- **Named export profiles** — save a full export config (format, paper size, margins, header/footer template) as a named preset
- **Email export** — send the exported file directly via MAPI to a configured email address

---

## threep-commons (shared library)

### New Utilities
- **Theming API** — a `ThemeProvider` that all apps can use for consistent dark/light/accent theme switching, stored in shared settings
- **Notification helper** — `threep_commons.notifications.toast(title, body)` wrapping Windows toast API; all apps get consistent notifications in one line
- **Cross-app IPC bus** — lightweight named-pipe or local TCP message bus so apps can communicate (e.g. prowlarr-ui sends a magnet to qbiremo-enhanced)
- **Crash reporter** — `threep_commons.crash.install_handler()` captures unhandled exceptions, writes a structured crash log, optionally shows a "copy to clipboard" dialog
- **Update checker** — `threep_commons.updates.check(repo, current_version)` pings GitHub releases API and returns if a newer version is available
- **Telemetry-free analytics** — local-only usage counter (how many times each feature is used) for personal decision making, no network calls

### Improvements
- **Settings schema versioning** — add migration helpers so apps can evolve their settings format without losing user data
- **Subprocess streaming** — async subprocess runner that yields output lines as they come, for long-running tools
- **Windows dark mode detection** — detect system dark/light preference and expose as a signal so apps can react at runtime
- **App lockfile** — prevent two instances of the same app from running simultaneously with a clear "already running" dialog

---

## _py_template

### Template Improvements
- **`project_kind = cli_app`** — third mode for pure CLI tools (no PySide6, no pytest-qt, adds rich/typer, different CI profile)
- **GitHub issue templates** — auto-generate `.github/ISSUE_TEMPLATE/` with bug report and feature request forms
- **CHANGELOG.md stub** — include a `CHANGELOG.md` with Keep a Changelog format as part of every new project
- **Dependabot config** — generate `.github/dependabot.yml` to keep GitHub Actions pinned versions fresh
- **PR template** — `.github/pull_request_template.md` with a standard checklist (tests pass, ruff clean, types pass)
- **Drift detection workflow** — as discussed in [audit-2026-03.md](audit-2026-03.md), a scheduled GH workflow that checks child projects against template standards

---

## Cross-App Ideas (the Fun Stuff)

- **Workspace launcher** — a single tray app that shows all installed workspace apps with launch buttons, version numbers, and update badges. Like a personal app store.
- **Shared clipboard bus** — all apps write notable "outputs" (downloaded file path, grabbed magnet, captured PDF path) to a shared clipboard ring accessible from any app
- **"Send to" between apps** — right-click in any app to send context to another (e.g. many-panelz-explorer → send folder to video-duperz for scanning; prowlarr-ui → send magnet to qbiremo-enhanced)
- **Unified dark mode** — one setting in threep-commons that all apps read and react to at runtime, including system dark mode sync
- **Workspace settings app** — a single settings UI for all shared preferences (theme, app paths, tool locations, API keys) stored in threep-commons config
- **"What's running" tray** — a combined tray icon showing active operations across all apps (current scan in video-duperz, active download in pdf-search-downloader-ui, etc.)
