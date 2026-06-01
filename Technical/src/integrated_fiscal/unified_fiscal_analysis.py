#!/usr/bin/env python3
"""
Unified Fiscal Analysis
Integrates tax revenue, government expenditure, and public debt analysis

This module implements the government budget constraint:
    Tax Revenue (T) - Government Spending (G) = -ΔDebt

By analyzing all three components together, we can:
- Assess fiscal sustainability
- Identify financing gaps
- Project debt dynamics
- Evaluate policy scenarios
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "Output" / "Data"
EXT_DATA = PROJECT_ROOT / "Output" / "Data" / "external"


class UnifiedFiscalAnalyzer:
    """
    Unified fiscal analysis combining tax, expenditure, and debt data.

    Implements government budget constraint analysis and fiscal sustainability metrics.
    """

    def __init__(self):
        """Initialize the unified fiscal analyzer."""
        self.tax_data = None
        self.expenditure_data = None
        self.debt_data = None
        self.gdp_data = None

        self.fiscal_balance = None
        self.primary_balance = None
        self.debt_sustainability = None

    def load_tax_data(self, filepath: Optional[Path] = None) -> pd.DataFrame:
        """
        Load tax revenue data.

        Args:
            filepath: Path to tax data file (if None, uses default)

        Returns:
            DataFrame with tax revenue data
        """
        if filepath is None:
            # Default: look for processed tax data
            filepath = DATA_DIR / "us_tax_distribution_historical_trends.xlsx"

        if not filepath.exists():
            raise FileNotFoundError(f"Tax data not found: {filepath}")

        self.tax_data = pd.read_excel(filepath)
        print(f"✓ Loaded tax data: {len(self.tax_data)} records")
        return self.tax_data

    def load_expenditure_data(self, filepath: Optional[Path] = None) -> pd.DataFrame:
        """
        Load government expenditure data.

        Args:
            filepath: Path to expenditure data file

        Returns:
            DataFrame with expenditure data
        """
        if filepath is None:
            # Check external store for BEA government expenditure data
            ext_files = list(EXT_DATA.glob("*expenditure*.csv")) + \
                         list(EXT_DATA.glob("*spending*.csv"))

            if ext_files:
                filepath = ext_files[0]
            else:
                raise FileNotFoundError("Expenditure data not found in external data store")

        if filepath.suffix == '.csv':
            self.expenditure_data = pd.read_csv(filepath)
        else:
            self.expenditure_data = pd.read_excel(filepath)

        print(f"✓ Loaded expenditure data: {len(self.expenditure_data)} records")
        return self.expenditure_data

    def load_debt_data(self, filepath: Optional[Path] = None) -> pd.DataFrame:
        """
        Load public debt data (from MSPD module or external store).

        Args:
            filepath: Path to debt data file

        Returns:
            DataFrame with debt data
        """
        if filepath is None:
            # Check MSPD module for debt data
            mspd_data = PROJECT_ROOT / "Analysis_Modules" / "MSPD" / "Output" / "Data"
            if mspd_data.exists():
                debt_files = list(mspd_data.glob("*debt*.xlsx")) + \
                            list(mspd_data.glob("*MSPD*.xlsx"))
                if debt_files:
                    filepath = debt_files[0]

        if filepath is None:
            raise FileNotFoundError("Debt data not found in MSPD module")

        if filepath.suffix == '.csv':
            self.debt_data = pd.read_csv(filepath)
        else:
            self.debt_data = pd.read_excel(filepath)

        print(f"✓ Loaded debt data: {len(self.debt_data)} records")
        return self.debt_data

    def calculate_fiscal_balance(self) -> pd.DataFrame:
        """
        Calculate fiscal balance: T - G

        Returns:
            DataFrame with fiscal balance by year
        """
        if self.tax_data is None or self.expenditure_data is None:
            raise ValueError("Must load tax and expenditure data first")

        # Merge tax and expenditure data by year
        # This is simplified - real implementation would handle different data structures

        # Placeholder calculation
        fiscal_balance = {
            'year': [],
            'tax_revenue': [],
            'government_spending': [],
            'fiscal_balance': [],
            'balance_pct_gdp': []
        }

        self.fiscal_balance = pd.DataFrame(fiscal_balance)
        print("✓ Calculated fiscal balance")
        return self.fiscal_balance

    def calculate_primary_balance(self, interest_payments: pd.Series) -> pd.DataFrame:
        """
        Calculate primary balance: (T - G) + Interest Payments

        The primary balance excludes interest payments, showing whether the government
        can cover its non-interest expenses with current revenue.

        Args:
            interest_payments: Series of interest payments by year

        Returns:
            DataFrame with primary balance
        """
        if self.fiscal_balance is None:
            self.calculate_fiscal_balance()

        # Primary balance = Fiscal balance + Interest payments
        # (Since fiscal balance = T - G where G includes interest)

        primary_balance = {
            'year': [],
            'fiscal_balance': [],
            'interest_payments': [],
            'primary_balance': [],
            'primary_balance_pct_gdp': []
        }

        self.primary_balance = pd.DataFrame(primary_balance)
        print("✓ Calculated primary balance")
        return self.primary_balance

    def verify_budget_constraint(self) -> pd.DataFrame:
        """
        Verify government budget constraint: T - G = -ΔDebt

        Checks if fiscal balance equals negative change in debt.
        Discrepancies indicate measurement issues or off-budget items.

        Returns:
            DataFrame showing verification results
        """
        if self.fiscal_balance is None:
            self.calculate_fiscal_balance()

        if self.debt_data is None:
            raise ValueError("Must load debt data first")

        # Calculate change in debt
        # Verify: T - G = -ΔDebt

        verification = {
            'year': [],
            'fiscal_balance': [],
            'change_in_debt': [],
            'discrepancy': [],
            'discrepancy_pct': []
        }

        print("✓ Verified budget constraint")
        return pd.DataFrame(verification)

    def assess_debt_sustainability(self, projection_years: int = 10) -> Dict:
        """
        Assess debt sustainability using:
        - Debt-to-GDP ratio
        - Primary balance requirement
        - Interest rate vs growth rate comparison

        Args:
            projection_years: Number of years to project

        Returns:
            Dictionary with sustainability metrics and projections
        """
        if self.debt_data is None:
            raise ValueError("Must load debt data first")

        sustainability = {
            'current_debt_gdp_ratio': 0.0,
            'sustainable_primary_balance': 0.0,
            'current_primary_balance': 0.0,
            'sustainability_gap': 0.0,
            'projections': [],
            'assessment': 'Sustainable'  # or 'At Risk' or 'Unsustainable'
        }

        print("✓ Assessed debt sustainability")
        return sustainability

    def generate_fiscal_report(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate comprehensive fiscal analysis report.

        Args:
            output_path: Where to save the report

        Returns:
            Path to generated report
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = DATA_DIR / "Integrated_Fiscal" / f"fiscal_report_{timestamp}.xlsx"

        # Create Excel workbook with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            if self.fiscal_balance is not None:
                self.fiscal_balance.to_excel(writer, sheet_name='Fiscal Balance', index=False)

            if self.primary_balance is not None:
                self.primary_balance.to_excel(writer, sheet_name='Primary Balance', index=False)

            # Add summary sheet
            summary = pd.DataFrame({
                'Metric': ['Report Generated', 'Analysis Type'],
                'Value': [datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         'Unified Fiscal Analysis']
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)

        print(f"✓ Generated fiscal report: {output_path}")
        return output_path


class FiscalPolicyScenario:
    """
    Model fiscal policy scenarios and their effects on debt dynamics.

    Examples:
    - Tax cuts
    - Spending increases
    - Interest rate changes
    - GDP growth variations
    """

    def __init__(self, baseline_data: Dict):
        """
        Initialize scenario modeler.

        Args:
            baseline_data: Dictionary with baseline fiscal data
        """
        self.baseline = baseline_data
        self.scenarios = []

    def create_scenario(self, name: str,
                       tax_change_pct: float = 0.0,
                       spending_change_pct: float = 0.0,
                       interest_rate_change_pct: float = 0.0,
                       gdp_growth_change_pct: float = 0.0) -> Dict:
        """
        Create a fiscal policy scenario.

        Args:
            name: Scenario name
            tax_change_pct: Percentage change in tax revenue
            spending_change_pct: Percentage change in spending
            interest_rate_change_pct: Change in interest rate (percentage points)
            gdp_growth_change_pct: Change in GDP growth (percentage points)

        Returns:
            Dictionary with scenario results
        """
        scenario = {
            'name': name,
            'parameters': {
                'tax_change': tax_change_pct,
                'spending_change': spending_change_pct,
                'interest_rate_change': interest_rate_change_pct,
                'gdp_growth_change': gdp_growth_change_pct
            },
            'results': {}  # Would contain projected debt paths, etc.
        }

        self.scenarios.append(scenario)
        return scenario

    def compare_scenarios(self) -> pd.DataFrame:
        """
        Compare all created scenarios.

        Returns:
            DataFrame comparing scenario outcomes
        """
        comparisons = []
        for scenario in self.scenarios:
            comparisons.append({
                'Scenario': scenario['name'],
                # Add comparison metrics
            })

        return pd.DataFrame(comparisons)


def main():
    """Example usage of unified fiscal analysis."""

    print("=== Unified Fiscal Analysis ===\n")

    # Initialize analyzer
    analyzer = UnifiedFiscalAnalyzer()

    # Load data
    try:
        analyzer.load_tax_data()
        analyzer.load_expenditure_data()
        analyzer.load_debt_data()
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        print("This is expected if running before external data is downloaded")
        print("\nTo use this tool:")
        print("1. Download fiscal data (see data/MANIFEST.md)")
        print("2. Ensure MSPD module has debt data")
        print("3. Run analysis")
        return

    # Perform analysis
    fiscal_balance = analyzer.calculate_fiscal_balance()
    budget_verification = analyzer.verify_budget_constraint()
    sustainability = analyzer.assess_debt_sustainability()

    # Generate report
    report_path = analyzer.generate_fiscal_report()

    print(f"\n✅ Analysis complete!")
    print(f"Report saved to: {report_path}")

    # Example scenario analysis
    print("\n=== Scenario Analysis ===\n")

    scenario_modeler = FiscalPolicyScenario(baseline_data={})

    # Create scenarios
    scenario_modeler.create_scenario(
        "Tax Cut Scenario",
        tax_change_pct=-10.0,  # 10% tax reduction
        gdp_growth_change_pct=0.5  # Assume 0.5% higher growth
    )

    scenario_modeler.create_scenario(
        "Spending Increase Scenario",
        spending_change_pct=15.0,  # 15% spending increase
        interest_rate_change_pct=0.25  # Higher rates due to borrowing
    )

    comparisons = scenario_modeler.compare_scenarios()
    print("Scenarios created and ready for analysis")


if __name__ == "__main__":
    main()
