# Contributing to Loker Agent

First off, thank you for considering contributing to Loker Agent! 🎉

We welcome contributions of all kinds: bug reports, feature suggestions, code improvements, documentation updates, and more.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Code Contributions](#code-contributions)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Style Guide](#style-guide)

---

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and considerate in your interactions.

---

## 💡 How Can I Contribute?

### Reporting Bugs

If you find a bug, please create an issue on GitHub with the following information:

- **Describe the bug**: A clear and concise description of what the bug is.
- **To Reproduce**: Steps to reproduce the behavior.
- **Expected behavior**: A clear and concise description of what you expected to happen.
- **Screenshots**: If applicable, add screenshots to help explain your problem.
- **Environment**: OS, Python version, and any relevant configuration.
- **Logs**: Include any error messages or logs.

### Suggesting Features

We welcome feature suggestions! Please create an issue on GitHub with:

- **Clear description**: What problem does this feature solve?
- **Use case**: Who would benefit from this feature?
- **Proposed solution**: How would you like it to work?
- **Alternatives**: Are there any alternative solutions you've considered?

### Code Contributions

We accept code contributions via pull requests. To get started:

1. **Find an issue**: Look for issues labeled `good-first-issue` or `help-wanted`.
2. **Fork the repository**: Click the "Fork" button on GitHub.
3. **Clone your fork**: `git clone https://github.com/your-username/loker-agent.git`
4. **Create a branch**: `git checkout -b feature/your-feature-name`
5. **Make your changes**: Write code and tests.
6. **Run tests**: Ensure all tests pass.
7. **Commit your changes**: Write a clear commit message.
8. **Push to your fork**: `git push origin feature/your-feature-name`
9. **Open a pull request**: Go to the original repository and click "New Pull Request".

---

## 🛠️ Development Setup

### Prerequisites

- Python 3.9 or higher
- pip
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/loker-agent.git
cd loker-agent
```

### Step 2: Create a Virtual Environment

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

### Step 4: Install Development Dependencies

```bash
pip install -r requirements-dev.txt  # If available
```

### Step 5: Install the Package in Editable Mode

```bash
pip install -e .
```

### Step 6: Set Up Configuration

```bash
cp config.example.json config.json
cp profile.example.json profile.json
```

### Step 7: Run Tests

```bash
pytest tests/
```

---

## 📝 Coding Standards

We follow PEP 8 for Python code style. Please ensure your code adheres to these standards.

### Key Guidelines

- Use 4 spaces for indentation (no tabs).
- Maximum line length: 100 characters.
- Use descriptive variable names.
- Write docstrings for all public classes, methods, and functions.
- Use type hints where possible.

### Example

```python
def calculate_match_score(job_skills: List[str], profile_skills: List[str]) -> float:
    """
    Calculate the match score between job skills and profile skills.

    Args:
        job_skills: List of skills required for the job.
        profile_skills: List of skills from the candidate profile.

    Returns:
        Match score as a float between 0 and 1.
    """
    if not job_skills:
        return 0.0

    matching_skills = set(job_skills) & set(profile_skills)
    return len(matching_skills) / len(job_skills)
```

---

## 🧪 Testing

All code contributions must include tests. We use `pytest` as our testing framework.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest --cov=loker_agent tests/

# Run a specific test file
pytest tests/test_matcher.py

# Run a specific test function
pytest tests/test_matcher.py::test_calculate_match_score
```

### Writing Tests

Place your tests in the `tests/` directory with the naming convention `test_*.py`.

Example test:

```python
def test_calculate_match_score():
    from loker_agent.matchers.engine import calculate_match_score
    
    job_skills = ["Python", "SQL", "Docker"]
    profile_skills = ["Python", "SQL", "Linux"]
    
    score = calculate_match_score(job_skills, profile_skills)
    assert score == 2/3
```

---

## 🔄 Pull Request Process

1. **Ensure your branch is up to date**:

   ```bash
   git fetch origin
   git checkout feature/your-feature-name
   git rebase origin/main
   ```

2. **Run tests**: Ensure all tests pass and code coverage does not decrease.

   ```bash
   pytest --cov=loker_agent tests/
   ```

3. **Update documentation**: If your changes affect user-facing features, update the relevant documentation.

4. **Write a clear PR description**: Include:
   - What problem does this PR solve?
   - How did you solve it?
   - What are the key changes?
   - Any breaking changes?
   - How to test?

5. **Request a review**: Assign a reviewer or request a review from the team.

6. **Address feedback**: Make requested changes and push them to your branch.

7. **Merge**: Once approved, a maintainer will merge your PR.

---

## 🎨 Style Guide

### Python

- Use `snake_case` for variables, functions, and methods.
- Use `PascalCase` for classes.
- Use `UPPER_CASE` for constants.
- Write docstrings in Google format.

### Commit Messages

Write clear and concise commit messages:

```
feat: add support for LinkedIn scraper

- Implemented LinkedIn login flow
- Added job search and parsing
- Updated CLI to include LinkedIn as a platform

fixes #42
```

### Commit Message Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary changes

---

## 📚 Additional Resources

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) - Python Style Guide
- [pytest Documentation](https://docs.pytest.org/) - Testing framework
- [Python Type Hints](https://docs.python.org/3/library/typing.html) - Type hints

---

## ❓ Questions?

If you have any questions, feel free to open an issue or reach out to the maintainers.

**Thank you for contributing! 🙏**
