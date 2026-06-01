# Integrated Fiscal Analysis
**Created**: October 10, 2025 | **Expanded**: May 4, 2026
**Purpose**: Unified analysis of taxes, expenditures, and public debt
**Economic Foundation**: Government Budget Constraint

---

## Analysis Suite (A01–A10)

Added 2026-05-04. Ten analytical modules using Gerhard's 4.37 GB of existing data.

```bash
cd Technical/src
python -m integrated_fiscal.run_all              # Run all 10 modules
python -m integrated_fiscal.run_all A01 A05 A08  # Run specific modules
python -m integrated_fiscal.run_all --list       # List modules
```

| Module | Analysis | Data | Key Finding |
|--------|----------|------|-------------|
| A01 | Expenditure Composition | WB (200 countries) | 65 years of convergence patterns |
| A02 | Military-Fiscal Tradeoffs | WB military | 1.17% GDP avg peace dividend, 73 nations above NATO 2% |
| A03 | Fiscal Sustainability | WDI debt+fiscal | 544 consolidation episodes identified |
| A04 | Tax Structure Evolution | WDI fiscal | 189 countries: modernization trajectory mapped |
| A05 | COFOG Functional (EU) | Eurostat 210MB | 30 EU countries, welfare typology × austerity impact |
| A06 | WID Distribution | WID 4.1GB | 23 countries: inequality-fiscal nexus, labor share trends |
| A07 | US Deep Fiscal | PSZ/DINA 20MB | 1913-2022 distributional accounts |
| A08 | Cross-Country Convergence | All WB | Beta-convergence confirmed (β=-0.02, p<0.001) |
| A09 | Fiscal Cyclicality | WDI national accounts | Pro/counter-cyclicality by income group |
| A10 | Debt Dynamics Decomposition | WDI panels | Fiscal balance panel, 211 countries |

Output: `Output/Data/integrated_fiscal/` (31 Excel files, one-sheet each)

---

---

## Overview

This module provides **integrated fiscal analysis** that combines:
1. **Tax Revenue Analysis** - Who pays and how much
2. **Government Expenditure Analysis** - What government spends on
3. **Public Debt Analysis** - How deficits are financed

### Economic Rationale

These three components are inseparable, connected by the **government budget constraint**:

```
Tax Revenue (T) - Government Spending (G) = -ΔDebt + Other Financing
```

**Implications**:
- Debt analysis IS tax/expenditure analysis
- You cannot understand public debt without understanding tax revenue
- You cannot assess tax policy without considering debt sustainability
- Comprehensive fiscal analysis requires all three components

---

## Modules

### 1. unified_fiscal_analysis.py
**Purpose**: Integrated analysis combining all fiscal components

**Key Classes**:
- `UnifiedFiscalAnalyzer` - Main analyzer combining tax, expenditure, and debt data
- `FiscalPolicyScenario` - Model policy scenarios and their fiscal effects

**Capabilities**:
- Load and integrate data from multiple sources
- Calculate fiscal balance (T - G)
- Calculate primary balance (excludes interest payments)
- Verify budget constraint
- Assess debt sustainability
- Generate comprehensive fiscal reports

**Usage**:
```python
from unified_fiscal_analysis import UnifiedFiscalAnalyzer

analyzer = UnifiedFiscalAnalyzer()
analyzer.load_tax_data()
analyzer.load_expenditure_data()
analyzer.load_debt_data()

fiscal_balance = analyzer.calculate_fiscal_balance()
sustainability = analyzer.assess_debt_sustainability()
report = analyzer.generate_fiscal_report()
```

### 2. government_budget_constraint.py
**Purpose**: Verify and analyze the government budget constraint

**Key Classes**:
- `BudgetConstraintAnalyzer` - Analyzes T - G = -ΔD relationship

**Capabilities**:
- Calculate fiscal balance
- Calculate debt changes
- Verify budget constraint holds
- Decompose discrepancies
- Analyze financing sources
- Visualize relationships

**Usage**:
```python
from government_budget_constraint import BudgetConstraintAnalyzer

analyzer = BudgetConstraintAnalyzer(tax_data, expenditure_data, debt_data)
verification = analyzer.verify_budget_constraint()
analyzer.plot_budget_constraint()
```

### 3. fiscal_sustainability.py
**Purpose**: Assess long-term fiscal sustainability

**Key Classes**:
- `FiscalSustainabilityAnalyzer` - Debt dynamics and sustainability analysis

