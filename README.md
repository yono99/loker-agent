# loker-agent

Multi-platform Indonesian job agent: **scrape ? match CV ? auto-apply**.

Scans Glints and Kalibrr (via their own public/mobile APIs), scores each job against
your CV, then optionally auto-applies to the best matches ? with confirmation
before sending anything.

> ?? **Risk disclosure**: Automating applications violates the terms of most job
> boards and your account may be limited/banned. Use at your own risk and with moderation.
> By default, `safe_mode` is ON and the tool does dry-run matching until you pass `--apply`.

## Features
- **Glints** ? search + one-tap auto-apply through the same GraphQL/REST API the Android app uses.
- **Kalibrr** ? search + auto-apply via the jobseeker API (needs cookie + KB-CSRF).
- **JobStreet** ? search API is unstable; see [JobStreet adapter notes](#jobstreet) for a Selenium-based path.
- **CV parsing** ? PDF / DOCX / TXT ? skills + profile for matching.
- **Offline matcher** ? deterministic keyword/skill scoring (no API needed). Optional LLM scoring via xAI Grok (`XAI_API_KEY`).
- **Reports** ? SQLite DB + HTML report.

## Setup
```
pip install -r requirements.txt
cp config.example.json config.json
```
Edit `config.json` with your credentials and `cv.path`.

Run a match-only scan (dry run):
```
python run.py --cv path/to/CV.pdf --platforms glints,kalibrr
```

Run with auto-apply (asks confirmation per job):
```
python run.py --cv path/to/CV.pdf --apply
```

Fully automatic (no confirmation):
```
python run.py --cv path/to/CV.pdf --apply --force-apply
```

## JobStreet
JobStreet actively blocks headless scraping and its search API key changes
frequently, so the built-in adapter raises `NotImplementedError` rather than
send broken requests. If you need JobStreet scraping, see the reference
implementation:
- bahrul-dev/jobstreet-scraper (Selenium + CDP)
- aldrin112602/JobCraft

You can feed its scraped results in via the `--from-csv` extension or a custom adapter.
