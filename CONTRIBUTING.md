# Contributing to AGUI SmartSupply

First off, thank you for considering contributing to AGUI SmartSupply! It's people like you that make this project better.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Docker Desktop
- Python 3.8 or higher (for local development)
- Git

### Setting Up the Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/agui-smartsupply.git
   cd agui-smartsupply
   ```

3. Set up your environment variables:
   ```bash
   cp .env.sample .env
   # Edit .env with your Azure credentials
   ```

4. Build and run with Docker:
   ```bash
   docker compose up --build
   ```

5. Access the application at `http://localhost:9000/`

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** to demonstrate the steps
- **Describe the behavior you observed** and what you expected to see
- **Include screenshots or animated GIFs** if applicable
- **Include your environment details** (OS, Python version, Docker version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful** to most users
- **List any similar features** in other projects if applicable

### Your First Code Contribution

Unsure where to begin? You can start by looking through `beginner` and `help-wanted` issues:

- **Beginner issues** - issues that should only require a few lines of code
- **Help wanted issues** - issues that might be more involved

### Pull Requests

The process described here has several goals:
- Maintain code quality
- Fix problems that are important to users
- Engage the community in working toward the best possible product
- Enable a sustainable system for maintainers to review contributions

## Development Process

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our style guidelines

3. **Test your changes** thoroughly:
   ```bash
   # Run any relevant tests
   docker compose up --build
   # Manually test the affected functionality
   ```

4. **Commit your changes** using clear commit messages

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request** against the main repository

## Style Guidelines

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use meaningful variable and function names
- Write docstrings for functions and classes
- Keep functions focused and small
- Add comments for complex logic

### JavaScript Code Style

- Use consistent indentation (2 spaces)
- Use meaningful variable and function names
- Use modern ES6+ features
- Add comments for complex logic

### Documentation Style

- Use clear and concise language
- Include code examples where appropriate
- Keep documentation up to date with code changes
- Use proper Markdown formatting

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - 🎨 `:art:` when improving the format/structure of the code
  - 🐛 `:bug:` when fixing a bug
  - ✨ `:sparkles:` when introducing new features
  - 📝 `:memo:` when writing docs
  - 🚀 `:rocket:` when improving performance
  - ✅ `:white_check_mark:` when adding tests
  - 🔒 `:lock:` when dealing with security

## Pull Requests

1. **Fill in the required template** completely
2. **Do not include issue numbers in the PR title**
3. **Include screenshots and animated GIFs** in your pull request whenever possible
4. **Follow the Python and JavaScript style guides**
5. **Include thoughtfully-worded, well-structured tests** when applicable
6. **Document new code** with clear comments and documentation
7. **End all files with a newline**
8. **Avoid platform-dependent code**

### Pull Request Review Process

1. Maintainers will review your PR
2. You may be asked to make changes
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

## Additional Notes

### Issue and Pull Request Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `documentation` | Improvements or additions to documentation |
| `enhancement` | New feature or request |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention is needed |
| `question` | Further information is requested |

## Recognition

Contributors will be recognized in our README and release notes.

## Questions?

Feel free to open an issue with your question, or reach out to the maintainers directly.

Thank you for contributing to AGUI SmartSupply! 🎉
