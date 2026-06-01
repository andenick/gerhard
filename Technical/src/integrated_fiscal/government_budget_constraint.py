#!/usr/bin/env python3
"""
Government Budget Constraint Analysis
Analyzes the fundamental relationship: T - G = -ΔDebt

This module verifies and analyzes the government budget constraint,
which states that the difference between tax revenue and government
spending must equal the negative of the change in debt.

Key Concepts:
- Fiscal Balance = Tax Revenue - Government Spending
- Change in Debt = -(Tax Revenue - Government Spending)
- Primary Balance = Fiscal Balance + Interest Payments
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns


class BudgetConstraintAnalyzer:
    """
    Analyzes government budget constraint relationships.

    The government budget constraint:
        T - G = -ΔD + (ΔM + ΔB)

    Where:
        T = Tax revenue
        G = Government spending
        ΔD = Change in debt
        ΔM = Change in monetary base (seigniorage)
        ΔB = Change in foreign reserves

    For most analysis, we simplify to: T - G = -ΔD
    """

    def __init__(self, tax_data: pd.DataFrame,
                 expenditure_data: pd.DataFrame,
                 debt_data: pd.DataFrame):
        """
        Initialize budget constraint analyzer.

        Args:
            tax_data: Tax revenue data
            expenditure_data: Government expenditure data
            debt_data: Public debt data
        """
        self.tax_data = tax_data
        self.expenditure_data = expenditure_data
        self.debt_data = debt_data

        self.fiscal_balance = None
        self.debt_changes = None
        self.discrepancies = None

    def calculate_fiscal_balance(self, year_col: str = 'year',
                                 tax_col: str = 'tax_revenue',
                                 spending_col: str = 'government_spending') -> pd.DataFrame:
        """
        Calculate fiscal balance: T - G

        Args:
            year_col: Column name for year
            tax_col: Column name for tax revenue
            spending_col: Column name for spending

        Returns:
            DataFrame with fiscal balance by year
        """
        # Merge tax and spending data
        merged = pd.merge(
            self.tax_data[[year_col, tax_col]],
            self.expenditure_data[[year_col, spending_col]],
            on=year_col
        )

        # Calculate balance
        merged['fiscal_balance'] = merged[tax_col] - merged[spending_col]
        merged['surplus_deficit'] = merged['fiscal_balance'].apply(
            lambda x: 'Surplus' if x > 0 else 'Deficit'
        )

        self.fiscal_balance = merged
        return self.fiscal_balance

    def calculate_debt_changes(self, year_col: str = 'year',
                               debt_col: str = 'total_debt') -> pd.DataFrame:
        """
        Calculate change in debt: ΔD

        Args:
            year_col: Column name for year
            debt_col: Column name for total debt

        Returns:
            DataFrame with debt changes
        """
        debt_df = self.debt_data[[year_col, debt_col]].sort_values(year_col)

        # Calculate year-over-year change
        debt_df['debt_change'] = debt_df[debt_col].diff()
        debt_df['debt_change_pct'] = debt_df[debt_col].pct_change() * 100

        self.debt_changes = debt_df
        return self.debt_changes

    def verify_budget_constraint(self, tolerance: float = 0.05) -> pd.DataFrame:
        """
        Verify budget constraint: T - G = -ΔD

        Args:
            tolerance: Acceptable discrepancy as fraction of GDP

        Returns:
            DataFrame with verification results
        """
        if self.fiscal_balance is None:
            self.calculate_fiscal_balance()

        if self.debt_changes is None:
            self.calculate_debt_changes()

        # Merge fiscal balance and debt changes
        verification = pd.merge(
            self.fiscal_balance[['year', 'fiscal_balance']],
            self.debt_changes[['year', 'debt_change']],
            on='year'
        )

        # Budget constraint: T - G = -ΔD
        # So: fiscal_balance = -debt_change
        verification['predicted_debt_change'] = -verification['fiscal_balance']
        verification['discrepancy'] = verification['debt_change'] - verification['predicted_debt_change']
        verification['discrepancy_pct'] = (
            verification['discrepancy'] / verification['debt_change'] * 100
        )

        # Flag significant discrepancies
        verification['significant_discrepancy'] = (
            abs(verification['discrepancy_pct']) > (tolerance * 100)
        )

        self.discrepancies = verification
        return verification

    def decompose_discrepancies(self) -> pd.DataFrame:
        """
        Decompose discrepancies into potential sources:
        - Off-budget spending
        - Asset sales/purchases
        - Accounting adjustments
        - Timing differences
        - Monetary financing

        Returns:
            DataFrame with discrepancy decomposition
        """
        if self.discrepancies is None:
            self.verify_budget_constraint()

        decomposition = self.discrepancies.copy()

        # Placeholder for actual decomposition logic
        decomposition['off_budget_estimate'] = 0.0
        decomposition['asset_transactions'] = 0.0
        decomposition['timing_differences'] = 0.0
        decomposition['other_adjustments'] = decomposition['discrepancy']

        return decomposition

    def analyze_financing_sources(self) -> pd.DataFrame:
        """
        Analyze how deficits are financed:
        - Domestic borrowing
        - Foreign borrowing
        - Monetary financing
        - Asset sales

        Returns:
            DataFrame with financing breakdown
        """
        financing = self.debt_changes.copy()

        # Placeholder for financing source analysis
        financing['domestic_borrowing'] = 0.0
        financing['foreign_borrowing'] = 0.0
        financing['monetary_financing'] = 0.0
        financing['asset_sales'] = 0.0

        return financing

    def calculate_sustainability_indicators(self, gdp_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate fiscal sustainability indicators:
        - Debt-to-GDP ratio
        - Primary balance as % of GDP
        - Interest payments as % of GDP
        - Debt burden indicators

        Args:
            gdp_data: GDP data for normalization

        Returns:
            DataFrame with sustainability indicators
        """
        # Merge all data
        sustainability = pd.merge(
            self.fiscal_balance[['year', 'fiscal_balance']],
            self.debt_changes[['year', 'total_debt']],
            on='year'
        )
        sustainability = pd.merge(
            sustainability,
            gdp_data[['year', 'gdp']],
            on='year'
        )

        # Calculate ratios
        sustainability['debt_gdp_ratio'] = (
            sustainability['total_debt'] / sustainability['gdp'] * 100
        )
        sustainability['fiscal_balance_gdp'] = (
            sustainability['fiscal_balance'] / sustainability['gdp'] * 100
        )

        return sustainability

    def plot_budget_constraint(self, output_path: Path = None):
        """
        Visualize budget constraint relationship.

        Args:
            output_path: Where to save the plot
        """
        if self.discrepancies is None:
            self.verify_budget_constraint()

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Plot 1: Fiscal Balance vs Debt Change
        axes[0, 0].scatter(
            self.discrepancies['fiscal_balance'],
            -self.discrepancies['debt_change'],
            alpha=0.6
        )
        axes[0, 0].plot(
            self.discrepancies['fiscal_balance'],
            self.discrepancies['fiscal_balance'],
            'r--', label='Budget Constraint (T - G = -ΔD)'
        )
        axes[0, 0].set_xlabel('Fiscal Balance (T - G)')
        axes[0, 0].set_ylabel('Negative Debt Change (-ΔD)')
        axes[0, 0].set_title('Budget Constraint Verification')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # Plot 2: Discrepancies Over Time
        axes[0, 1].plot(
            self.discrepancies['year'],
            self.discrepancies['discrepancy'],
            marker='o'
        )
        axes[0, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[0, 1].set_xlabel('Year')
        axes[0, 1].set_ylabel('Discrepancy')
        axes[0, 1].set_title('Budget Constraint Discrepancies Over Time')
        axes[0, 1].grid(True, alpha=0.3)

        # Plot 3: Fiscal Balance Over Time
        axes[1, 0].bar(
            self.fiscal_balance['year'],
            self.fiscal_balance['fiscal_balance'],
            color=self.fiscal_balance['fiscal_balance'].apply(
                lambda x: 'g' if x > 0 else 'r'
            ),
            alpha=0.6
        )
        axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[1, 0].set_xlabel('Year')
        axes[1, 0].set_ylabel('Fiscal Balance')
        axes[1, 0].set_title('Fiscal Balance Over Time (Surplus/Deficit)')
        axes[1, 0].grid(True, alpha=0.3)

        # Plot 4: Debt Change Over Time
        axes[1, 1].plot(
            self.debt_changes['year'],
            self.debt_changes['debt_change'],
            marker='o',
            color='blue',
            label='Actual Debt Change'
        )
        axes[1, 1].plot(
            self.discrepancies['year'],
            self.discrepancies['predicted_debt_change'],
            marker='s',
            color='red',
            linestyle='--',
            label='Predicted from Budget Constraint'
        )
        axes[1, 1].set_xlabel('Year')
        axes[1, 1].set_ylabel('Change in Debt')
        axes[1, 1].set_title('Actual vs Predicted Debt Changes')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved plot to: {output_path}")
        else:
            plt.show()

    def generate_report(self, output_path: Path = None) -> Path:
        """
        Generate comprehensive budget constraint analysis report.

        Args:
            output_path: Where to save the report

        Returns:
            Path to generated report
        """
        if output_path is None:
            output_path = Path("budget_constraint_analysis.xlsx")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            # Fiscal balance
            if self.fiscal_balance is not None:
                self.fiscal_balance.to_excel(
                    writer, sheet_name='Fiscal Balance', index=False
                )

            # Debt changes
            if self.debt_changes is not None:
                self.debt_changes.to_excel(
                    writer, sheet_name='Debt Changes', index=False
                )

            # Budget constraint verification
            if self.discrepancies is not None:
                self.discrepancies.to_excel(
                    writer, sheet_name='Budget Constraint', index=False
                )

            # Summary statistics
            summary = pd.DataFrame({
                'Metric': [
                    'Average Fiscal Balance',
                    'Average Debt Change',
                    'Average Discrepancy',
                    'Discrepancy as % of Debt Change'
                ],
                'Value': [
                    self.fiscal_balance['fiscal_balance'].mean(),
                    self.debt_changes['debt_change'].mean(),
                    self.discrepancies['discrepancy'].mean(),
                    self.discrepancies['discrepancy_pct'].mean()
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)

        print(f"✓ Generated report: {output_path}")
        return output_path


def main():
    """Example usage."""
    print("=== Government Budget Constraint Analysis ===\n")
    print("This module verifies: T - G = -ΔD")
    print("\nTo use:")
    print("1. Load tax, expenditure, and debt data")
    print("2. Initialize BudgetConstraintAnalyzer")
    print("3. Run verification and analysis")
    print("4. Generate reports and visualizations")


if __name__ == "__main__":
    main()
