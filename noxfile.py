from __future__ import annotations

import logging
import pathlib

import nox

nox.options.sessions = ["reformat", "type-check"]
nox.options.reuse_existing_virtualenvs = True
PACKAGE = "culturebot"
GENERAL_TARGETS = ["./noxfile.py", "./culturebot", "./ext", "./server"]

nox_logger = logging.getLogger(nox.__name__)


@nox.session()
def lint(session: nox.Session) -> None:
    """Run this project's modules against pre-defined linters."""
    session.install("black", "isort")

    session.run("black", *GENERAL_TARGETS, "--check")
    session.run("isort", *GENERAL_TARGETS, "--check")


@nox.session()
def reformat(session: nox.Session) -> None:
    """Reformat this project's modules to fit the standard style."""
    session.install("black", "isort", "sort-all")
    session.run("black", *GENERAL_TARGETS)
    session.run("isort", *GENERAL_TARGETS)

    session.log("sort-all")
    nox_logger.disabled = True
    session.run("sort-all", *map(str, pathlib.Path(PACKAGE).glob("**/*.py")), success_codes=[0, 1])
    nox_logger.disabled = False


@nox.session(name="type-check")
def type_check(session: nox.Session) -> None:
    """Statically analyse and veirfy this project using pyright and mypy."""
    session.install("pyright", "-r", "requirements.txt", silent=False)

    session.run("python", "-m", "pyright", PACKAGE, env={"PYRIGHT_PYTHON_FORCE_VERSION": "latest"})


@nox.session(python=False)
def prettier(session: nox.Session) -> None:
    """Run prettier on markdown files."""
    session.run("prettier", "-w", "*.md", "docs/*.md", "*.yml")
