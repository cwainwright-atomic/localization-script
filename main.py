import asyncio
from enum import Enum
import sys
import argparse
from pathlib import Path
import re
from dataclasses import dataclass

from pretty_table import PrettyTable
from translate import Translator


@dataclass
class ParseReporting:
    """Configuration for reporting during parsing."""

    empty_line: bool = False
    mismatch_pattern: bool = True
    duplicate_key: bool = True
    manual_translation: bool = True

    class Config(Enum):
        """Configuration for parse reporting levels."""

        DEFAULT = 0
        SILENT = 1
        VERBOSE = 2

        def get_report(self) -> "ParseReporting":
            match self:
                case ParseReporting.Config.DEFAULT:
                    return ParseReporting.default()
                case ParseReporting.Config.SILENT:
                    return ParseReporting.silent()
                case ParseReporting.Config.VERBOSE:
                    return ParseReporting.verbose()
                case _:
                    # If the enum is not recognized, raise an error
                    raise ValueError(f"Unknown config: {self}")

    @classmethod
    def default(cls) -> "ParseReporting":
        return cls(
            empty_line=False,
            mismatch_pattern=True,
            duplicate_key=True,
            manual_translation=True,
        )

    @classmethod
    def silent(cls) -> "ParseReporting":
        return cls(
            empty_line=False,
            mismatch_pattern=False,
            duplicate_key=False,
            manual_translation=False,
        )

    @classmethod
    def verbose(cls) -> "ParseReporting":
        return cls(
            empty_line=True,
            mismatch_pattern=True,
            duplicate_key=True,
            manual_translation=True,
        )


@dataclass
class MissingReporting:
    """Configuration for reporting missing declarations."""

    missing_declarations: bool = True
    string_format_warnings: bool = True

    class Config(Enum):
        """Configuration for missing reporting levels."""

        DEFAULT = 0
        SILENT = 1
        VERBOSE = 2

        def get_report(self) -> "MissingReporting":
            match self:
                case MissingReporting.Config.DEFAULT:
                    return MissingReporting.default()
                case MissingReporting.Config.SILENT:
                    return MissingReporting.silent()
                case MissingReporting.Config.VERBOSE:
                    return MissingReporting.verbose()
                case _:
                    # If the enum is not recognized, raise an error
                    raise ValueError(f"Unknown config: {self}")

    @classmethod
    def default(cls) -> "MissingReporting":
        return cls(missing_declarations=True, string_format_warnings=True)

    @classmethod
    def silent(cls) -> "MissingReporting":
        return cls(missing_declarations=False, string_format_warnings=False)

    @classmethod
    def verbose(cls) -> "MissingReporting":
        return cls(missing_declarations=True, string_format_warnings=True)


def get_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Process input file lines.")
    parser.add_argument(
        "--base",
        type=Path,
        required=True,
        help="Base file name to compare or reference",
    )
    parser.add_argument(
        "comparison_files", type=Path, nargs="*", help="Comparison files"
    )
    parser.add_argument(
        "--parse",
        type=str,
        choices=[e.name for e in ParseReporting.Config],
        default=ParseReporting.Config.DEFAULT.name,
        help="Set the level of reporting for parsing",
    )
    parser.add_argument(
        "--missing",
        type=str,
        choices=[e.name for e in MissingReporting.Config],
        default=MissingReporting.Config.DEFAULT.name,
        help="Show missing declarations in comparison files",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        default=False,
        help="Translate the input file to comparison files with google translate",
    )
    return parser.parse_args()


def collect_language_files(root_directory: Path, exclude: Path | None) -> list[Path]:
    """Collect all language files in a directory, excluding a specific file."""
    collected_files: list[Path] = []
    for path in root_directory.rglob("Localizable.strings"):
        if path.is_file() and path != exclude:
            collected_files.append(path)
    return collected_files


def parse(
    filepath: Path, report: ParseReporting = ParseReporting.default()
) -> dict[str, tuple[int, str]]:
    """Parse a file and return a dictionary of lines with their line numbers and values.

    Files are expected to contain lines in the format: \"foo\" = \"bar\";"""
    lines: dict[str, tuple[int, str]] = {}

    print(f"\nParsing file: {filepath}", file=sys.stderr)

    with open(filepath, "r", encoding="utf-8") as f:
        pattern = re.compile(r"\"(.*)\" *= *\"(.*)\";")

        for i, line in enumerate(f.readlines()):
            match = pattern.match(line.strip())

            if match == None or len(match.groups()) != 2:
                if line.strip() == "":
                    if report.empty_line:
                        print(f"Line {i} is empty, skipping.", file=sys.stderr)
                elif report.mismatch_pattern:
                    print(
                        f"Line {i} does not match pattern: {line.strip()}, skipping",
                        file=sys.stderr,
                    )
                continue

            key, value = match.groups()

            if key in lines:
                if report.duplicate_key:
                    print(
                        f"Duplicate key found: {key} appears at line {lines[key][0]} and line {i}. skipping.",
                        file=sys.stderr,
                    )
                continue

            lines[key] = (i, value)
    return lines


def shorten_string(s: str, max_length: int = 60) -> str:
    """Shorten a string to max_length, adding ellipses if truncated."""
    if len(s) > max_length:
        return s[: max_length - 3] + "..."
    return s


