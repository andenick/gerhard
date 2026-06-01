"""
Batch generate fiscal reports for multiple countries
"""
import sys
from generate_country_fiscal_report import generate_country_report

def batch_generate(country_codes, tier_name=""):
    """Generate reports for a list of countries"""
    total = len(country_codes)
    successful = 0
    failed = []

    print(f"\n{'='*70}")
    print(f"Batch Report Generation: {tier_name}")
    print(f"Total countries: {total}")
    print(f"{'='*70}\n")

    for i, code in enumerate(country_codes, 1):
        print(f"\n[{i}/{total}] Processing {code}...")
        try:
            success = generate_country_report(code)
            if success:
                successful += 1
            else:
                failed.append(code)
        except Exception as e:
            print(f"ERROR: Failed to generate report for {code}: {e}")
            failed.append(code)

    # Summary
    print(f"\n{'='*70}")
    print(f"BATCH GENERATION COMPLETE: {tier_name}")
    print(f"{'='*70}")
    print(f"Total: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(failed)}")
    if failed:
        print(f"Failed countries: {', '.join(failed)}")
    print(f"{'='*70}\n")

    return successful, failed


if __name__ == "__main__":
    # Tier 1 countries
    tier1_all = ['AR', 'AU', 'AT', 'BE', 'BR', 'CA', 'CL', 'CN', 'DK', 'FI',
                 'FR', 'DE', 'GR', 'IN', 'ID', 'IE', 'IT', 'JP', 'KR', 'MX',
                 'NL', 'NZ', 'NO', 'PL', 'PT', 'RU', 'ZA', 'ES', 'SE', 'CH',
                 'TR', 'GB', 'US']

    tier1_completed = ['US', 'FR', 'BR', 'IN', 'ZA']
    tier1_remaining = [c for c in tier1_all if c not in tier1_completed]

    # Tier 2 countries
    tier2_all = ['BD', 'BO', 'BG', 'CO', 'HR', 'CZ', 'EC', 'EG', 'ET', 'GH',
                 'HU', 'IL', 'KE', 'KW', 'MY', 'PK', 'PY', 'PE', 'PH', 'RO',
                 'SA', 'SK', 'SI', 'LK', 'TZ', 'TH', 'UG', 'AE', 'UY']

    # All completed countries (Tier 1 + Tier 2)
    completed_countries = set(tier1_all + tier2_all)

    # Read all countries from unified index
    from pathlib import Path
    import re

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    index_file = PROJECT_ROOT / "Countries" / "UNIFIED_MASTER_INDEX.md"

    all_countries = []
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Match lines like: | United States | US | 1 | ...
                match = re.match(r'\|\s*([^|]+)\s*\|\s*([A-Z]{2,3})\s*\|\s*(\d+)', line)
                if match:
                    country_code = match.group(2).strip()
                    all_countries.append(country_code)

    # Remove duplicates and sort
    all_countries = sorted(set(all_countries))
    remaining_countries = [c for c in all_countries if c not in completed_countries]

    print(f"Total countries in index: {len(all_countries)}")
    print(f"Completed (Tier 1+2): {len(completed_countries)}")
    print(f"Remaining (Tier 3): {len(remaining_countries)}")

    if len(sys.argv) > 1:
        tier = sys.argv[1].lower()
        if tier == 'tier1':
            batch_generate(tier1_remaining, "Tier 1 Countries (Remaining)")
        elif tier == 'tier1-all':
            batch_generate(tier1_all, "Tier 1 Countries (All)")
        elif tier == 'tier2':
            batch_generate(tier2_all, "Tier 2 Countries")
        elif tier == 'tier3' or tier == 'remaining':
            batch_generate(remaining_countries, f"Remaining Countries (Tier 3 - {len(remaining_countries)} total)")
        elif tier == 'all':
            batch_generate(all_countries, f"All Countries ({len(all_countries)} total)")
        elif tier == 'test':
            # Test with just a few countries
            batch_generate(['AR', 'AU', 'AT'], "Test Batch")
        else:
            print("Usage: python batch_generate_reports.py [tier1|tier1-all|tier2|tier3|all|test]")
    else:
        print("Usage: python batch_generate_reports.py [tier1|tier1-all|tier2|tier3|all|test]")
        print("\nOptions:")
        print(f"  tier1      - Generate remaining Tier 1 countries (0)")
        print(f"  tier1-all  - Regenerate all Tier 1 countries ({len(tier1_all)})")
        print(f"  tier2      - Generate all Tier 2 countries ({len(tier2_all)})")
        print(f"  tier3      - Generate remaining Tier 3 countries ({len(remaining_countries)})")
        print(f"  all        - Generate ALL countries ({len(all_countries)})")
        print("  test       - Test with 3 countries")
