# Contributing

## Bug Reports

Open an issue on the [GitHub repository](https://github.com/wazam/r-fantasybaseball-indexer/issues). Include as much detail as possible: what you expected to happen, what actually happened, and the steps to reproduce it.

## Feature Requests

Check [ROADMAP.md](ROADMAP.md) first to see if the feature is already planned or proposed. If it is not listed, open an issue describing the feature and why it would be useful.

## Pull Requests

1. Fork the repository and create a branch from `main`.
2. Keep changes focused. One fix or feature per pull request.
3. Match the existing code style and patterns.
4. Test your changes locally before submitting.
5. Open the pull request against `main` with a clear description of what was changed and why.

## Code Style

- Python: follow the existing structure and naming conventions. Run `pipenv run flake8 .` to check for errors before submitting.
- Templates: plain HTML and Jinja2, no JavaScript frameworks.
- CSS: mobile-first, no CSS frameworks.
