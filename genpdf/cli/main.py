"""genpdf command line: build, check, new."""

from __future__ import annotations

import argparse
import io
import logging
import sys
import time
from pathlib import Path

from genpdf.application.guards import BuildResult
from genpdf.cli.container import Container, create_container
from genpdf.domain.errors import GenpdfError

EXIT_OK = 0
EXIT_FAILED = 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _configure_output(args.verbose)
    container = create_container()
    try:
        return args.handler(container, args)
    except GenpdfError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_FAILED


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m genpdf", description=(
        "Generate PDF documents (WeasyPrint) and slide decks (Chrome) from Markdown."))
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-v", "--verbose", action="store_true", help="show details")
    shared.add_argument("--content", type=Path, default=Path("content"),
                        help="folder with the .md files (default: content)")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", parents=[shared], help="generate PDFs")
    build.add_argument("names", nargs="*", help="files to build, without .md (default: all)")
    build.add_argument("--out", type=Path, default=Path("output"),
                       help="output folder (default: output)")
    build.set_defaults(handler=_build)

    check = commands.add_parser("check", parents=[shared], help="validate without generating")
    check.add_argument("names", nargs="*", help="files to check, without .md (default: all)")
    check.set_defaults(handler=_check)

    new = commands.add_parser("new", parents=[shared], help="create a .md from a template")
    new.add_argument("kind", choices=["doc", "deck"], help="document or deck")
    new.add_argument("name", help="file name, e.g. my-document")
    new.set_defaults(handler=_new)
    return parser


# ── Commands ───────────────────────────────────────────────────────────────────


def _build(container: Container, args: argparse.Namespace) -> int:
    failed = 0
    for source in _sources(container, args.content, args.names):
        started = time.perf_counter()
        try:
            result = container.build.execute(source, args.out)
        except GenpdfError as error:
            print(f"FAIL  {error}", file=sys.stderr)
            failed += 1
            continue
        _report(result, time.perf_counter() - started, args.verbose)
        failed += 0 if result.ok else 1
    return EXIT_FAILED if failed else EXIT_OK


def _report(result: BuildResult, seconds: float, verbose: bool) -> None:
    pages = f"{result.pages} page" + ("" if result.pages == 1 else "s")
    line = f"{result.output.as_posix()}  {result.size_bytes / 1024:.1f} KB  {pages}"
    if verbose:
        line += f"  ({seconds:.1f}s, from {Path(result.source).as_posix()})"
    print(("OK    " if result.ok else "FAIL  ") + line)
    for violation in result.violations:
        print(f"      {violation}", file=sys.stderr)


def _check(container: Container, args: argparse.Namespace) -> int:
    sources = _sources(container, args.content, args.names)
    total = 0
    for source in sources:
        issues = container.validate.execute(source)
        total += len(issues)
        if issues or args.verbose:
            print(f"{'FAIL' if issues else 'OK  '}  {source.as_posix()}")
        for issue in issues:
            print(f"      line {issue.line}: {issue.message}")
    print(f"{len(sources)} file(s) checked, {total} issue(s)")
    return EXIT_FAILED if total else EXIT_OK


def _new(container: Container, args: argparse.Namespace) -> int:
    starter = container.presentation.starter("document" if args.kind == "doc" else "deck")
    target = container.create.execute(args.name, starter, args.content)
    print(f"created {target.as_posix()}")
    print(f"next: edit it, then run 'python -m genpdf build {args.name}'")
    return EXIT_OK


# ── Helpers ────────────────────────────────────────────────────────────────────


def _sources(container: Container, content: Path, names: list[str]) -> list[Path]:
    if not names:
        sources = container.storage.list_markdown(content)
        if not sources:
            raise GenpdfError(f"there are no .md files in {content.as_posix()}/. "
                              "Create one with 'python -m genpdf new doc my-document'")
        return sources
    return [_resolve(container, content, name) for name in names]


def _resolve(container: Container, content: Path, name: str) -> Path:
    path = content / (name if name.endswith(".md") else f"{name}.md")
    if not container.storage.exists(path):
        available = ", ".join(p.stem for p in container.storage.list_markdown(content))
        raise GenpdfError(f"{path.as_posix()} does not exist. Available: {available or 'none'}")
    return path


def _configure_output(verbose: bool) -> None:
    """UTF-8 output so accents survive on Windows, and engine warnings only in verbose."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(format="      %(name)s: %(message)s")
    level = logging.WARNING if verbose else logging.ERROR
    for name in ("weasyprint", "fontTools"):
        logging.getLogger(name).setLevel(level)