**Capabilities**:
- Calculate required primary balance for debt stabilization
- Project future debt paths
- Assess sustainability status
- Compare policy scenarios
- Visualize sustainability

**Usage**:
```python
from fiscal_sustainability import FiscalSustainabilityAnalyzer

analyzer = FiscalSustainabilityAnalyzer(
    initial_debt_gdp=1.20,
    avg_interest_rate=0.03,
    avg_growth_rate=0.02
)

required_pb = analyzer.calculate_required_primary_balance()
assessment = analyzer.assess_sustainability(current_primary_balance=-3.0)
```

---

## Analytical Framework

### The Government Budget Constraint

**Basic Form**:
```
T - G = -ΔD
```

Where:
- T = Tax revenue
- G = Government spending (including interest)
- ΔD = Change in debt

**Expanded Form**:
```
T - G = -ΔD + ΔM + ΔB
```

Where:
- ΔM = Change in monetary base (seigniorage)
- ΔB = Change in foreign reserves

**Primary Balance**:
```
Primary Balance = T - (G - i*D)
```

Where i*D = interest payments on debt

### Debt Dynamics

**Debt Sustainability Condition**:
```
d_t = [(1 + r)/(1 + g)] * d_(t-1) - pb_t
```

Where:
- d_t = debt-to-GDP ratio at time t
- r = real interest rate
- g = real GDP growth rate
- pb_t = primary balance as fraction of GDP

**Required Primary Balance for Stability**:
```
pb* = (r - g) * d
```

Key insight: When r > g, maintaining stable debt requires primary surplus

---

## Data Requirements

### Input Data

#### Tax Revenue Data
- Source: `Output/Data/` (from tax analysis modules)
- Required fields:
  - Year
  - Total tax revenue
  - Tax revenue by type (income, payroll, corporate, etc.)

#### Government Expenditure Data
- Source: external data store (`Output/Data/external/`)
- Required fields:
  - Year
  - Total expenditure
  - Interest payments
  - Primary expenditure

#### Public Debt Data
- Source: MSPD module (`Analysis_Modules/MSPD/Output/Data/`)
- Required fields:
  - Year
  - Total outstanding debt
  - Debt by type (marketable, non-marketable)
  - Interest rates

#### GDP Data (for normalization)
- Source: external data store
- Required fields:
  - Year
  - Nominal GDP
  - Real GDP

### Output Data

All analysis outputs saved to:
```
Output/Data/Integrated_Fiscal/
```

**Files Generated**:
- `fiscal_report_[timestamp].xlsx` - Comprehensive fiscal analysis
- `budget_constraint_verification.xlsx` - Budget constraint tests
- `sustainability_assessment.xlsx` - Sustainability metrics
- Various visualization PNG files

---

## Integration with Other Modules

### Tax Analysis (`Technical/src/tax_analysis/`)
- Provides detailed tax revenue data
- Distributional analysis by income group
- Tax policy scenarios

### Debt Analysis (`Technical/src/debt_analysis/`)
- Public debt composition
- Duration and maturity analysis
- Debt management metrics

### MSPD Module (`Analysis_Modules/MSPD/`)
- Monthly Statement of Public Debt data
- Historical debt series
- Original R analysis preserved in `Technical/archive/original_analysis/debt/`

### External Data (`Output/Data/external/`)
- BEA fiscal accounts
- Treasury data
- GDP and macroeconomic data

---

## Example Workflows

### Workflow 1: Comprehensive Fiscal Assessment

```python
# 1. Load all data
analyzer = UnifiedFiscalAnalyzer()
analyzer.load_tax_data()
analyzer.load_expenditure_data()
analyzer.load_debt_data()

# 2. Calculate fiscal position
fiscal_balance = analyzer.calculate_fiscal_balance()
primary_balance = analyzer.calculate_primary_balance(interest_data)

# 3. Verify budget constraint
verification = analyzer.verify_budget_constraint()

# 4. Assess sustainability
sustainability = analyzer.assess_debt_sustainability(projection_years=10)

# 5. Generate report
report_path = analyzer.generate_fiscal_report()
```

### Workflow 2: Budget Constraint Analysis

```python
# 1. Initialize analyzer
bc_analyzer = BudgetConstraintAnalyzer(tax_data, exp_data, debt_data)

# 2. Verify constraint
fiscal_balance = bc_analyzer.calculate_fiscal_balance()
debt_changes = bc_analyzer.calculate_debt_changes()
verification = bc_analyzer.verify_budget_constraint()

# 3. Analyze discrepancies
decomposition = bc_analyzer.decompose_discrepancies()

# 4. Visualize
bc_analyzer.plot_budget_constraint(output_path="budget_constraint.png")
```

