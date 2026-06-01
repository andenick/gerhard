#!/usr/bin/env python3
"""
Fiscal Sustainability Analysis
Assesses long-term sustainability of government fiscal policy

Key Questions:
1. Is the current fiscal path sustainable?
2. What primary balance is required for sustainability?
3. How does debt evolve under different scenarios?
4. What are the risks to fiscal sustainability?

Methodology:
- Debt dynamics equation: d_t = (1 + r - g)/(1 + g) * d_(t-1) - pb_t
- Where: d = debt/GDP, r = real interest rate, g = growth rate, pb = primary balance
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt


class FiscalSustainabilityAnalyzer:
    """
    Analyzes fiscal sustainability using debt dynamics.

    The debt sustainability condition:
        Debt is stable if the primary balance >= interest payments - nominal growth contribution

    Formally: pb* = (r - g) * d
    Where:
        pb* = required primary balance (as % of GDP)
        r = real interest rate
        g = real GDP growth rate
        d = debt-to-GDP ratio
    """

    def __init__(self, initial_debt_gdp: float,
                 avg_interest_rate: float,
                 avg_growth_rate: float):
        """
        Initialize sustainability analyzer.

        Args:
            initial_debt_gdp: Current debt-to-GDP ratio (as decimal, e.g., 1.0 for 100%)
            avg_interest_rate: Average real interest rate on debt (as decimal)
            avg_growth_rate: Average real GDP growth rate (as decimal)
        """
        self.d0 = initial_debt_gdp
        self.r = avg_interest_rate
        self.g = avg_growth_rate

        self.required_primary_balance = None
        self.sustainability_assessment = None

    def calculate_required_primary_balance(self) -> float:
        """
        Calculate required primary balance for debt stabilization.

        Formula: pb* = (r - g) * d

        Returns:
            Required primary balance as % of GDP
        """
        self.required_primary_balance = (self.r - self.g) * self.d0 * 100
        return self.required_primary_balance

    def project_debt_path(self,
                         primary_balance_path: List[float],
                         years: int = 10,
                         interest_rate_path: Optional[List[float]] = None,
                         growth_rate_path: Optional[List[float]] = None) -> pd.DataFrame:
        """
        Project future debt path given policy assumptions.

        Args:
            primary_balance_path: List of primary balances (as % of GDP)
            years: Number of years to project
            interest_rate_path: Optional list of interest rates (uses constant if None)
            growth_rate_path: Optional list of growth rates (uses constant if None)

        Returns:
            DataFrame with projected debt path
        """
        # Initialize
        debt_path = [self.d0]
        years_list = list(range(years + 1))

        # Use constant rates if paths not provided
        if interest_rate_path is None:
            interest_rate_path = [self.r] * years

        if growth_rate_path is None:
            growth_rate_path = [self.g] * years

        # Ensure primary balance path is long enough
        if len(primary_balance_path) < years:
            # Extend with last value
            primary_balance_path = primary_balance_path + \
                                  [primary_balance_path[-1]] * (years - len(primary_balance_path))

        # Project debt dynamics
        for t in range(years):
            r_t = interest_rate_path[t]
            g_t = growth_rate_path[t]
            pb_t = primary_balance_path[t] / 100  # Convert from % to decimal

            # Debt dynamics: d_t = [(1 + r)/(1 + g)] * d_(t-1) - pb_t
            d_t = ((1 + r_t) / (1 + g_t)) * debt_path[-1] - pb_t

            debt_path.append(d_t)

        # Create DataFrame
        projection = pd.DataFrame({
            'year': years_list,
            'debt_gdp_ratio': [d * 100 for d in debt_path],  # Convert to percentage
            'primary_balance': [0] + primary_balance_path[:years],
            'interest_rate': [self.r] + interest_rate_path[:years],
            'growth_rate': [self.g] + growth_rate_path[:years]
        })

        return projection

    def assess_sustainability(self, current_primary_balance: float) -> Dict:
        """
        Assess current fiscal sustainability.

        Args:
            current_primary_balance: Current primary balance (as % of GDP)

        Returns:
            Dictionary with sustainability assessment
        """
        required_pb = self.calculate_required_primary_balance()

        sustainability_gap = current_primary_balance - required_pb

        if sustainability_gap >= 0:
            assessment = "Sustainable"
            interpretation = "Current primary balance is sufficient to stabilize debt"
        elif sustainability_gap >= -1:
            assessment = "At Risk"
            interpretation = "Small adjustment needed to stabilize debt"
        else:
            assessment = "Unsustainable"
            interpretation = "Significant fiscal adjustment needed"

        self.sustainability_assessment = {
            'assessment': assessment,
            'interpretation': interpretation,
            'current_primary_balance': current_primary_balance,
            'required_primary_balance': required_pb,
            'sustainability_gap': sustainability_gap,
            'required_adjustment': max(0, -sustainability_gap),
            'current_debt_gdp': self.d0 * 100,
            'interest_rate': self.r * 100,
            'growth_rate': self.g * 100,
            'r_minus_g': (self.r - self.g) * 100
        }

        return self.sustainability_assessment

    def scenario_analysis(self,
                         scenarios: Dict[str, Dict],
                         years: int = 10) -> pd.DataFrame:
        """
        Compare debt paths under different scenarios.

        Args:
            scenarios: Dictionary mapping scenario names to parameters
                      Example: {
                          'Baseline': {'pb': -3, 'r': 0.02, 'g': 0.02},
                          'Austerity': {'pb': 0, 'r': 0.02, 'g': 0.015}
                      }
            years: Number of years to project

        Returns:
            DataFrame comparing scenario outcomes
        """
        all_projections = {}

        for scenario_name, params in scenarios.items():
            # Extract parameters
            pb_path = [params.get('pb', 0)] * years
            r_path = [params.get('r', self.r)] * years
            g_path = [params.get('g', self.g)] * years

            # Project debt path
            projection = self.project_debt_path(
                primary_balance_path=pb_path,
                years=years,
                interest_rate_path=r_path,
                growth_rate_path=g_path
            )

            all_projections[scenario_name] = projection['debt_gdp_ratio']

        # Combine into single DataFrame
        comparison = pd.DataFrame(all_projections)
        comparison['year'] = range(years + 1)

        return comparison

    def plot_sustainability(self,
                           current_primary_balance: float,
                           output_path: Optional[Path] = None):
        """
        Visualize sustainability analysis.

        Args:
            current_primary_balance: Current primary balance
            output_path: Where to save the plot
        """
        assessment = self.assess_sustainability(current_primary_balance)

        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Plot 1: Required vs Current Primary Balance
        categories = ['Required\nPrimary Balance', 'Current\nPrimary Balance']
        values = [assessment['required_primary_balance'],
                 assessment['current_primary_balance']]
        colors = ['red' if assessment['current_primary_balance'] < assessment['required_primary_balance'] else 'green',
                 'red' if assessment['current_primary_balance'] < 0 else 'green']

        axes[0, 0].bar(categories, values, color=colors, alpha=0.6)
        axes[0, 0].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[0, 0].set_ylabel('Primary Balance (% of GDP)')
        axes[0, 0].set_title('Sustainability: Required vs Current Primary Balance')
        axes[0, 0].grid(True, alpha=0.3, axis='y')

        # Plot 2: Sustainability Gap
        axes[0, 1].bar(['Sustainability\nGap'], [assessment['sustainability_gap']],
                      color='red' if assessment['sustainability_gap'] < 0 else 'green',
                      alpha=0.6)
        axes[0, 1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[0, 1].set_ylabel('Gap (percentage points)')
        axes[0, 1].set_title(f"Assessment: {assessment['assessment']}")
        axes[0, 1].grid(True, alpha=0.3, axis='y')

        # Plot 3: Scenario Projections
        scenarios = {
            'Current Policy': {'pb': current_primary_balance, 'r': self.r, 'g': self.g},
            'Stabilization': {'pb': assessment['required_primary_balance'], 'r': self.r, 'g': self.g},
            'Optimistic': {'pb': current_primary_balance, 'r': self.r, 'g': self.g + 0.01}
        }

        comparison = self.scenario_analysis(scenarios, years=20)

        for scenario in scenarios.keys():
            axes[1, 0].plot(comparison['year'], comparison[scenario],
                          marker='o', label=scenario, linewidth=2)

        axes[1, 0].axhline(y=self.d0 * 100, color='gray', linestyle='--', alpha=0.5,
                          label='Initial Debt Level')
        axes[1, 0].set_xlabel('Years')
        axes[1, 0].set_ylabel('Debt-to-GDP Ratio (%)')
        axes[1, 0].set_title('Debt Projections Under Different Scenarios')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # Plot 4: Key Parameters
        params_text = f"""
