from __future__ import annotations

import argparse
import os
import sys
from typing import List

from .apply import ApplicationEngine, GlintsApplier, KalibrrApplier
from .config import Config
from .cv_parser import CVProfileParser
from .database import Database
from .matchers.engine import MatcherFactory
from .models import ApplicantProfile, MatchResult
from .scrapers import GlintsScraper, KalibrrScraper


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="loker-agent", description="Multi-platform Indonesian job agent")
    p.add_argument("--config", default="config.json", help="path to config.json")
    p.add_argument("--cv", default=None, help="path to CV file (PDF/DOC/TXT) or profile JSON")
    p.add_argument("--platforms", default=None, help="comma-separated: glints,kalibrr,all")
    p.add_argument("--keywords", default=None, help="comma-separated search keywords override")
    p.add_argument("--apply", action="store_true", help="run auto-apply (otherwise dry-run match only)")
    p.add_argument("--force-apply", action="store_true", help="apply without confirmation")
    p.add_argument("--output", default=None, help="write HTML report to this file")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    cfg = Config.load(args.config)

    # ---- profile ----
    parser = CVProfileParser()
    cv_path = args.cv or cfg.cv_path
    if cv_path and cv_path.lower().endswith((".json", ".yaml", ".yml")):
        import json
        with open(cv_path, "r", encoding="utf-8-sig") as fh:
            profile = parser.from_structured(json.load(fh))
    elif cv_path:
        profile = parser.parse_file(cv_path)
    else:
        print("Provide --cv or set cv.path in config.json to build a matching profile.")
        return 1

    keywords = args.keywords.split(",") if args.keywords else cfg.keywords

    # ---- scraper selection ----
    from .scrapers import (
        DeallsScraper,
        GlintsScraper,
        IndeedScraper,
        KalibrrScraper,
        KarirhubScraper,
        KitaLulusScraper,
        LinkedInScraper,
    )

    platforms = cfg.enabled_platforms
    if args.platforms:
        platforms = [x.strip() for x in args.platforms.split(",") if x.strip()]

    db = Database(os.path.join(cfg.db_dir, "loker.db"))
    scrapers = {}
    for plat in platforms:
        if plat == "glints":
            scrapers["glints"] = GlintsScraper(cfg)
        elif plat == "kalibrr":
            scrapers["kalibrr"] = KalibrrScraper(cfg)
        elif plat == "linkedin":
            scrapers["linkedin"] = LinkedInScraper(cfg)
        elif plat == "kitalulus":
            scrapers["kitalulus"] = KitaLulusScraper(cfg)
        elif plat == "dealls":
            scrapers["dealls"] = DeallsScraper(cfg)
        elif plat == "indeed":
            scrapers["indeed"] = IndeedScraper(cfg)
        elif plat == "karirhub":
            scrapers["karirhub"] = KarirhubScraper(cfg)

    matcher = MatcherFactory.build(cfg.xai_api_key, cfg.llm_base_url)
    all_results: List[MatchResult] = []

    for plat, scraper in scrapers.items():
        for keyword in keywords:
            for location in cfg.locations:
                try:
                    jobs = scraper.search(keyword, location)
                except Exception as exc:  # noqa: BLE001
                    print(f"  [{plat}] search '{keyword}' @ {location} failed: {exc}")
                    continue
                db.upsert_jobs(jobs)
                print(f"  [{plat}] {keyword} @ {location}: {len(jobs)} jobs")
                for job in jobs:
                    res = matcher.match(job, profile)
                    db.save_match(job.fingerprint(), res.scores, res.verdict, res.reason)
                    all_results.append(res)

    # ---- report ----
    if args.output:
        _write_report(cfg, args.output, all_results)

    candidates = [r for r in all_results if r.verdict == "apply"]
    print(f"\nTotal matched: {len(all_results)} | candidates to apply: {len(candidates)}")
    print("Top candidates:")
    for r in sorted(candidates, key=lambda x: x.scores.overall, reverse=True)[:15]:
        print(f"  [{r.job.platform}] {r.scores.overall:5.1f}  {r.job.title} @ {r.job.company}  {r.reason}")

    # ---- apply ----
    if args.apply and candidates:
        appliers = []
        if "glints" in platforms:
            appliers.append(GlintsApplier(cfg))
        if "kalibrr" in platforms:
            appliers.append(KalibrrApplier(cfg))
        engine = ApplicationEngine(cfg, db, appliers, dry_run=False)
        if args.force_apply:
            engine.config._data["apply"]["confirm_before_apply"] = False
        applied = engine.apply(candidates)
        print(f"\nApplied: {len(applied)}")
    elif args.apply:
        print("\nNo candidates above threshold to apply.")
    db.close()
    return 0


def _write_report(cfg, path, results):
    import html as _html
    rows = []
    for r in sorted(results, key=lambda x: x.scores.overall, reverse=True):
        rows.append(
            f"<tr><td>{_html.escape(r.job.platform)}</td><td>{_html.escape(r.job.title)}</td>"
            f"<td>{_html.escape(r.job.company)}</td>"
            f"<td>{_html.escape(r.job.location)}</td><td><b>{r.scores.overall:.1f}</b></td>"
            f"<td>{_html.escape(r.verdict)}</td><td>{_html.escape(r.reason)}</td></tr>"
        )
    html = (
        "<html><head><meta charset='utf-8'><title>Loker Agent Report</title></head><body>"
        "<h1>Loker Agent Report</h1><table border=1 cellpadding=6>"
        "<tr><th>Platform</th><th>Title</th><th>Company</th><th>Location</th>"
        "<th>Score</th><th>Verdict</th><th>Reason</th></tr>"
        + "".join(rows)
        + "</table></body></html>"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
