# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2024-XX-XX

### Added
- Initial release of Loker Agent
- Multi-platform job scraping for Glints and Kalibrr
- CV parsing from PDF, DOCX, and TXT files
- Keyword-based job matching engine
- Optional LLM-based matching via xAI Grok
- Auto-apply functionality with safe mode
- SQLite database for job storage and application history
- HTML report generation
- Scheduler for automated scans (daily, weekly, custom intervals)
- Cover letter generator with templates
- CLI with comprehensive options
- Example configuration files (`config.example.json`, `profile.example.json`)
- Unit tests for matching engine
- Basic documentation (README, CONTRIBUTING, LICENSE)

### Platform Support
- Glints: Full support ( + auto-apply)
- Kalibrr: Full support ( + auto-apply)
- JobStreet: Unstable, Selenium recommended
- LinkedIn: In progress
- Indeed: In progress
- Dealls: In progress

### Known Issues
- JobStreet API key changes frequently; the built-in adapter raises `NotImplementedError`
- Some platforms may require additional cookies or tokens for auto-apply
- LLM-based matching requires an xAI API key (paid service)

---

## [Unreleased]

### Planned Features
- Full LinkedIn integration
- Indeed scraper
- Dealls scraper
- WhatsApp notifications for job matches
- Telegram bot integration
- Improved matching algorithms with NLP
- Support for more CV formats (ODT, RTF)
- CI/CD pipeline with GitHub Actions
- Docker deployment
- Enhanced report dashboard

---

## Versioning

- **Major**: Incompatible API changes
- **Minor**: Backward-compatible new features
- **Patch**: Backward-compatible bug fixes

---

**Note**: This project is in active development. Breaking changes may occur before version 1.0.0.
