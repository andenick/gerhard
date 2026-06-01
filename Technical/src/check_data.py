"""
Data Completeness Checker
Reports which data sources have real data vs. need manual download.
Project: Gerhard
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "Technical" / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "Output" / "Data"
COUNTRIES_DIR = PROJECT_ROOT / "Countries"


def get_dir_size(path: Path) -> int:
    """Get total size of directory in bytes."""
    total = 0
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes >= 1_073_741_824:
        return f"{size_bytes / 1_073_741_824:.1f} GB"
    elif size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def count_files(path: Path, pattern: str = "*") -> int:
    """Count files matching pattern in directory."""
    if not path.exists():
        return 0
    return sum(1 for f in path.rglob(pattern) if f.is_file())


def check_raw_data():
    """Check raw data source completeness."""
    print("=" * 70)
    print("RAW DATA SOURCES")
    print("=" * 70)

    sources = {
        "worldbank": {
            "name": "World Bank",
            "description": "Tax revenue as % of GDP for 200+ countries",
            "min_size": 100_000,  # 100 KB minimum for real data
        },
        "imf": {
            "name": "IMF GFS",
            "description": "Government Finance Statistics",
            "min_size": 100_000,
        },
        "oecd": {
            "name": "OECD Revenue",
            "description": "Detailed revenue statistics by tax type",
            "min_size": 100_000,
        },
        "eurostat": {
            "name": "Eurostat",
            "description": "EU government finance statistics (COFOG)",
            "min_size": 1_000_000,  # 1 MB minimum
        },
        "wid": {
            "name": "WID.world",
            "description": "World Inequality Database (distributional)",
            "min_size": 1_000_000,
        },
        "us_dina": {
            "name": "US DINA",
            "description": "Saez-Zucman Distributional National Accounts",
            "min_size": 100_000,
        },
    }

    # Also check standalone CSV files
    standalone_files = {
        "worldbank_tax_revenue.csv": "World Bank tax revenue (direct CSV)",
        "imf_world_revenue.csv": "IMF World Revenue Longitudinal Data",
        "data_inventory.csv": "Data inventory manifest",
    }

    real_count = 0
    placeholder_count = 0

    for source_key, info in sources.items():
        source_dir = RAW_DIR / source_key
        if source_dir.exists():
            size = get_dir_size(source_dir)
            n_files = count_files(source_dir)
            is_real = size >= info["min_size"]

            status = "REAL DATA" if is_real else "PLACEHOLDER/GUIDE"
            symbol = "+" if is_real else "x"

            print(f"  [{symbol}] {info['name']:20s} {format_size(size):>10s}  ({n_files} files)  — {status}")

            if is_real:
                real_count += 1
            else:
                placeholder_count += 1
                print(f"      Note: {info['description']} — may need manual download")
        else:
            print(f"  [x] {info['name']:20s}  {'N/A':>10s}  (missing)  — DIRECTORY NOT FOUND")
            placeholder_count += 1

    print()
    print("  Standalone CSV files in raw/:")
    for filename, desc in standalone_files.items():
        filepath = RAW_DIR / filename
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"    [+] {filename:40s} {format_size(size):>10s}")
        else:
            print(f"    [x] {filename:40s}  not found")

    # Scan for HTML error pages masquerading as data files
    print()
    print("  HTML error page scan:")
    html_found = 0
    if RAW_DIR.exists():
        for data_file in RAW_DIR.rglob("*"):
            if data_file.is_file() and data_file.suffix.lower() in ('.csv', '.json', '.xml'):
                try:
                    with open(data_file, 'r', encoding='utf-8', errors='ignore') as f:
                        first_line = f.readline(512).strip()
                    if first_line.lower().startswith('<!doctype') or first_line.lower().startswith('<html'):
                        print(f"    [!] HTML ERROR PAGE: {data_file.relative_to(RAW_DIR)}")
                        html_found += 1
                except Exception:
                    pass
    if html_found == 0:
        print("    No HTML error pages detected")
    else:
        print(f"    WARNING: {html_found} file(s) contain HTML instead of data")
        placeholder_count += html_found

    print()
    print(f"  Summary: {real_count}/{real_count + placeholder_count} sources have real data")
    return real_count, placeholder_count


def check_outputs():
    """Check output completeness."""
    print()
    print("=" * 70)
    print("OUTPUT DATA")
    print("=" * 70)

    # Excel files
    if OUTPUT_DIR.exists():
        xlsx_files = list(OUTPUT_DIR.glob("*.xlsx"))
        json_files = list(OUTPUT_DIR.glob("*.json"))
        print(f"  Excel files:  {len(xlsx_files)}")
        print(f"  JSON files:   {len(json_files)}")

        # Check subdirectories
        for subdir in sorted(OUTPUT_DIR.iterdir()):
            if subdir.is_dir():
                n = count_files(subdir)
                size = get_dir_size(subdir)
                print(f"  {subdir.name + '/':16s} {n} files, {format_size(size)}")
    else:
        print("  [x] Output/Data directory not found!")

    # PDFs
    pdf_dir = PROJECT_ROOT / "Output" / "PDFs"
    if pdf_dir.exists():
        pdfs = list(pdf_dir.glob("*.pdf"))
        pngs = list(pdf_dir.glob("*.png"))
        print(f"\n  PDF reports:  {len(pdfs)}")
        print(f"  PNG charts:   {len(pngs)}")

    return len(xlsx_files) if OUTPUT_DIR.exists() else 0


def check_countries():
    """Check country infrastructure completeness."""
    print()
    print("=" * 70)
    print("COUNTRY INFRASTRUCTURE")
    print("=" * 70)

    if not COUNTRIES_DIR.exists():
        print("  [x] Countries directory not found!")
        return 0

    country_dirs = [d for d in COUNTRIES_DIR.iterdir() if d.is_dir() and len(d.name) == 2]
    print(f"  Country directories: {len(country_dirs)}")

    # Check completeness
    has_data = 0
    has_pdf = 0
    has_profile = 0

    for cdir in country_dirs:
        code = cdir.name
        if list((cdir / "Output" / "Data").glob("*.xlsx")) if (cdir / "Output" / "Data").exists() else []:
            has_data += 1
        if list((cdir / "Output" / "PDFs").glob("*.pdf")) if (cdir / "Output" / "PDFs").exists() else []:
            has_pdf += 1
        if (cdir / f"{code}_PROFILE.md").exists():
            has_profile += 1

    print(f"  With Excel data:    {has_data}/{len(country_dirs)}")
    print(f"  With PDF reports:   {has_pdf}/{len(country_dirs)}")
    print(f"  With profile docs:  {has_profile}/{len(country_dirs)}")

    return len(country_dirs)


def main():
    print()
    print("GERHARD DATA COMPLETENESS REPORT")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    real, placeholder = check_raw_data()
    n_outputs = check_outputs()
    n_countries = check_countries()

    print()
    print("=" * 70)
    print("OVERALL ASSESSMENT")
    print("=" * 70)

    if placeholder > 0:
        print(f"  WARNING: {placeholder} data source(s) need manual download or API fix")
        print("  The pipeline can still run with existing data, but coverage will be limited.")

    if n_outputs > 0:
        print(f"  Output data looks good ({n_outputs} Excel files)")

    if n_countries >= 200:
        print(f"  Country infrastructure complete ({n_countries} countries)")

    print()


if __name__ == "__main__":
    main()
