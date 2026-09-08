# Loker Agent

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Multi-platform Indonesian job agent: scrape, match CV, and auto-apply to job vacancies.**

Loker Agent automates the job search process by scraping job listings from multiple Indonesian job platforms (Glints, Kalibrr, and more), matching them against your CV using keyword and AI-based scoring, and optionally auto-applying to the best matches.

> **⚠️ Important**: Automating applications violates the Terms of Service of most job boards. Your account may be limited, suspended, or banned. Use at your own risk and always exercise moderation. By default, `safe_mode` is enabled, performing only dry-run matching until you explicitly enable `--apply`.

---

## 📋 Table of Contents

- [Features](#features)
- [Supported Platforms](#supported-platforms)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Scheduler](#scheduler)
- [Cover Letter Generator](#cover-letter-generator)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## ✨ Features

- ✅ **Scrape Jobs** – Search and fetch job listings from multiple Indonesian platforms.
- ✅ **CV Parsing** – Extract skills, experience, and education from PDF, DOCX, and TXT files.
- ✅ **Offline Matching** – Deterministic keyword/skill-based scoring (no external API required).
- ✅ **AI Matching** – Optional LLM-based scoring via xAI Grok (`XAI_API_KEY`).
- ✅ **Auto-Apply** – Submit applications to Glints and Kalibrr (with confirmation prompts).
- ✅ **Database** – Stores all job listings and application history in SQLite.
- ✅ **HTML Reports** – Generate visual reports of all scans and applications.
- ✅ **Scheduler** – Run regular automated scans on a schedule (daily, weekly, or custom intervals).
- ✅ **Cover Letter Generation** – Generate personalized cover letters from templates or via LLM.
- ✅ **Multi-Platform** – Supports Glints, Kalibrr, JobStreet (limited), and extensible for others.

---

## 🌐 Supported Platforms

| Platform | Status | Method | Notes |
|----------|--------|--------|-------|
| **Glints** | ✅ Full | GraphQL/REST API | Uses the same API as the Android app. Full auto-apply support. |
| **Kalibrr** | ✅ Full | Jobseeker API | Requires cookies and KB-CSRF token. Full auto-apply support. |
| **JobStreet** | ⚠️ Unstable | Selenium (recommended) | Search API key changes frequently. See [JobStreet Notes](#jobstreet-notes). |
| **LinkedIn** | 🚧 In Progress | Web scraping | - |
| **Indeed** | 🚧 In Progress | Web scraping | - |
| **Dealls** | 🚧 In Progress | Web scraping | - |

**Note**: You can extend support for additional platforms by implementing a scraper class that inherits from `BaseScraper` (see [Adding a New Platform](#adding-a-new-platform)).

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git (for cloning)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/loker-agent.git
cd loker-agent
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install the Package (Optional)

```bash
pip install -e .
```

This allows you to run `loker-agent` as a command-line tool from anywhere.

---

## ⚙️ Configuration

### Step 1: Copy Configuration Files

```bash
cp config.example.json config.json
cp profile.example.json profile.json
```

### Step 2: Edit `config.json`

The configuration file contains the following sections:

```json
{
  "cv": {
    "path": "cv/CV_CAHYONO_IT_SUPPORT_ATS.docx"  // Path to your CV file
  },
  "platforms": {
    "glints": {
      "enabled": true,                          // Enable/disable this platform
      "email": "your_email@example.com",       // Your Glints account email
      "password": "your_password"              // Your Glints account password
    },
    "kalibrr": {
      "enabled": true,
      "email": "your_email@example.com",
      "password": "your_password"
    },
    "jobstreet": {
      "enabled": false,                        // Disabled by default
      "email": "",
      "password": ""
    }
  },
  "": {
    "keywords": [                              // Keywords to search for
      "IT Support",
      "Network Engineer",
      "System Administrator"
    ],
    "locations": ["Jakarta", "Bandung", "Tangerang"],
    "max_results": 20                         // Maximum results per platform
  },
  "apply": {
    "safe_mode": true,                         // If true, only dry-run (no actual applications)
    "min_score": 60,                          // Minimum match score to apply (0-100)
    "max_applications": 10                    // Maximum applications per run
  },
  "report": {
    "output_dir": "outputs",                  // Directory for reports
    "format": "html"                          // Report format (html, json)
  },
  "llm": {
    "enabled": false,                         // Enable LLM-based scoring (requires API key)
    "provider": "xai",                        // Only xAI is currently supported
    "api_key": "your_xai_api_key"             // Get from https://console.x.ai
  }
}
```

### Step 3: Edit `profile.json`

Your profile should contain your personal information, skills, experience, and education:

```json
{
  "name": "Your Name",
  "title": "IT Support Specialist",
  "summary": "Experienced IT support professional with 5+ years in network administration.",
  "skills": [
    "Windows Server",
    "Linux",
    "Network Configuration",
    "Firewall Management",
    "Active Directory"
  ],
  "experience": [
    {
      "title": "IT Support Engineer",
      "company": "TechSolutions Inc.",
      "years": "2019-2024",
      "description": "Managed network infrastructure and user support."
    }
  ],
  "education": [
    {
      "degree": "Bachelor of Computer Science",
      "institution": "University of Indonesia",
      "year": "2018"
    }
  ]
}
```

### Step 4: Environment Variables

You can also use environment variables for sensitive data (recommended for CI/CD):

```bash
# .env file
GLINTS_EMAIL=your_email@example.com
GLINTS_PASSWORD=your_password
KALIBRR_EMAIL=your_email@example.com
KALIBRR_PASSWORD=your_password
XAI_API_KEY=your_xai_api_key
```

The config system will check environment variables first, then fall back to the config file.

---

## 📖 Usage

### Basic Usage (Dry Run)

Perform a match-only scan without sending any applications:

```bash
python run.py --cv path/to/CV.pdf --platforms glints,kalibrr
```

### Run with Auto-Apply (Confirmation)

Enable auto-apply with confirmation prompts for each job:

```bash
python run.py --cv path/to/CV.pdf --apply
```

### Run Fully Automatic (No Confirmation)

Enable auto-apply without any confirmation prompts:

```bash
python run.py --cv path/to/CV.pdf --apply --force-apply
```

### Override Configuration via CLI

You can override configuration values directly from the command line:

```bash
python run.py \
  --cv path/to/CV.pdf \
  --platforms glints,kalibrr \
  --min-score 70 \
  --max-applications 5 \
  --apply \
  --force-apply \
  --output outputs/custom_report
```

### Specify a Custom Config File

```bash
python run.py --config custom_config.json
```

### Set Logging Level

```bash
python run.py --log-level DEBUG
```

### Check Version

```bash
python run.py --version
```

---

## 📅 Scheduler

The scheduler allows you to run automated scans at regular intervals. See the full [Scheduler Guide](docs/SCHEDULER.md) for details.

### Quick Start

1. Configure your schedule in `schedule.json` (auto-created on first run):

```json
{
  "jobs": [
    {
      "id": "daily_morning",
      "name": "Daily Morning Scan",
      "schedule": {
        "type": "daily",
        "time": "08:00"
      },
      "options": {
        "platforms": ["glints", "kalibrr"],
        "apply": true,
        "min_score": 60,
        "max_applications": 10
      },
      "enabled": true
    }
  ]
}
```

2. Run the scheduler:

```bash
python -m scheduler.scheduler
```

### Schedule Types

- **Daily**: Run at a specific time every day (e.g., `08:00`)
- **Weekly**: Run on specific days of the week (e.g., `["Monday", "Wednesday", "Friday"]`)
- **Interval**: Run every N hours (e.g., `6` = every 6 hours)

---

## ✉️ Cover Letter Generator

The Cover Letter Generator creates personalized cover letters for job applications. See the full [Cover Letter Guide](docs/COVER_LETTER.md) for details.

### Quick Example

```python
from modules.cover_letter_generator import CoverLetterGenerator

# Initialize with config
generator = CoverLetterGenerator(config)

# Generate a cover letter
job_data = {
    "title": "IT Support Engineer",
    "company": "TechCorp",
    "description": "..."
}
profile = load_profile("profile.json")
letter = generator.generate(job_data, profile, template_name="professional")

print(letter)
```

### Template Types

- **default**: Standard cover letter
- **professional**: More formal, achievement-focused
- **short**: Brief and concise
- **custom**: Load from a file in `modules/templates/`

---

## 📁 Project Structure

```
loker-agent/
├── config.example.json          # Example configuration file
├── config.json                  # Your configuration (gitignored)
├── profile.example.json         # Example profile file
├── profile.json                 # Your profile (gitignored)
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── run.py                       # Main entry point
├── README.md                    # This file
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
├── CHANGELOG.md                 # Version history
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── API.md                   # API documentation
│   ├── SCHEDULER.md             # Scheduler guide
│   ├── COVER_LETTER.md          # Cover letter generator guide
│   ├── PLATFORMS.md             # Platform-specific documentation
│   └── TROUBLESHOOTING.md       # Troubleshooting guide
├── config/                      # Configuration module
│   ├── __init__.py
│   └── config_manager.py
├── core/                        # Core utilities
│   ├── __init__.py
│   ├── encryption.py            # Encryption utilities for credentials
│   └── env_loader.py            # Environment variable loader
├── loker_agent/                 # Main package
│   ├── __init__.py
│   ├── cli.py                   # Command-line interface
│   ├── config.py                # Configuration loader
│   ├── cv_parser.py             # CV parsing (PDF, DOCX, TXT)
│   ├── database.py              # SQLite database operations
│   ├── models.py                # Data models (Job, Application, etc.)
│   ├── utils.py                 # Utility functions
│   ├── apply/                   # Auto-apply engines
│   │   ├── __init__.py
│   │   ├── engine.py            # Application engine orchestrator
│   │   ├── glints_applier.py    # Glints auto-apply
│   │   └── kalibrr_applier.py   # Kalibrr auto-apply
│   ├── matchers/                # Matching engines
│   │   ├── __init__.py
│   │   ├── engine.py            # Matcher orchestrator
│   │   └── keywords.py          # Keyword-based matching
│   └── scrapers/                # Platform scrapers
│       ├── __init__.py
│       ├── base.py              # Base scraper class
│       ├── glints.py            # Glints scraper
│       ├── kalibrr.py           # Kalibrr scraper
│       ├── jobstreet.py         # JobStreet scraper (unstable)
│       ├── linkedin.py          # LinkedIn scraper (WIP)
│       ├── indeed.py            # Indeed scraper (WIP)
│       ├── dealls.py            # Dealls scraper (WIP)
│       ├── karirhub.py          # KarirHub scraper (WIP)
│       └── kitalulus.py         # KitaLulus scraper (WIP)
├── modules/                     # Additional modules
│   ├── cover_letter_generator.py
│   └── smart_filter.py          # AI-based job filtering
├── scheduler/                   # Scheduler module
│   └── scheduler.py
├── tests/                       # Unit tests
│   └── test_matcher.py
├── cv/                          # CV files
│   └── CV_CAHYONO_IT_SUPPORT_ATS.docx
├── data/                        # Data directory
│   └── loker.db                 # SQLite database
└── outputs/                     # Output directory
    └── report.html              # Generated HTML report
```

---

## 🔧 Advanced Usage

### LLM-Based Matching (xAI Grok)

To enable AI-powered matching, set `llm.enabled: true` in `config.json` and provide your xAI API key:

```json
"llm": {
  "enabled": true,
  "provider": "xai",
  "api_key": "your_xai_api_key"
}
```

The LLM will analyze the job description alongside your CV to provide a more nuanced match score than keyword-based matching alone.

### Custom Keywords

Modify the `.keywords` array in `config.json` to tailor job searches:

```json
"": {
  "keywords": [
    "Data Scientist",
    "Machine Learning Engineer",
    "AI Researcher"
  ]
}
```

### Custom Profile

Update `profile.json` with your actual details. The system uses this data for both matching and generating cover letters.

### Adding a New Platform

1. Create a new scraper class in `loker_agent/scrapers/` that inherits from `BaseScraper`:

```python
from .base import BaseScraper

class NewPlatformScraper(BaseScraper):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def search(self, keywords: list, location: str = None) -> list:
        # Implement search logic
        pass
        
    def get_job_details(self, job_id: str) -> dict:
        # Implement job details fetching
        pass
```

2. Implement an applier class in `loker_agent/apply/`:

```python
class NewPlatformApplier:
    def __init__(self, email: str, password: str):
        # Initialize session
        pass
        
    def apply(self, job_id: str, profile: dict) -> bool:
        # Implement application logic
        pass
```

3. Update the orchestrator in `loker_agent/cli.py` to include your new platform.

### JobStreet Notes

JobStreet actively blocks headless scraping and its search API key changes frequently. The built-in adapter will raise `NotImplementedError` rather than sending broken requests.

For JobStreet scraping, we recommend using a Selenium-based approach. See the reference implementations:
- [bahrul-dev/jobstreet-scraper](https://github.com/bahrul-dev/jobstreet-scraper) (Selenium + CDP)
- [aldrin112602/JobCraft](https://github.com/aldrin112602/JobCraft)

You can feed scraped results via a CSV import or custom adapter.

---

## 🧪 Testing

Run the test suite:

```bash
pytest tests/
```

Run a specific test file:

```bash
pytest tests/test_matcher.py
```

Run with coverage:

```bash
pytest --cov=loker_agent tests/
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Reporting bugs
- Suggesting features
- Submitting pull requests
- Coding standards
- Testing

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

**Use at your own risk.**

Automating applications violates the Terms of Service of most job boards. Your account may be limited, suspended, or banned. This tool is provided for educational and experimental purposes only. The authors are not responsible for any consequences arising from the use of this tool.

By using this tool, you agree that:
1. You are solely responsible for your actions.
2. You will not use this tool for malicious purposes.
3. You understand the risks of automating job applications.

---

## 📞 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Happy job hunting! 🎯**
