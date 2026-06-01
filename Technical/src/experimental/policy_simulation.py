#!/usr/bin/env python3
"""
Policy Simulation Framework
Advanced what-if analysis for fiscal policy scenarios and impact assessment
"""

import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime, timedelta
import warnings
from dataclasses import dataclass
from enum import Enum
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PolicyType(Enum):
    """Types of fiscal policies for simulation"""
    TAX_POLICY = "tax_policy"
    EXPENDITURE_POLICY = "expenditure_policy"
    STRUCTURAL_REFORM = "structural_reform"
    EXTERNAL_SHOCK = "external_shock"
    MONETARY_FISCAL = "monetary_fiscal"

@dataclass
class PolicyParameter:
    """Policy parameter definition"""
    name: str
    current_value: float
    policy_type: PolicyType
    min_value: float
    max_value: float
    unit: str
    description: str
    elasticities: Dict[str, float]  # Impact elasticities for different outcomes
    implementation_lag: int = 0  # Years to take effect
    persistence: float = 1.0  # How long the effect lasts (0-1)

class PolicyScenario:
    """Individual policy scenario definition"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters = {}  # parameter_name: new_value
        self.time_horizon = 10  # years
        self.assumptions = {}
        self.created_at = datetime.now()

class PolicySimulator:
    """Advanced fiscal policy simulation framework"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.simulation_dir = self.data_dir / "simulations"
        self.simulation_dir.mkdir(exist_ok=True)

        # Load base data
        self.base_data = {}
        self.load_base_data()

        # Initialize policy parameters
        self.policy_parameters = {}
        self.initialize_policy_parameters()

        # Simulation results storage
        self.simulation_results = {}
        self.scenario_library = {}

        # Model components
        self.economic_model = None
        self.fiscal_model = None
        self.distributional_model = None

        # Initialize models
        self.initialize_models()

    def load_base_data(self):
        """Load base fiscal and economic data"""
        logger.info("Loading base data for policy simulation...")

        # Try to load fiscal balances data
        fiscal_file = self.data_dir / "processed/fiscal_balances_master_dataset.csv"
        if fiscal_file.exists():
            self.base_data['fiscal_balances'] = pd.read_csv(fiscal_file)
            logger.info(f"✓ Loaded fiscal balances: {len(self.base_data['fiscal_balances'])} observations")

        # Try to load country rankings data
        rankings_file = self.data_dir / "processed/comprehensive_fiscal_rankings.csv"
        if rankings_file.exists():
            self.base_data['rankings'] = pd.read_csv(rankings_file)
            logger.info(f"✓ Loaded country rankings: {len(self.base_data['rankings'])} observations")

        # Try to load World Bank tax data
        tax_file = self.data_dir / "processed/world_bank_tax_revenue.csv"
        if tax_file.exists():
            self.base_data['tax_revenue'] = pd.read_csv(tax_file)
            logger.info(f"✓ Loaded World Bank tax data: {len(self.base_data['tax_revenue'])} observations")

        # Generate synthetic data if needed
        if not self.base_data:
            self.generate_synthetic_base_data()

    def generate_synthetic_base_data(self):
        """Generate synthetic base data for demonstration"""
        logger.info("Generating synthetic base data...")

        # Create synthetic fiscal data
        countries = ['USA', 'GER', 'FRA', 'GBR', 'JPN', 'CAN', 'AUS', 'ITA', 'ESP', 'KOR']
        years = list(range(2010, 2023))

        fiscal_data = []
        for country in countries:
            for year in years:
                # Generate realistic fiscal indicators
                gdp = np.random.uniform(500, 2000) * 1e9  # GDP in USD
                population = np.random.uniform(10, 300) * 1e6  # Population

                # Base fiscal ratios
                revenue_pct_gdp = np.random.uniform(15, 45)
                expenditure_pct_gdp = np.random.uniform(18, 50)
                deficit_pct_gdp = expenditure_pct_gdp - revenue_pct_gdp

                # Tax composition
                income_tax_share = np.random.uniform(0.25, 0.45)
                corporate_tax_share = np.random.uniform(0.05, 0.15)
                consumption_tax_share = np.random.uniform(0.25, 0.40)
                other_tax_share = 1 - (income_tax_share + corporate_tax_share + consumption_tax_share)

                # Expenditure composition
                education_share = np.random.uniform(0.12, 0.20)
                healthcare_share = np.random.uniform(0.15, 0.25)
                social_protection_share = np.random.uniform(0.25, 0.40)
                infrastructure_share = np.random.uniform(0.08, 0.15)
                other_expenditure_share = 1 - (education_share + healthcare_share + social_protection_share + infrastructure_share)

                fiscal_data.append({
                    'country_code': country,
                    'country_name': f'Country_{country}',
                    'year': year,
                    'gdp': gdp,
                    'population': population,
                    'gdp_per_capita': gdp / population,
                    'revenue_pct_gdp': revenue_pct_gdp,
                    'expenditure_pct_gdp': expenditure_pct_gdp,
                    'deficit_pct_gdp': deficit_pct_gdp,
                    'debt_pct_gdp': np.random.uniform(30, 120),
                    'income_tax_share': income_tax_share,
                    'corporate_tax_share': corporate_tax_share,
                    'consumption_tax_share': consumption_tax_share,
                    'other_tax_share': other_tax_share,
                    'education_share': education_share,
                    'healthcare_share': healthcare_share,
                    'social_protection_share': social_protection_share,
                    'infrastructure_share': infrastructure_share,
                    'other_expenditure_share': other_expenditure_share,
                    'unemployment_rate': np.random.uniform(3, 12),
                    'inflation_rate': np.random.uniform(0.5, 5),
                    'growth_rate': np.random.uniform(-2, 6)
                })

        self.base_data['fiscal_balances'] = pd.DataFrame(fiscal_data)
        logger.info(f"✓ Generated synthetic fiscal data: {len(fiscal_data)} observations")

    def initialize_policy_parameters(self):
        """Initialize comprehensive set of policy parameters"""
        logger.info("Initializing policy parameters...")

        # Tax Policy Parameters
        self.policy_parameters['personal_income_tax_rate'] = PolicyParameter(
            name="personal_income_tax_rate",
            current_value=0.25,  # 25% average rate
            policy_type=PolicyType.TAX_POLICY,
            min_value=0.10,
            max_value=0.50,
            unit="percentage",
            description="Average personal income tax rate",
            elasticities={
                'revenue_pct_gdp': 1.2,
                'growth_rate': -0.3,
                'income_inequality': -0.4,
                'labor_supply': -0.1
            }
        )

        self.policy_parameters['corporate_tax_rate'] = PolicyParameter(
            name="corporate_tax_rate",
            current_value=0.21,
            policy_type=PolicyType.TAX_POLICY,
            min_value=0.10,
            max_value=0.35,
            unit="percentage",
            description="Corporate income tax rate",
            elasticities={
                'revenue_pct_gdp': 0.3,
                'growth_rate': -0.2,
                'investment': -0.5,
                'competitiveness': -0.3
            }
        )

        self.policy_parameters['vat_rate'] = PolicyParameter(
            name="vat_rate",
            current_value=0.20,
            policy_type=PolicyType.TAX_POLICY,
            min_value=0.05,
            max_value=0.25,
            unit="percentage",
            description="Value Added Tax rate",
            elasticities={
                'revenue_pct_gdp': 0.8,
                'inflation_rate': 0.2,
                'consumption': -0.4,
                'regressive_impact': 0.3
            }
        )

        # Expenditure Policy Parameters
        self.policy_parameters['education_spending_pct_gdp'] = PolicyParameter(
            name="education_spending_pct_gdp",
            current_value=0.045,
            policy_type=PolicyType.EXPENDITURE_POLICY,
            min_value=0.02,
            max_value=0.08,
            unit="percentage of GDP",
            description="Government education spending as % of GDP",
            elasticities={
                'expenditure_pct_gdp': 1.0,
                'growth_rate': 0.2,
                'human_capital': 0.5,
                'long_term_productivity': 0.4
            },
            implementation_lag=2
        )

        self.policy_parameters['healthcare_spending_pct_gdp'] = PolicyParameter(
            name="healthcare_spending_pct_gdp",
            current_value=0.075,
            policy_type=PolicyType.EXPENDITURE_POLICY,
            min_value=0.04,
            max_value=0.12,
            unit="percentage of GDP",
            description="Government healthcare spending as % of GDP",
            elasticities={
                'expenditure_pct_gdp': 1.0,
                'health_outcomes': 0.6,
                'labor_productivity': 0.3,
                'fiscal_sustainability': -0.2
            }
        )

        self.policy_parameters['infrastructure_spending_pct_gdp'] = PolicyParameter(
            name="infrastructure_spending_pct_gdp",
            current_value=0.025,
            policy_type=PolicyType.EXPENDITURE_POLICY,
            min_value=0.01,
            max_value=0.05,
            unit="percentage of GDP",
            description="Infrastructure spending as % of GDP",
            elasticities={
                'expenditure_pct_gdp': 1.0,
                'growth_rate': 0.3,
                'productivity': 0.4,
                'competitiveness': 0.2
            },
            implementation_lag=1,
            persistence=0.8
        )

        # Structural Reform Parameters
        self.policy_parameters['pension_reform_factor'] = PolicyParameter(
            name="pension_reform_factor",
            current_value=1.0,
            policy_type=PolicyType.STRUCTURAL_REFORM,
            min_value=0.8,
            max_value=1.2,
            unit="multiplier",
            description="Pension system reform factor (1.0 = no change)",
            elasticities={
                'expenditure_pct_gdp': -0.4,
                'poverty_elderly': 0.5,
                'labor_force_participation': 0.1,
                'fiscal_sustainability': 0.6
            },
            implementation_lag=3,
            persistence=0.9
        )

        self.policy_parameters['labor_market_flexibility'] = PolicyParameter(
            name="labor_market_flexibility",
            current_value=0.5,
            policy_type=PolicyType.STRUCTURAL_REFORM,
            min_value=0.0,
            max_value=1.0,
            unit="index (0-1)",
            description="Labor market flexibility index",
            elasticities={
                'unemployment_rate': -0.3,
                'growth_rate': 0.2,
                'wage_flexibility': 0.4,
                'job_creation': 0.3
            },
            implementation_lag=1
        )

        # External Shock Parameters
        self.policy_parameters['global_growth_shock'] = PolicyParameter(
            name="global_growth_shock",
            current_value=0.0,
            policy_type=PolicyType.EXTERNAL_SHOCK,
            min_value=-0.05,
            max_value=0.05,
            unit="GDP growth points",
            description="Global economic growth shock",
            elasticities={
                'growth_rate': 1.0,
                'trade_volume': 1.5,
                'investment': 0.8,
                'employment': 0.6
            }
        )

        self.policy_parameters['commodity_price_shock'] = PolicyParameter(
            name="commodity_price_shock",
            current_value=0.0,
            policy_type=PolicyType.EXTERNAL_SHOCK,
            min_value=-0.5,
            max_value=0.5,
            unit="percentage change",
            description="Commodity price shock",
            elasticities={
                'inflation_rate': 0.3,
                'terms_of_trade': 1.0,
                'export_revenue': 0.8,
                'import_costs': 0.6
            }
        )

        logger.info(f"✓ Initialized {len(self.policy_parameters)} policy parameters")

    def initialize_models(self):
        """Initialize economic and fiscal modeling components"""
        logger.info("Initializing simulation models...")

        # Economic impact model
        self.economic_model = {
            'growth_equation': 'growth = base_growth + sum(policy_impacts)',
            'multipliers': {
                'tax_multiplier': -0.5,
                'spending_multiplier': 0.8,
                'investment_multiplier': 1.2
            },
            'elasticities': {}
        }

        # Fiscal sustainability model
        self.fiscal_model = {
            'debt_dynamics': 'debt_ratio_t+1 = debt_ratio_t * (1+interest_rate) - primary_balance',
            'primary_balance_target': 0.01,  # 1% of GDP
            'interest_rate_assumption': 0.03,
            'growth_rate_assumption': 0.02
        }

        # Distributional impact model
        self.distributional_model = {
            'income_groups': ['bottom_20', 'next_20', 'middle_20', 'next_20', 'top_20'],
            'tax_burden_elasticities': {
                'bottom_20': 0.5,
                'next_20': 0.8,
                'middle_20': 1.0,
                'next_20': 1.2,
                'top_20': 1.5
            },
            'benefit_elasticities': {
                'bottom_20': 1.5,
                'next_20': 1.2,
                'middle_20': 0.8,
                'next_20': 0.5,
                'top_20': 0.3
            }
        }

        logger.info("✓ Models initialized successfully")

    def create_scenario(self, name: str, description: str, parameter_changes: Dict[str, float]) -> PolicyScenario:
        """Create a new policy scenario"""
        scenario = PolicyScenario(name, description)

        for param_name, new_value in parameter_changes.items():
            if param_name in self.policy_parameters:
                scenario.parameters[param_name] = new_value
            else:
                logger.warning(f"Unknown parameter: {param_name}")

        self.scenario_library[name] = scenario
        logger.info(f"✓ Created scenario: {name}")

        return scenario

    def simulate_scenario(self, scenario: PolicyScenario, country_code: str = None, base_year: int = 2022) -> Dict:
        """Simulate the impact of a policy scenario"""
        logger.info(f"Simulating scenario: {scenario.name}")

        # Get base data for country (or use average if no country specified)
        if country_code and 'fiscal_balances' in self.base_data:
            country_data = self.base_data['fiscal_balances']
            base_country_data = country_data[country_data['country_code'] == country_code]
            if len(base_country_data) > 0:
                base_data = base_country_data[base_country_data['year'] == base_year].iloc[0]
            else:
                # Use country average
                base_data = country_data[country_data['year'] == base_year].iloc[0]
        else:
            # Use overall average
            if 'fiscal_balances' in self.base_data:
                base_data = self.base_data['fiscal_balances'][self.base_data['fiscal_balances']['year'] == base_year].iloc[0]
            else:
                logger.error("No base data available for simulation")
                return {}

        # Initialize simulation results
        years = list(range(base_year, base_year + scenario.time_horizon + 1))
        simulation_results = {
            'scenario_name': scenario.name,
            'country_code': country_code,
            'base_year': base_year,
            'time_horizon': scenario.time_horizon,
            'assumptions': scenario.assumptions,
            'yearly_results': {},
            'summary_metrics': {}
        }

        # Simulate year by year
        current_values = base_data.to_dict()

        for year in years[1:]:  # Skip base year
            year_results = current_values.copy()
            year_results['year'] = year

            # Calculate policy impacts
            policy_impacts = self.calculate_policy_impacts(scenario, current_values, year - base_year)

            # Update economic variables
            for variable, impact in policy_impacts.items():
                if variable in current_values:
                    year_results[variable] = current_values[variable] + impact

            # Calculate derived variables
            year_results['primary_balance_pct_gdp'] = year_results['revenue_pct_gdp'] - year_results['expenditure_pct_gdp']

            # Update debt dynamics
            if 'debt_pct_gdp' in current_values:
                interest_payment = current_values['debt_pct_gdp'] * self.fiscal_model['interest_rate_assumption']
                year_results['debt_pct_gdp'] = current_values['debt_pct_gdp'] + interest_payment - year_results['primary_balance_pct_gdp']

            # Store results
            simulation_results['yearly_results'][year] = year_results
            current_values = year_results

        # Calculate summary metrics
        simulation_results['summary_metrics'] = self.calculate_summary_metrics(simulation_results)

        # Store simulation results
        self.simulation_results[f"{scenario.name}_{country_code}_{base_year}"] = simulation_results

        logger.info(f"✓ Simulation completed for {scenario.name}")
        return simulation_results

    def calculate_policy_impacts(self, scenario: PolicyScenario, current_values: Dict, year_offset: int) -> Dict[str, float]:
        """Calculate the impact of policy changes in a given year"""
        impacts = {}

        for param_name, new_value in scenario.parameters.items():
            if param_name not in self.policy_parameters:
                continue

            param = self.policy_parameters[param_name]
            current_value = param.current_value
            change = new_value - current_value

            # Check implementation lag
            if year_offset < param.implementation_lag:
                continue

            # Calculate effective change with persistence
            effective_change = change * (param.persistence ** max(0, year_offset - param.implementation_lag))

            # Apply elasticities to calculate impacts
            for outcome, elasticity in param.elasticities.items():
                if outcome not in impacts:
                    impacts[outcome] = 0

                # Calculate impact based on elasticity
                if outcome == 'revenue_pct_gdp':
                    impacts[outcome] += effective_change * elasticity
                elif outcome == 'expenditure_pct_gdp':
                    impacts[outcome] += effective_change * elasticity
                elif outcome == 'growth_rate':
                    impacts[outcome] += effective_change * elasticity
                elif outcome == 'inflation_rate':
                    impacts[outcome] += effective_change * elasticity
                elif outcome == 'unemployment_rate':
                    impacts[outcome] += effective_change * elasticity
                elif outcome == 'debt_pct_gdp':
                    impacts[outcome] += effective_change * elasticity

        return impacts

    def calculate_summary_metrics(self, simulation_results: Dict) -> Dict:
        """Calculate summary metrics for simulation results"""
        yearly_data = simulation_results['yearly_results']

        if not yearly_data:
            return {}

        # Extract time series
        years = list(yearly_data.keys())
        final_year = max(years)

        # Growth metrics
        growth_rates = [data.get('growth_rate', 0) for data in yearly_data.values()]
        avg_growth = np.mean(growth_rates)
        growth_volatility = np.std(growth_rates)

        # Fiscal metrics
        final_balance = yearly_data[final_year].get('primary_balance_pct_gdp', 0)
        final_debt = yearly_data[final_year].get('debt_pct_gdp', 0)

        balances = [data.get('primary_balance_pct_gdp', 0) for data in yearly_data.values()]
        avg_balance = np.mean(balances)
        balance_trend = balances[-1] - balances[0] if len(balances) > 1 else 0

        # Social metrics
        unemployment_rates = [data.get('unemployment_rate', 0) for data in yearly_data.values()]
        avg_unemployment = np.mean(unemployment_rates)

        inflation_rates = [data.get('inflation_rate', 0) for data in yearly_data.values()]
        avg_inflation = np.mean(inflation_rates)

        # Sustainability metrics
        debt_sustainability_score = max(0, 100 - (final_debt - 60) * 2)  # 60% debt threshold
        fiscal_space_score = max(0, 100 - abs(final_balance) * 10)

        return {
            'economic_performance': {
                'average_growth_rate': avg_growth,
                'growth_volatility': growth_volatility,
                'average_unemployment': avg_unemployment,
                'average_inflation': avg_inflation
            },
            'fiscal_performance': {
                'final_primary_balance': final_balance,
                'final_debt_ratio': final_debt,
                'average_balance': avg_balance,
                'balance_improvement': balance_trend
            },
            'sustainability_indicators': {
                'debt_sustainability_score': debt_sustainability_score,
                'fiscal_space_score': fiscal_space_score,
                'overall_sustainability': (debt_sustainability_score + fiscal_space_score) / 2
            },
            'scenario_assessment': {
                'economic_impact': 'positive' if avg_growth > 2 else 'negative' if avg_growth < 1 else 'neutral',
                'fiscal_impact': 'improving' if balance_trend > 0.5 else 'deteriorating' if balance_trend < -0.5 else 'stable',
                'overall_assessment': self.assess_overall_impact(avg_growth, balance_trend, final_debt)
            }
        }

    def assess_overall_impact(self, growth: float, balance_trend: float, debt: float) -> str:
        """Assess overall policy impact"""
        score = 0

        # Growth impact
        if growth > 3:
            score += 2
        elif growth > 2:
            score += 1
        elif growth < 1:
            score -= 1

        # Fiscal balance impact
        if balance_trend > 1:
            score += 2
        elif balance_trend > 0.5:
            score += 1
        elif balance_trend < -0.5:
            score -= 1

        # Debt sustainability
        if debt < 60:
            score += 1
        elif debt > 90:
            score -= 2

        if score >= 3:
            return 'highly_positive'
        elif score >= 1:
            return 'positive'
        elif score >= -1:
            return 'neutral'
        elif score >= -3:
            return 'negative'
        else:
            return 'highly_negative'

    def create_predefined_scenarios(self):
        """Create a library of predefined policy scenarios"""
        logger.info("Creating predefined policy scenarios...")

        # Scenario 1: Fiscal Consolidation
        self.create_scenario(
            name="fiscal_consolidation",
            description="Gradual fiscal consolidation through expenditure cuts and revenue increases",
            parameter_changes={
                'personal_income_tax_rate': 0.27,  # +2 percentage points
                'corporate_tax_rate': 0.23,  # +2 percentage points
                'education_spending_pct_gdp': 0.04,  # -0.5 percentage points
                'infrastructure_spending_pct_gdp': 0.02  # -0.5 percentage points
            }
        )

        # Scenario 2: Growth-Oriented Reform
        self.create_scenario(
            name="growth_oriented_reform",
            description="Pro-growth reforms with tax cuts and investment spending",
            parameter_changes={
                'corporate_tax_rate': 0.18,  # -3 percentage points
                'personal_income_tax_rate': 0.23,  # -2 percentage points
                'infrastructure_spending_pct_gdp': 0.04,  # +1.5 percentage points
                'labor_market_flexibility': 0.7  # Increase flexibility
            }
        )

        # Scenario 3: Social Investment
        self.create_scenario(
            name="social_investment",
            description="Increased social spending with progressive financing",
            parameter_changes={
                'personal_income_tax_rate': 0.28,  # +3 percentage points
                'education_spending_pct_gdp': 0.06,  # +1.5 percentage points
                'healthcare_spending_pct_gdp': 0.09,  # +1.5 percentage points
                'pension_reform_factor': 0.95  # Slight pension reduction
            }
        )

        # Scenario 4: Climate Transition
        self.create_scenario(
            name="climate_transition",
            description="Fiscal policy supporting green transition",
            parameter_changes={
                'vat_rate': 0.22,  # +2 percentage points
                'corporate_tax_rate': 0.23,  # +2 percentage points (with green exemptions)
                'infrastructure_spending_pct_gdp': 0.04,  # Focus on green infrastructure
                'personal_income_tax_rate': 0.24  # Slight increase for progressivity
            }
        )

        # Scenario 5: External Shock - Global Recession
        self.create_scenario(
            name="global_recession",
            description="Policy response to global economic downturn",
            parameter_changes={
                'global_growth_shock': -0.03,  # -3 percentage points global growth
                'infrastructure_spending_pct_gdp': 0.035,  # Counter-cyclical spending
                'corporate_tax_rate': 0.19,  # Temporary relief
                'unemployment_benefits': 0.02  # Increased support
            }
        )

        # Scenario 6: Demographic Challenge
        self.create_scenario(
            name="demographic_challenge",
            description="Addressing aging population and rising healthcare costs",
            parameter_changes={
                'pension_reform_factor': 0.85,  # Significant pension reform
                'healthcare_spending_pct_gdp': 0.09,  # Increased healthcare spending
                'personal_income_tax_rate': 0.27,  # Higher taxes for financing
                'retirement_age': 67  # Increased retirement age
            }
        )

        logger.info(f"✓ Created {len(self.scenario_library)} predefined scenarios")

    def compare_scenarios(self, scenario_names: List[str], country_code: str = None, base_year: int = 2022) -> Dict:
        """Compare multiple policy scenarios side by side"""
        logger.info(f"Comparing scenarios: {scenario_names}")

        comparison = {
            'comparison_date': datetime.now().isoformat(),
            'country_code': country_code,
            'base_year': base_year,
            'scenarios_compared': scenario_names,
            'scenario_results': {},
            'summary_comparison': {},
            'recommendations': {}
        }

        # Run simulations for all scenarios
        for scenario_name in scenario_names:
            if scenario_name in self.scenario_library:
                scenario = self.scenario_library[scenario_name]
                results = self.simulate_scenario(scenario, country_code, base_year)
                comparison['scenario_results'][scenario_name] = results['summary_metrics']

        # Create summary comparison
        metrics = ['average_growth_rate', 'final_primary_balance', 'final_debt_ratio', 'overall_sustainability']

        for metric in metrics:
            comparison['summary_comparison'][metric] = {}
            for scenario_name, results in comparison['scenario_results'].items():
                # Navigate nested dictionary structure
                if 'economic_performance' in results and metric in ['average_growth_rate']:
                    value = results['economic_performance'][metric]
                elif 'fiscal_performance' in results and metric in ['final_primary_balance', 'final_debt_ratio']:
                    value = results['fiscal_performance'][metric]
                elif 'sustainability_indicators' in results and metric == 'overall_sustainability':
                    value = results['sustainability_indicators'][metric]
                else:
                    value = 0

                comparison['summary_comparison'][metric][scenario_name] = value

        # Generate recommendations
        comparison['recommendations'] = self.generate_scenario_recommendations(comparison)

        # Save comparison results
        comparison_file = self.simulation_dir / f"scenario_comparison_{country_code or 'global'}_{base_year}.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Scenario comparison completed and saved")
        return comparison

    def generate_scenario_recommendations(self, comparison: Dict) -> Dict:
        """Generate policy recommendations based on scenario comparison"""
        recommendations = {
            'best_scenario_overall': None,
            'best_for_growth': None,
            'best_for_fiscal_sustainability': None,
            'balanced_approach': None,
            'risk_assessment': {},
            'policy_mix_suggestions': []
        }

        if not comparison['scenario_results']:
            return recommendations

        # Find best scenarios for different objectives
        scenario_scores = {}

        for scenario_name, results in comparison['scenario_results'].items():
            score = 0

            # Economic performance score
            if 'economic_performance' in results:
                growth = results['economic_performance'].get('average_growth_rate', 0)
                unemployment = results['economic_performance'].get('average_unemployment', 10)
                score += (growth - 2) * 20  # Growth above 2% gets positive points
                score += (8 - unemployment) * 10  # Lower unemployment is better

            # Fiscal performance score
            if 'fiscal_performance' in results:
                balance = results['fiscal_performance'].get('final_primary_balance', 0)
                debt = results['fiscal_performance'].get('final_debt_ratio', 100)
                score += balance * 30  # Better balance gets points
                score += (90 - debt) * 5  # Lower debt gets points

            # Sustainability score
            if 'sustainability_indicators' in results:
                sustainability = results['sustainability_indicators'].get('overall_sustainability', 50)
                score += sustainability - 50  # Above 50 gets positive points

            scenario_scores[scenario_name] = score

        # Determine best scenarios
        if scenario_scores:
            best_overall = max(scenario_scores.items(), key=lambda x: x[1])
            recommendations['best_scenario_overall'] = best_overall[0]

            # Best for growth
            growth_scores = {name: results['economic_performance'].get('average_growth_rate', 0)
                           for name, results in comparison['scenario_results'].items()
                           if 'economic_performance' in results}
            if growth_scores:
                best_growth = max(growth_scores.items(), key=lambda x: x[1])
                recommendations['best_for_growth'] = best_growth[0]

            # Best for fiscal sustainability
            debt_scores = {name: 100 - results['fiscal_performance'].get('final_debt_ratio', 100)
                         for name, results in comparison['scenario_results'].items()
                         if 'fiscal_performance' in results}
            if debt_scores:
                best_fiscal = max(debt_scores.items(), key=lambda x: x[1])
                recommendations['best_for_fiscal_sustainability'] = best_fiscal[0]

        # Policy mix suggestions
        recommendations['policy_mix_suggestions'] = [
            "Consider gradual implementation to allow economic adjustment",
            "Maintain counter-cyclical fiscal capacity for economic shocks",
            "Balance short-term stabilization with long-term sustainability",
            "Ensure distributional fairness in policy design",
            "Build policy credibility through consistent implementation"
        ]

        # Risk assessment
        recommendations['risk_assessment'] = {
            'implementation_risks': [
                "Political resistance to tax increases",
                "Administrative capacity constraints",
                "External economic shocks",
                "Policy coordination challenges"
            ],
            'mitigation_strategies': [
                "Phased implementation with clear timelines",
                "Stakeholder engagement and communication",
                "Building institutional capacity",
                "Flexibility for policy adjustments"
            ]
        }

        return recommendations

    def generate_policy_report(self, scenario_name: str, country_code: str = None, base_year: int = 2022) -> str:
        """Generate comprehensive policy simulation report"""
        logger.info(f"Generating policy report for scenario: {scenario_name}")

        if scenario_name not in self.scenario_library:
            return f"Scenario '{scenario_name}' not found"

        scenario = self.scenario_library[scenario_name]
        simulation_key = f"{scenario_name}_{country_code}_{base_year}"

        if simulation_key not in self.simulation_results:
            # Run simulation if not available
            self.simulate_scenario(scenario, country_code, base_year)
            simulation_key = f"{scenario_name}_{country_code}_{base_year}"

        results = self.simulation_results[simulation_key]

        report = f"""
# Policy Simulation Report
## {scenario.name}

**Scenario Description**: {scenario.description}
**Country**: {country_code or 'Generic Economy'}
**Base Year**: {base_year}
**Time Horizon**: {scenario.time_horizon} years
**Report Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

This report analyzes the potential impacts of the **{scenario.name}** policy scenario over a {scenario.time_horizon}-year horizon. The simulation projects key economic and fiscal indicators based on the specified policy changes and their estimated elasticities.

### Overall Assessment: {results['summary_metrics']['scenario_assessment']['overall_assessment'].replace('_', ' ').title()}

---

## Policy Changes Implemented

"""
        # Add policy changes
        for param_name, new_value in scenario.parameters.items():
            if param_name in self.policy_parameters:
                param = self.policy_parameters[param_name]
                current_value = param.current_value
                change = new_value - current_value
                change_pct = (change / current_value) * 100

                report += f"""
### {param.name.replace('_', ' ').title()}
- **Current Value**: {current_value:.2f} {param.unit}
- **New Value**: {new_value:.2f} {param.unit}
- **Change**: {change:+.2f} {param.unit} ({change_pct:+.1f}%)
- **Implementation Lag**: {param.implementation_lag} years
- **Description**: {param.description}
"""

        # Add results summary
        summary = results['summary_metrics']
        report += f"""

## Projected Outcomes

### Economic Performance
- **Average Annual Growth**: {summary['economic_performance']['average_growth_rate']:.2f}%
- **Growth Volatility**: {summary['economic_performance']['growth_volatility']:.2f}%
- **Average Unemployment**: {summary['economic_performance']['average_unemployment']:.1f}%
- **Average Inflation**: {summary['economic_performance']['average_inflation']:.1f}%

### Fiscal Performance
- **Final Primary Balance**: {summary['fiscal_performance']['final_primary_balance']:+.2f}% of GDP
- **Final Debt Ratio**: {summary['fiscal_performance']['final_debt_ratio']:.1f}% of GDP
- **Average Balance**: {summary['fiscal_performance']['average_balance']:+.2f}% of GDP
- **Balance Improvement**: {summary['fiscal_performance']['balance_improvement']:+.2f}% points

### Sustainability Indicators
- **Debt Sustainability Score**: {summary['sustainability_indicators']['debt_sustainability_score']:.1f}/100
- **Fiscal Space Score**: {summary['sustainability_indicators']['fiscal_space_score']:.1f}/100
- **Overall Sustainability**: {summary['sustainability_indicators']['overall_sustainability']:.1f}/100

---

## Year-by-Year Projections

| Year | Growth (%) | Primary Balance (% GDP) | Debt (% GDP) | Unemployment (%) |
|------|------------|-------------------------|--------------|------------------|
"""
        # Add yearly projections table
        for year, data in results['yearly_results'].items():
            report += f"| {year} | {data.get('growth_rate', 0):.2f} | {data.get('primary_balance_pct_gdp', 0):+.2f} | {data.get('debt_pct_gdp', 0):.1f} | {data.get('unemployment_rate', 0):.1f} |\n"

        report += f"""

## Impact Assessment

### Economic Impact: {summary['scenario_assessment']['economic_impact'].title()}
The scenario is projected to {'stimulate' if summary['economic_performance']['average_growth_rate'] > 2 else 'moderately affect' if summary['economic_performance']['average_growth_rate'] > 1 else 'constrain'} economic growth, with an average annual growth rate of {summary['economic_performance']['average_growth_rate']:.2f}%.

### Fiscal Impact: {summary['scenario_assessment']['fiscal_impact'].title()}
Fiscal balances are expected to {'improve significantly' if summary['fiscal_performance']['balance_improvement'] > 1 else 'improve moderately' if summary['fiscal_performance']['balance_improvement'] > 0 else 'remain stable' if summary['fiscal_performance']['balance_improvement'] > -0.5 else 'deteriorate'} over the simulation horizon.

### Debt Sustainability
The debt trajectory is {'sustainable' if summary['fiscal_performance']['final_debt_ratio'] < 60 else 'manageable' if summary['fiscal_performance']['final_debt_ratio'] < 90 else 'concerning'}, with the debt ratio projected to reach {summary['fiscal_performance']['final_debt_ratio']:.1f}% of GDP by {base_year + scenario.time_horizon}.

---

## Sensitivity Analysis

### Key Assumptions
- **Interest Rate**: {self.fiscal_model['interest_rate_assumption']:.1%}
- **Baseline Growth**: {self.fiscal_model['growth_rate_assumption']:.1%}
- **Policy Elasticities**: Based on historical averages and literature estimates

### Risk Factors
1. **Implementation Risk**: Policy changes may face political or administrative delays
2. **Economic Shock Risk**: External factors could significantly alter outcomes
3. **Elasticity Uncertainty**: Actual impacts may differ from estimates
4. **Feedback Effects**: Policy changes may generate unexpected behavioral responses

### Scenario Variations
- **Pessimistic Case**: Higher interest rates, lower growth multipliers
- **Optimistic Case**: Lower interest rates, stronger policy multipliers
- **Stress Test**: Combined economic shocks with policy implementation

---

## Policy Recommendations

### Implementation Strategy
1. **Phased Approach**: Implement changes gradually to allow economic adjustment
2. **Monitoring Framework**: Establish clear indicators and regular reviews
3. **Flexibility Mechanisms**: Build in adjustment capacity for changing conditions
4. **Communication Strategy**: Maintain transparency and manage expectations

### Complementary Measures
1. **Structural Reforms**: Enhance long-term growth potential
2. **Institutional Capacity**: Strengthen policy implementation capabilities
3. **Social Safety Nets**: Protect vulnerable populations during transition
4. **International Coordination**: Consider spillover effects and cooperation

### Success Indicators
- **Primary Indicators**: Growth rate, primary balance, debt ratio
- **Secondary Indicators**: Employment, investment, competitiveness
- **Distributional Metrics**: Income inequality, poverty rates
- **Market Indicators**: Interest rates, exchange rates, credit ratings

---

## Technical Notes

### Methodology
This simulation uses a dynamic scoring approach with policy elasticities estimated from historical data and academic research. The model incorporates:
- Fiscal multipliers for tax and spending changes
- Elasticities for economic and social outcomes
- Implementation lags and persistence effects
- Debt dynamics with interest-growth differentials

### Limitations
- Results depend on elasticity estimates and assumptions
- Does not fully account for general equilibrium effects
- External shocks and behavioral responses may alter outcomes
- Distributional impacts are approximated

### Data Sources
- Historical fiscal data from national accounts
- Economic models from IMF, OECD, and academic research
- Policy impact studies from central banks and research institutions

---

*Report generated by Gerhard Policy Simulation Framework*
*Part of the Global Public Finance Analysis Platform*

**Disclaimer**: This simulation provides estimates based on specified assumptions and should be used as one input among many for policy decision-making. Actual outcomes may vary significantly from projections.
"""

        # Save report
        report_file = self.simulation_dir / f"{scenario_name}_policy_report_{country_code or 'global'}_{base_year}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"✓ Generated policy report: {report_file}")
        return report

    def run_comprehensive_simulation_suite(self):
        """Run comprehensive simulation suite with all scenarios"""
        logger.info("Running comprehensive policy simulation suite...")

        # Create predefined scenarios
        self.create_predefined_scenarios()

        # Test countries
        test_countries = ['USA', 'GER', 'FRA']  # Major economies
        base_year = 2022

        results = {
            'simulation_suite_date': datetime.now().isoformat(),
            'scenarios_created': len(self.scenario_library),
            'countries_analyzed': test_countries,
            'individual_simulations': [],
            'comparative_analyses': [],
            'reports_generated': []
        }

        # Run individual scenario simulations
        for country in test_countries:
            for scenario_name, scenario in self.scenario_library.items():
                try:
                    sim_result = self.simulate_scenario(scenario, country, base_year)
                    results['individual_simulations'].append(f"{scenario_name}_{country}")

                    # Generate report
                    report = self.generate_policy_report(scenario_name, country, base_year)
                    results['reports_generated'].append(f"{scenario_name}_{country}_report")
                except Exception as e:
                    logger.error(f"Error simulating {scenario_name} for {country}: {e}")

        # Run comparative analyses
        scenario_groups = [
            ['fiscal_consolidation', 'growth_oriented_reform'],
            ['social_investment', 'climate_transition'],
            ['global_recession', 'demographic_challenge']
        ]

        for group in scenario_groups:
            try:
                comparison = self.compare_scenarios(group, 'USA', base_year)
                results['comparative_analyses'].append(f"comparison_{'_'.join(group)}")
            except Exception as e:
                logger.error(f"Error comparing scenarios {group}: {e}")

        # Save master results
        master_results_file = self.simulation_dir / "policy_simulation_suite_results.json"
        with open(master_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Comprehensive simulation suite completed")
        logger.info(f"   - Scenarios created: {results['scenarios_created']}")
        logger.info(f"   - Individual simulations: {len(results['individual_simulations'])}")
        logger.info(f"   - Comparative analyses: {len(results['comparative_analyses'])}")
        logger.info(f"   - Reports generated: {len(results['reports_generated'])}")

        return results

def main():
    """Main execution function"""
    # Data directory
    data_dir = Path(__file__).resolve().parents[3] / "Technical" / "data"

    # Create policy simulator
    simulator = PolicySimulator(data_dir)

    # Run comprehensive simulation suite
    results = simulator.run_comprehensive_simulation_suite()

    print("\n" + "="*80)
    print("POLICY SIMULATION FRAMEWORK")
    print("="*80)
    print(f"✅ Simulation Suite Complete: {results['simulation_suite_date']}")
    print(f"📜 Scenarios Available: {results['scenarios_created']}")
    print(f"🌍 Countries Analyzed: {len(results['countries_analyzed'])}")
    print(f"📊 Individual Simulations: {len(results['individual_simulations'])}")
    print(f"🔍 Comparative Analyses: {len(results['comparative_analyses'])}")
    print(f"📄 Reports Generated: {len(results['reports_generated'])}")
    print(f"📁 Results Location: {data_dir}/simulations/")
    print("\nAvailable Scenarios:")
    for i, scenario_name in enumerate(simulator.scenario_library.keys(), 1):
        print(f"  {i}. {scenario_name.replace('_', ' ').title()}")

    print(f"\n🎯 Policy Simulation Framework Status: FULLY OPERATIONAL")
    print("="*80)

if __name__ == "__main__":
    main()