### Workflow 3: Sustainability Analysis

```python
# 1. Set up parameters
sustainability_analyzer = FiscalSustainabilityAnalyzer(
    initial_debt_gdp=1.20,
    avg_interest_rate=0.03,
    avg_growth_rate=0.02
)

# 2. Calculate required adjustments
required_pb = sustainability_analyzer.calculate_required_primary_balance()

# 3. Assess current policy
assessment = sustainability_analyzer.assess_sustainability(
    current_primary_balance=-3.0
)

# 4. Compare scenarios
scenarios = {
    'Baseline': {'pb': -3.0, 'r': 0.03, 'g': 0.02},
    'Reform': {'pb': -1.0, 'r': 0.03, 'g': 0.025},
    'Crisis': {'pb': -5.0, 'r': 0.05, 'g': 0.01}
}
comparison = sustainability_analyzer.scenario_analysis(scenarios, years=20)

# 5. Visualize
sustainability_analyzer.plot_sustainability(
    current_primary_balance=-3.0,
    output_path="sustainability.png"
)
```

---

## Connection to Original Work

This integrated approach builds on:

### Original Tax Analysis
- Detailed distributional analysis
- Tax burden by income group
- International comparisons

### Original MSPD Analysis (R code)
- Duration analysis of debt portfolio
- Maturity structure evolution
- Market vs non-marketable securities

**Preserved in**: `Technical/archive/original_analysis/debt/`

**Evolution**: Original R methods inform current Python implementation while adding integration with tax/expenditure analysis

---

## Best Practices

### Data Consistency
1. **Use the external data store as source of truth** for government data
2. **Document data downloads** in `Output/Data/external/CHECKOUT_RECEIPT.md`
3. **Verify data alignment** across tax, expenditure, and debt series
4. **Check budget constraint** - discrepancies indicate data issues

### Analysis Standards
1. **Report both levels and ratios** (absolute amounts and % of GDP)
2. **Include uncertainty** when projecting
3. **Document assumptions** clearly in all scenario analysis
4. **Validate results** against authoritative sources

### Reproducibility
1. **Save all parameters** used in analysis
2. **Version control code** changes
3. **Document data sources** completely
4. **Preserve intermediate results**

---

## References

### Economic Literature
- Blanchard, O. (2019). "Public Debt and Low Interest Rates"
- IMF (2013). "Staff Guidance Note for Public Debt Sustainability Analysis"
- Escolano, J. (2010). "A Practical Guide to Public Debt Dynamics, Fiscal Sustainability, and Cyclical Adjustment of Budgetary Aggregates"

### Related Documentation
- `../../archive/original_analysis/README.md` - Original analysis preservation
- `../../../Analysis_Modules/MSPD/` - MSPD module documentation
- `../../../Output/Data/external/CHECKOUT_RECEIPT.md` - Data sources

### Data Standards
- Government budget constraint verification
- Integrated fiscal analysis patterns
- Data checkout and lineage tracking

---

## Future Enhancements

### Planned Features
1. **Stochastic debt projections** - Monte Carlo simulation of debt paths
2. **Generational accounting** - Long-term fiscal burdens by cohort
3. **International comparisons** - Cross-country fiscal sustainability
4. **State/local integration** - Include sub-national fiscal data

### Research Applications
1. **Climate fiscal impact** - Cost of climate adaptation
2. **Demographic transitions** - Aging population effects
3. **Tax reform scenarios** - Revenue effects and debt implications
4. **Expenditure efficiency** - Spending quality and fiscal space

---

## Support

### Questions?
- **Methodology**: Review economic literature references
- **Code usage**: See example workflows above
- **Data issues**: Check the data download receipt
- **Integration**: Consult main project documentation

### Issues?
- **Data not found**: Verify data download completed
- **Budget constraint fails**: Check data alignment
- **Projections unrealistic**: Review parameter assumptions

---

**Status**: Active Module ✅
**Created**: October 10, 2025
**Language**: Python 3.8+
**Dependencies**: pandas, numpy, matplotlib, seaborn

---

*This module demonstrates that comprehensive fiscal analysis requires integrating tax, expenditure, and debt - three sides of the same government budget constraint.*