Sustainability Assessment
{'='*40}

Current Debt-to-GDP: {assessment['current_debt_gdp']:.1f}%
Interest Rate: {assessment['interest_rate']:.2f}%
Growth Rate: {assessment['growth_rate']:.2f}%
r - g: {assessment['r_minus_g']:.2f}%

Required Primary Balance: {assessment['required_primary_balance']:.2f}%
Current Primary Balance: {assessment['current_primary_balance']:.2f}%
Sustainability Gap: {assessment['sustainability_gap']:.2f}%

Status: {assessment['assessment']}
{assessment['interpretation']}
"""

        axes[1, 1].text(0.1, 0.5, params_text,
                       fontsize=10, family='monospace',
                       verticalalignment='center',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        axes[1, 1].axis('off')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"✓ Saved sustainability plot to: {output_path}")
        else:
            plt.show()


def main():
    """Example usage of fiscal sustainability analyzer."""

    print("=== Fiscal Sustainability Analysis ===\n")

    # Example: US fiscal situation (approximate 2024 values)
    analyzer = FiscalSustainabilityAnalyzer(
        initial_debt_gdp=1.20,     # 120% debt-to-GDP
        avg_interest_rate=0.03,    # 3% real interest rate
        avg_growth_rate=0.02       # 2% real GDP growth
    )

    # Calculate required primary balance
    required_pb = analyzer.calculate_required_primary_balance()
    print(f"Required Primary Balance: {required_pb:.2f}% of GDP")

    # Assess sustainability with current policy
    current_pb = -3.0  # Running -3% primary deficit
    assessment = analyzer.assess_sustainability(current_pb)

    print(f"\nSustainability Assessment: {assessment['assessment']}")
    print(f"Current Primary Balance: {assessment['current_primary_balance']:.2f}%")
    print(f"Required Primary Balance: {assessment['required_primary_balance']:.2f}%")
    print(f"Sustainability Gap: {assessment['sustainability_gap']:.2f}%")
    print(f"\n{assessment['interpretation']}")

    # Run scenario analysis
    print("\n=== Scenario Analysis ===\n")

    scenarios = {
        'Current Policy': {'pb': -3.0, 'r': 0.03, 'g': 0.02},
        'Fiscal Consolidation': {'pb': 0.0, 'r': 0.03, 'g': 0.025},
        'High Growth': {'pb': -3.0, 'r': 0.03, 'g': 0.04}
    }

    comparison = analyzer.scenario_analysis(scenarios, years=20)
    print("Debt-to-GDP Ratio in 20 years:")
    for scenario in scenarios.keys():
        final_debt = comparison[scenario].iloc[-1]
        print(f"  {scenario}: {final_debt:.1f}%")


if __name__ == "__main__":
    main()
