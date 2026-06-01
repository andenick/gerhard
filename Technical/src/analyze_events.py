"""
Analyze Collected Fiscal Regime Events
=======================================

Query and analyze the fiscal regime events database.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

def analyze_events():
    db_path = Path("data/fiscal_regime_events.db")

    if not db_path.exists():
        print("Database not found!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print('='*80)
    print('FISCAL REGIME EVENTS DATABASE - COMPLETE ANALYSIS')
    print('='*80)

    # Total events
    cursor.execute('SELECT COUNT(*) FROM fiscal_regime_events')
    total = cursor.fetchone()[0]
    print(f'\nTotal Events Collected: {total}')

    # Events by type
    print('\n' + '='*80)
    print('EVENTS BY TYPE')
    print('='*80)
    cursor.execute('''
        SELECT event_type, COUNT(*), AVG(relevance_score)
        FROM fiscal_regime_events
        GROUP BY event_type
        ORDER BY COUNT(*) DESC
    ''')
    for event_type, count, avg_relevance in cursor.fetchall():
        print(f'{event_type:25s}: {count:2d} events (avg relevance: {avg_relevance:.2f})')

    # Events by severity
    print('\n' + '='*80)
    print('EVENTS BY SEVERITY')
    print('='*80)
    cursor.execute('''
        SELECT severity, COUNT(*)
        FROM fiscal_regime_events
        GROUP BY severity
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'major' THEN 2
                WHEN 'moderate' THEN 3
                WHEN 'minor' THEN 4
            END
    ''')
    for severity, count in cursor.fetchall():
        print(f'{severity:15s}: {count:2d} events')

    # Regime breaks
    print('\n' + '='*80)
    print('REGIME BREAK ANALYSIS')
    print('='*80)
    cursor.execute('''
        SELECT regime_break, comparability_impact, COUNT(*)
        FROM fiscal_regime_events
        GROUP BY regime_break, comparability_impact
        ORDER BY regime_break DESC
    ''')
    for regime_break, impact, count in cursor.fetchall():
        break_str = 'YES' if regime_break else 'NO'
        print(f'Regime Break: {break_str:3s} | Impact: {impact:15s} | Count: {count:2d}')

    # Countries
    print('\n' + '='*80)
    print('COUNTRIES AFFECTED')
    print('='*80)
    cursor.execute('SELECT countries FROM fiscal_regime_events')
    all_countries = set()
    for row in cursor.fetchall():
        try:
            countries = json.loads(row[0])
            all_countries.update(countries)
        except:
            pass

    if all_countries:
        print(f'Total countries identified: {len(all_countries)}')
        print(f'Countries: {", ".join(sorted(all_countries))}')
    else:
        print('No countries identified (events are global or unclassified)')

    # High-impact events
    print('\n' + '='*80)
    print('CRITICAL EVENTS (Regime Breaks)')
    print('='*80)
    cursor.execute('''
        SELECT title, event_type, countries, severity, comparability_impact, published_at
        FROM fiscal_regime_events
        WHERE regime_break = 1
        ORDER BY published_at DESC
    ''')
    for i, row in enumerate(cursor.fetchall(), 1):
        title, event_type, countries, severity, impact, pub_date = row
        try:
            countries_list = json.loads(countries) if countries else []
        except:
            countries_list = []
        print(f'\n{i}. {title}')
        print(f'   Type: {event_type} | Severity: {severity}')
        print(f'   Countries: {", ".join(countries_list) if countries_list else "Global"}')
        print(f'   Impact: {impact} | Published: {pub_date[:10]}')

    # Recent events
    print('\n' + '='*80)
    print('ALL EVENTS (Most Recent First)')
    print('='*80)
    cursor.execute('''
        SELECT title, event_type, severity, published_at, relevance_score
        FROM fiscal_regime_events
        ORDER BY published_at DESC
    ''')
    for i, row in enumerate(cursor.fetchall(), 1):
        title, event_type, severity, pub_date, relevance = row
        print(f'\n{i}. {title[:70]}')
        print(f'   Type: {event_type} | Severity: {severity} | Relevance: {relevance:.2f}')
        print(f'   Published: {pub_date[:10]}')

    conn.close()

if __name__ == "__main__":
    analyze_events()
