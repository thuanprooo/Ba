#!/usr/bin/env python3
# deviltools.py
# Python 3.8+
# Requires: rich (pip install rich)

import os
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

console = Console()

# ---------------- Banner (Fox) ----------------
def banner_fox():
    ascii_art = r"""
          /\   /\
         {  `---'  }
         {  O   O  }
         ~~>  V  <~~
          \  \|/  /
           `-----'____
           /     \    \_
          {       }\  )_\_   🦊
          |  \_/  |/ /  /
           \__/  /(_/  /
             (__/
    """
    console.print(ascii_art, style="bold green")
    console.print("       ☠️ DEVIL TOOLS ☠️", style="bold red")
    console.print("   Developed by @Cyber_LexS_Vx", style="cyan")
    console.print("   Channel : Anonymous_LexS_Vx\n", style="cyan")


# ---------------- Keywords ----------------
KEYWORDS = {
    "binance.com": "binance.com.txt",
    "paypal.com": "paypal.com.txt",
    "coinbase.com": "coinbase.com.txt",
    "kraken.com": "kraken.com.txt",
    "wise.com": "wise.com.txt",
    "revolut.com": "revolut.com.txt",
    "skrill.com": "skrill.com.txt",
    "neteller.com": "neteller.com.txt",
    "webmoney.ru": "webmoney.ru.txt",
    "blockchain.com": "blockchain.com.txt",
    "crypto.com": "crypto.com.txt",
    "okx.com": "okx.com.txt",
    "bybit.com": "bybit.com.txt",
    "huobi.com": "huobi.com.txt",
    "bitfinex.com": "bitfinex.com.txt",
    "facebook.com": "facebook.com.txt",
    "tiktok.com": "tiktok.com.txt",
    "wp-content": "wp-content.txt",
    "wp-admin": "wp-admin.txt",
    "wp-login.php": "wp-login.php.txt",
    "wp-config.php": "wp-config.php.txt",
    "wp_": "prefix_wp.txt",
    "plugins": "plugins.txt",
    "themes": "themes.txt",
}

KEYWORD_TUPLE = tuple(KEYWORDS.keys())


# ---------------- File processing (worker) ----------------
def process_file(file_path: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = defaultdict(list)
    try:
        with open(file_path, "r", errors="ignore", buffering=65536) as fh:
            for raw_line in fh:
                line = raw_line.rstrip("\n")
                lower = line.lower()
                for key in KEYWORD_TUPLE:
                    if key in lower:
                        result[key].append(line)
    except Exception as exc:
        console.print(f"[red][!] Error reading {file_path}: {exc}[/red]")
    return result


# ---------------- Save & Report ----------------
def save_results(output_dir: str, aggregated: Dict[str, List[str]]) -> None:
    os.makedirs(output_dir, exist_ok=True)
    for key, filename in KEYWORDS.items():
        out_path = os.path.join(output_dir, filename)
        try:
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write("\n".join(aggregated.get(key, [])))
        except Exception as exc:
            console.print(f"[red][!] Error writing {out_path}: {exc}[/red]")


def print_final_report(aggregated: Dict[str, List[str]]) -> None:
    table = Table(title="📊 FINAL SCAN REPORT", show_lines=True)
    table.add_column("Keyword", style="cyan", justify="left")
    table.add_column("Matches", style="magenta", justify="right")

    for key in KEYWORDS.keys():
        table.add_row(key, str(len(aggregated.get(key, []))))

    console.print("\n")
    console.print(table)


# ---------------- Main ----------------
def gather_txt_files(path_input: str) -> List[str]:
    files = []
    if os.path.isfile(path_input):
        files.append(path_input)
    else:
        for root, _, filenames in os.walk(path_input):
            for fn in filenames:
                if fn.lower().endswith(".txt"):
                    files.append(os.path.join(root, fn))
    return files


def main():
    banner_fox()

    path_input = input("Enter folder path or single .txt file (PATH) : ").strip()
    if not path_input:
        path_input = "."

    if not os.path.exists(path_input):
        console.print(f"[red]❌ Path does not exist: {path_input}[/red]")
        return

    all_files = gather_txt_files(path_input)
    if not all_files:
        console.print("[yellow]⚠️ No .txt files found in the given path.[/yellow]")
        return

    console.print(f"[green]Found {len(all_files)} .txt files. Starting scan...[/green]\n")

    aggregated: Dict[str, List[str]] = defaultdict(list)

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        "{task.completed}/{task.total} files",
        TimeElapsedColumn(),
        "• ETA:",
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Scanning files...", total=len(all_files))
        max_workers = min(32, (os.cpu_count() or 1))
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for partial in executor.map(process_file, all_files):
                for k, v in partial.items():
                    aggregated[k].extend(v)
                progress.advance(task)

    save_results("results", aggregated)
    print_final_report(aggregated)
    console.print("[bold green]\n[✓] Scan finished. Results saved in folder: results/[/bold green]")


if __name__ == "__main__":
    main()