def get_missing_declarations(
    base_parse: dict[str, tuple[int, str]],
    comparison_file: Path,
    comparison_parse: dict[str, tuple[int, str]],
    report: MissingReporting = MissingReporting.default(),
) -> list[tuple[str, tuple[int, str]]]:
    """Check for missing declarations in comparison files compared to the base file.

    If report = True: report any missing declarations."""

    print(
        f"\nScanning for missing declarations in file: {comparison_file}",
        file=sys.stderr,
    )

    missing_declarations: list[tuple[str, tuple[int, str]]] = []
    for base_key, base_value in base_parse.items():
        if base_key not in comparison_parse:
            missing_declarations.append((base_key, base_value))

    if report.missing_declarations:
        if missing_declarations:
            print(
                f"Found {len(missing_declarations)} missing declarations",
                file=sys.stderr,
            )

            table = PrettyTable(
                data=[
                    [line_num, key, shorten_string(value)]
                    for (key, (line_num, value)) in missing_declarations
                ],
                headers=["Line", "Key", "Value"],
            )
            print(table, file=sys.stderr)
        else:
            print(
                f"No missing declarations found in {comparison_file}.", file=sys.stderr
            )

    string_format_lines = list(filter(lambda x: "%@" in x[1][1], missing_declarations))

    if report.string_format_warnings:
        if string_format_lines:
            print(
                f"Warning: The following missing declarations in {comparison_file} contain string format specifiers (%@):",
                file=sys.stderr,
            )

            table = PrettyTable(
                data=[
                    [line_num, key, shorten_string(value)]
                    for (key, (line_num, value)) in string_format_lines
                ],
                headers=["Line", "Key", "Value"],
            )

            print(table, file=sys.stderr)

    return missing_declarations


def get_language(filepath: Path) -> str:
    """Determine the destination language based on the file name.

    Supports language codes like 'fr', 'zh-CN', etc. in paths like '/fr.lproj/' or '/zh-CN.lproj/'.
    """
    match = re.search(r"([a-z]{2,3}(?:-[a-zA-Z]{2})?)\.lproj", str(filepath))
    if match:
        return match.group(1)
    raise ValueError(f"Could not determine language from filepath: {filepath}")


def get_translated_declarations(
    missing_decls: list[tuple[str, tuple[int, str]]],
    dest: str,
    src: str = "en",
) -> list[tuple[str, tuple[int, str], str]]:
    translator = Translator()

    texts = list(map(lambda x: x[1][1], missing_decls))

    coroutine = translator.a_batch_translate(texts, dest=dest, src=src)

    translations: list[str] = asyncio.run(coroutine)
    translated_texts: map[str] = map(lambda t: t.text, translations)  # type: ignore

    return list(
        map(
            lambda pair: (pair[0][0], pair[0][1], pair[1]),
            zip(missing_decls, translated_texts),
        )
    )


def main() -> None:
    args: argparse.Namespace = get_args()

    parse_reporting = ParseReporting.Config[args.parse].get_report()
    missing_reporting = MissingReporting.Config[args.missing].get_report()

    base_file: Path = args.base
    print(f"Parsing base file {base_file}", file=sys.stderr)
    base_parse: dict[str, tuple[int, str]] = parse(base_file, parse_reporting)

    comparison_files: list[Path] = args.comparison_files
    if not comparison_files:
        print(
            "No comparison files provided. Exiting.",
            file=sys.stderr,
        )
        sys.exit(0)

    if len(comparison_files) == 1 and comparison_files[0].is_dir():
        print(
            f"Collecting language files from directory: {comparison_files[0]}",
            file=sys.stderr,
        )
        comparison_files = collect_language_files(
            comparison_files[0], exclude=base_file
        )
    else:
        comparison_files = args.comparison_files

    # Dictionary to hold comparison parses
    # Key: filepath (Path object)
    # Value: parse dictionary (see parse function)
    comparison_parses: dict[Path, dict[str, tuple[int, str]]] = {}
    print("\n\nParsing comparison files", comparison_files, file=sys.stderr)
    for comparison_file in comparison_files:
        comparison_parse: dict[str, tuple[int, str]] = parse(
            comparison_file, parse_reporting
        )
        comparison_parses[comparison_file] = comparison_parse

    # Dictionary to hold missing declarations
    # Key: filepath (Path object)
    # Value: list of tuples (key, (line number, value))
    missing_declarations: dict[Path, list[tuple[str, tuple[int, str]]]] = {}

    print("\n\nChecking for missing declarations", file=sys.stderr)
    for comparison_file, comparison_parse in comparison_parses.items():
        missing_declarations[comparison_file] = get_missing_declarations(
            base_parse,
            comparison_file,
            comparison_parse,
            report=missing_reporting,
        )

    # Dictionary to hold translated declarations
    # Key: filepath (Path object)
    # Value: list of tuples (key, (line number, value), translation)
    translated_declarations: dict[Path, list[tuple[str, tuple[int, str], str]]] = {}

    if args.translate:
        for comparison_file, missing_decls in missing_declarations.items():
            if not missing_decls:
                print(
                    f"No missing declarations to translate in {comparison_file}.",
                    file=sys.stderr,
                )
                continue

            print(
                f"\n\nTranslating missing declarations in {comparison_file}...",
                file=sys.stderr,
            )

            src = get_language(base_file)
            dest = get_language(comparison_file)

            print(
                f"Destination language for {comparison_file}: {dest}", file=sys.stderr
            )

            translated_declarations[comparison_file] = get_translated_declarations(
                missing_decls,
                src=src,
                dest=dest,
            )

    for comparison_file, translated_decls in translated_declarations.items():
        if not translated_decls:
            continue

        if args.translate:
            print(f"\nTranslated declarations for {comparison_file}:", file=sys.stderr)

            translated_table = PrettyTable(
                data=[
                    [
                        line_num,
                        key,
                        shorten_string(value),
                        shorten_string(translation),
                    ]
                    for (
                        key,
                        (line_num, value),
                        translation,
                    ) in translated_decls
                ],
                headers=["Line", "Key", "Value", "Translation"],
            )
            print(translated_table, file=sys.stderr)


if __name__ == "__main__":
    main()
