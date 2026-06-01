#!/usr/bin/env python3
"""
Machine Learning Fiscal Forecasting Pipeline
Advanced predictive models for fiscal data analysis and anomaly detection
"""

import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

# ML libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, IsolationForest
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

# Resolve project paths
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.config import project_root
from utils.paths import output_data_dir
from utils.logging_setup import setup_logging

logger = setup_logging(__name__)

# For advanced models
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not available. Will use alternative models.")

class FiscalMLPipeline:
    """Machine Learning pipeline for fiscal forecasting and analysis"""

    def __init__(self, data_dir: Path, models_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir)
        self.models_dir = models_dir or self.data_dir / "ml_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Data sources
        self.data_sources = {}
        self.processed_data = {}

        # ML models
        self.models = {}
        self.scalers = {}
        self.feature_columns = []

        # Model configurations
        self.model_configs = {
            'revenue_forecasting': {
                'target': 'revenue_pct_gdp',
                'features': ['year', 'lag_1', 'lag_2', 'lag_3', 'rolling_mean_3', 'rolling_std_3'],
                'models': ['Linear', 'RandomForest', 'GradientBoosting', 'XGBoost'],
                'test_size': 0.2,
                'cv_folds': 5
            },
            'expenditure_forecasting': {
                'target': 'expenditure_pct_gdp',
                'features': ['year', 'lag_1', 'lag_2', 'lag_3', 'rolling_mean_3', 'revenue_pct_gdp'],
                'models': ['Linear', 'RandomForest', 'GradientBoosting', 'XGBoost'],
                'test_size': 0.2,
                'cv_folds': 5
            },
            'deficit_forecasting': {
                'target': 'deficit_pct_gdp',
                'features': ['year', 'lag_1', 'lag_2', 'revenue_pct_gdp', 'expenditure_pct_gdp', 'debt_pct_gdp'],
                'models': ['Linear', 'RandomForest', 'GradientBoosting', 'XGBoost'],
                'test_size': 0.2,
                'cv_folds': 5
            },
            'sustainability_scoring': {
                'target': 'sustainability_score',
                'features': ['revenue_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp', 'expenditure_pct_gdp'],
                'models': ['RandomForest', 'GradientBoosting'],
                'test_size': 0.25,
                'cv_folds': 5
            },
            'anomaly_detection': {
                'target': 'all_features',
                'features': None,  # Will use all available
                'models': ['IsolationForest'],
                'contamination': 0.1
            }
        }

        # Load data
        self.load_data_sources()

    def load_data_sources(self):
        """Load all available data sources"""
        logger.info("Loading data sources for ML pipeline...")

        out_dir = output_data_dir()

        # Load fiscal balances
        balances_file = out_dir / "fiscal_balances_master_dataset.xlsx"
        if balances_file.exists():
            self.data_sources['fiscal_balances'] = pd.read_excel(balances_file)
            logger.info(f"Loaded fiscal balances: {len(self.data_sources['fiscal_balances'])} observations")

        # Load country rankings
        rankings_file = out_dir / "global_tax_rankings.xlsx"
        if rankings_file.exists():
            self.data_sources['rankings'] = pd.read_excel(rankings_file)
            logger.info(f"Loaded rankings: {len(self.data_sources['rankings'])} observations")

        # Load world bank data
        worldbank_file = out_dir / "world_bank_tax_revenue.xlsx"
        if worldbank_file.exists():
            self.data_sources['worldbank_tax'] = pd.read_excel(worldbank_file)
            logger.info(f"Loaded World Bank data: {len(self.data_sources['worldbank_tax'])} observations")

        logger.info(f" Loaded {len(self.data_sources)} data sources for ML pipeline")

    def prepare_data_for_modeling(self, model_type: str, country_code: Optional[str] = None) -> pd.DataFrame:
        """Prepare data for specific modeling task"""
        logger.info(f"Preparing data for {model_type} modeling...")

        config = self.model_configs[model_type]
        target_col = config['target']

        # Get base data
        if model_type in ['revenue_forecasting', 'expenditure_forecasting', 'deficit_forecasting', 'sustainability_scoring']:
            base_df = self.data_sources.get('fiscal_balances', pd.DataFrame())
        else:
            base_df = pd.concat([df for df in self.data_sources.values()], ignore_index=True)

        if len(base_df) == 0:
            raise ValueError(f"No data available for {model_type}")

        # Filter by country if specified
        if country_code:
            if 'country_code' in base_df.columns:
                base_df = base_df[base_df['country_code'] == country_code.upper()].copy()
            else:
                logger.warning(f"country_code column not found. Using all data.")

        # Sort by year
        if 'year' in base_df.columns:
            base_df = base_df.sort_values('year').reset_index(drop=True)

        # Ensure target column exists
        if target_col not in base_df.columns:
            logger.error(f"Target column '{target_col}' not found in data")
            return pd.DataFrame()

        # Remove rows with missing target values
        initial_len = len(base_df)
        base_df = base_df.dropna(subset=[target_col])
        logger.info(f"Removed {initial_len - len(base_df)} rows with missing {target_col}")

        if len(base_df) < 10:
            logger.warning(f"Insufficient data for {model_type}: {len(base_df)} rows")
            return pd.DataFrame()

        # Create features
        processed_df = self.create_features(base_df, config)

        # Filter to required features
        available_features = [f for f in config['features'] if f in processed_df.columns]
        required_cols = available_features + [target_col]

        if len(required_cols) < 2:
            logger.error(f"Insufficient features for {model_type}. Available: {available_features}")
            return pd.DataFrame()

        final_df = processed_df[required_cols].dropna()

        logger.info(f" Prepared data for {model_type}: {len(final_df)} rows, {len(required_cols)} features")
        return final_df

    def create_features(self, df: pd.DataFrame, config: Dict) -> pd.DataFrame:
        """Create ML features from fiscal data"""
        logger.info("Creating ML features...")

        feature_df = df.copy()

        # Time-based features
        if 'year' in feature_df.columns:
            feature_df['decade'] = (feature_df['year'] // 10) * 10
            feature_df['year_since_2000'] = feature_df['year'] - 2000

        # Lag features (time series)
        for lag in [1, 2, 3]:
            for col in ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']:
                lag_col = f'lag_{lag}_{col}'
                if col in feature_df.columns:
                    feature_df[lag_col] = feature_df[col].shift(lag)

        # Rolling statistics
        for window in [3, 5]:
            for col in ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']:
                if col in feature_df.columns:
                    feature_df[f'rolling_mean_{window}_{col}'] = feature_df[col].rolling(window=window).mean()
                    feature_df[f'rolling_std_{window}_{col}'] = feature_df[col].rolling(window=window).std()
                    feature_df[f'rolling_min_{window}_{col}'] = feature_df[col].rolling(window=window).min()
                    feature_df[f'rolling_max_{window}_{col}'] = feature_df[col].rolling(window=window).max()

        # Ratio features
        if 'revenue_pct_gdp' in feature_df.columns and 'expenditure_pct_gdp' in feature_df.columns:
            feature_df['revenue_expenditure_ratio'] = (
                feature_df['revenue_pct_gdp'] / feature_df['expenditure_pct_gdp'].replace(0, np.nan)
            )

        if 'debt_pct_gdp' in feature_df.columns and 'deficit_pct_gdp' in feature_df.columns:
            feature_df['debt_deficit_ratio'] = (
                feature_df['debt_pct_gdp'] / feature_df['deficit_pct_gdp'].replace(0, np.nan)
            )

        # Growth rates
        for col in ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']:
            if col in feature_df.columns and 'year' in feature_df.columns:
                feature_df = feature_df.sort_values('year')
                feature_df[f'{col}_growth_rate'] = feature_df[col].pct_change()

        # Economic indicators
        if 'revenue_pct_gdp' in feature_df.columns and 'expenditure_pct_gdp' in feature_df.columns:
            feature_df['fiscal_stress'] = feature_df['deficit_pct_gdp'] - feature_df['debt_pct_gdp'] * 0.05
            feature_df['tax_burden'] = feature_df['revenue_pct_gdp'] / 100
            feature_df['government_size'] = feature_df['expenditure_pct_gdp'] / 100

        # Policy indicators
        if 'deficit_pct_gdp' in feature_df.columns:
            feature_df['deficit_severity'] = pd.cut(
                feature_df['deficit_pct_gdp'],
                bins=[-np.inf, -6, -3, 0, np.inf],
                labels=['critical', 'high', 'moderate', 'low']
            )

        logger.info(f" Created {len(feature_df.columns) - len(df.columns)} new features")
        return feature_df

    def train_model(self, model_type: str, country_code: Optional[str] = None) -> Dict:
        """Train models for specific task"""
        logger.info(f"Training models for {model_type}...")

        # Prepare data
        data = self.prepare_data_for_modeling(model_type, country_code)

        if len(data) == 0:
            raise ValueError(f"Insufficient data for {model_type}")

        config = self.model_configs[model_type]
        target_col = config['target']
        feature_cols = [f for f in config['features'] if f in data.columns]

        # Prepare X and y
        X = data[feature_cols]
        y = data[target_col]

        # Remove rows with missing values
        mask = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[mask]
        y = y[mask]

        if len(X) < 10:
            raise ValueError(f"Insufficient clean data for {model_type}: {len(X)} rows")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=config['test_size'], random_state=42
        )

        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Train models
        models = {}
        results = {}

        for model_name in config['models']:
            try:
                logger.info(f"Training {model_name} model...")

                if model_name == 'Linear':
                    model = LinearRegression()
                elif model_name == 'Ridge':
                    model = Ridge()
                elif model_name == 'Lasso':
                    model = Lasso()
                elif model_name == 'RandomForest':
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                elif model_name == 'GradientBoosting':
                    model = GradientBoostingRegressor(random_state=42)
                elif model_name == 'XGBoost':
                    if not XGBOOST_AVAILABLE:
                        logger.warning("XGBoost not available, skipping...")
                        continue
                    model = xgb.XGBRegressor(random_state=42, n_estimators=100)
                else:
                    logger.warning(f"Unknown model type: {model_name}")
                    continue

                # Train model
                model.fit(X_train_scaled, y_train)

                # Predictions
                y_pred = model.predict(X_test_scaled)

                # Evaluate
                mse = mean_squared_error(y_test, y_pred)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)

                # Cross-validation
                cv_scores = cross_val_score(model, X_train_scaled, y_train,
                                         cv=config['cv_folds'], scoring='neg_mean_squared_error')
                cv_rmse = np.sqrt(-cv_scores.mean())

                models[model_name] = model
                self.scalers[f"{model_type}_{model_name}"] = scaler

                results[model_name] = {
                    'model': model,
                    'mse': mse,
                    'mae': mae,
                    'r2': r2,
                    'rmse': np.sqrt(mse),
                    'cv_rmse': cv_rmse,
                    'training_samples': len(X_train),
                    'test_samples': len(X_test),
                    'features': feature_cols
                }

                logger.info(f" {model_name}: R²={r2:.3f}, RMSE={cv_rmse:.3f}")

            except Exception as e:
                logger.error(f"Error training {model_name}: {e}")
                continue

        # Find best model
        if results:
            best_model_name = max(results.keys(), key=lambda k: results[k]['r2'])
            best_model = results[best_model_name]

            # Save best model
            model_path = self.models_dir / f"{model_type}_{country_code or 'global'}_best_model.joblib"
            joblib.dump(best_model['model'], model_path)

            scaler_path = self.models_dir / f"{model_type}_{country_code or 'global'}_ scaler.joblib"
            joblib.dump(self.scalers[f"{model_type}_{best_model_name}"], scaler_path)

            # Save results
            results_path = self.models_dir / f"{model_type}_{country_code or 'global'}_results.json"
            with open(results_path, 'w') as f:
                # Convert numpy types to Python types for JSON serialization
                json_serializable_results = {}
                for model_name, result in results.items():
                    json_serializable_results[model_name] = {
                        'mse': float(result['mse']),
                        'mae': float(result['mae']),
                        'r2': float(result['r2']),
                        'rmse': float(result['rmse']),
                        'cv_rmse': float(result['cv_rmse']),
                        'training_samples': int(result['training_samples']),
                        'test_samples': int(result['test_samples']),
                        'features': result['features']
                    }
                json.dump(json_serializable_results, f, indent=2)

            logger.info(f" Saved best model: {best_model_name} (R²={best_model['r2']:.3f})")
            logger.info(f" Results saved to: {results_path}")

            return {
                'best_model': best_model_name,
                'model_results': results,
                'model_path': str(model_path),
                'scaler_path': str(scaler_path),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features': feature_cols
            }

        else:
            raise ValueError("No models were successfully trained")

    def detect_anomalies(self, model_type: str = 'anomaly_detection', country_code: Optional[str] = None) -> Dict:
        """Detect fiscal anomalies using isolation forest"""
        logger.info(f"Detecting anomalies for {model_type}...")

        # Prepare data
        data = self.prepare_data_for_modeling(model_type, country_code)

        if len(data) == 0:
            raise ValueError(f"No data available for anomaly detection")

        config = self.model_configs[model_type]
        feature_cols = [col for col in data.columns if col != 'year' and pd.api.types.is_numeric_dtype(data[col])]

        if not feature_cols:
            raise ValueError("No numeric features available for anomaly detection")

        X = data[feature_cols].dropna()

        if len(X) < 10:
            raise ValueError("Insufficient data for anomaly detection")

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Train isolation forest
        contamination = config.get('contamination', 0.1)
        model = IsolationForest(contamination=contamination, random_state=42)
        model.fit(X_scaled)

        # Predict anomalies
        anomaly_predictions = model.predict(X_scaled)
        anomaly_scores = model.decision_function(X_scaled)

        # Create results
        results = {
            'model': model,
            'scaler': scaler,
            'anomalies_detected': sum(anomaly_predictions == -1),
            'total_samples': len(X),
            'contamination_rate': contamination,
            'feature_importance': None,
            'anomaly_threshold': None
        }

        # Add original data back for analysis
        data_copy = X.copy()
        data_copy['is_anomaly'] = anomaly_predictions
        data_copy['anomaly_score'] = anomaly_scores

        # Calculate threshold
        results['anomaly_threshold'] = np.percentile(anomaly_scores, (1 - contamination) * 100)

        # Feature importance (if available)
        if hasattr(model, 'feature_importances_'):
            results['feature_importance'] = dict(zip(feature_cols, model.feature_importances_))

        # Save model
        model_path = self.models_dir / f"{model_type}_{country_code or 'global'}_ anomaly_model.joblib"
        joblib.dump(model, model_path)

        scaler_path = self.models_dir / f"{model_type}_{country_code or 'global'}_ anomaly_scaler.joblib"
        joblib.dump(scaler, scaler_path)

        # Save results
        anomalies_path = self.models_dir / f"{model_type}_{country_code or 'global'}_anomalies.json"

        # Prepare anomalies data for JSON
        anomalies_data = data_copy[data_copy['is_anomaly'] == True].to_dict('records')

        with open(anomalies_path, 'w') as f:
            json.dump({
                'anomalies': anomalies_data,
                'total_detected': len(anomalies_data),
                'threshold': float(results['anomaly_threshold']),
                'detection_date': datetime.now().isoformat(),
                'features_used': feature_cols
            }, f, indent=2)

        logger.info(f" Detected {results['anomalies_detected']} anomalies out of {results['total_samples']} samples")
        return results

    def forecast_fiscal_data(self, model_type: str, country_code: Optional[str] = None,
                           years_ahead: int = 5) -> Dict:
        """Forecast fiscal data using trained models"""
        logger.info(f"Forecasting fiscal data for {model_type}...")

        # Load trained model
        model_path = self.models_dir / f"{model_type}_{country_code or 'global'}_best_model.joblib"
        scaler_path = self.models_dir / f"{model_type}_{country_code or 'global'}_ scaler.joblib"

        if not model_path.exists() or not scaler_path.exists():
            raise ValueError(f"No trained model found for {model_type}. Train model first.")

        try:
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)

            # Load results to get feature columns
            results_path = self.models_dir / f"{model_type}_{country_code or 'global'}_results.json"
            with open(results_path, 'r') as f:
                results = json.load(f)

            best_model_name = results['best_model']
            feature_cols = results['best_model']['features']

            # Get latest data
            latest_data = self.prepare_data_for_modeling(model_type, country_code)

            if len(latest_data) == 0:
                raise ValueError(f"No data available for forecasting {model_type}")

            # Create future scenarios
            forecasts = {}
            target_col = self.model_configs[model_type]['target']

            for year_ahead in range(1, years_ahead + 1):
                # Get last available data
                last_row = latest_data.iloc[-1:].copy()

                # Simple extrapolation for features
                future_row = last_row.copy()

                # Update year
                if 'year' in future_row:
                    future_row['year'] = last_row['year'].iloc[0] + year_ahead

                # Update lag features (simple extrapolation)
                for lag in [1, 2, 3]:
                    lag_col = f'lag_{lag}_'
                    for base_col in ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']:
                        full_lag_col = f"{lag_col}{base_col}"
                        if full_lag_col in latest_data.columns and base_col in last_row.columns:
                            if lag == 1:
                                future_row[full_lag_col] = last_row[base_col].iloc[0]
                            elif lag == 2 and f'lag_{lag-1}_{base_col}' in last_row.columns:
                                future_row[full_lag_col] = last_row[f'lag_{lag-1}_{base_col}'].iloc[0]

                # Update rolling statistics (use last available)
                for window in [3, 5]:
                    for base_col in ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp']:
                        if base_col in last_row.columns:
                            future_row[f'rolling_mean_{window}_{base_col}'] = last_row[base_col].iloc[0]

                # Prepare features for prediction
                feature_data = future_row[feature_cols].dropna()

                if len(feature_data) == 0:
                    continue

                # Scale features
                feature_data_scaled = scaler.transform(feature_data)

                # Make prediction
                prediction = model.predict(feature_data)[0]

                # Add uncertainty estimation (using training error)
                results_data = results.get('model_results', {})
                if best_model_name in results_data:
                    rmse = results_data[best_model_name].get('rmse', 0)
                    # Simple uncertainty band (±RMSE)
                    future_row[f'{target_col}_forecast'] = prediction
                    future_row[f'{target_col}_lower_bound'] = prediction - rmse
                    future_row[f'{target_col}_upper_bound'] = prediction + rmse

                    forecasts[year_ahead] = {
                        'year': int(future_row['year'].iloc[0]),
                        'forecast': float(prediction),
                        'lower_bound': float(prediction - rmse),
                        'upper_bound': float(prediction + rmse),
                        'features_used': feature_cols,
                        'confidence_interval': f"±{rmse:.3f}"
                    }

            # Save forecasts
            forecasts_path = self.models_dir / f"{model_type}_{country_code or 'global'}_forecasts.json"
            with open(forecasts_path, 'w') as f:
                json.dump({
                    'forecast_date': datetime.now().isoformat(),
                    'model_type': model_type,
                    'country_code': country_code or 'global',
                    'years_ahead': years_ahead,
                    'forecasts': forecasts,
                    'methodology': 'Linear extrapolation with ML model predictions',
                    'uncertainty': 'Based on training RMSE'
                }, f, indent=2)

            logger.info(f" Generated forecasts for {years_ahead} years ahead")
            return forecasts

        except Exception as e:
            logger.error(f"Error generating forecasts: {e}")
            raise

    def run_complete_pipeline(self, country_code: Optional[str] = None):
        """Run complete ML pipeline"""
        logger.info(" Starting complete ML pipeline...")

        pipeline_results = {}

        # Training results
        training_tasks = [
            'revenue_forecasting',
            'expenditure_forecasting',
            'deficit_forecasting',
            'sustainability_scoring'
        ]

        for task in training_tasks:
            try:
                logger.info(f"Training {task}...")
                result = self.train_model(task, country_code)
                pipeline_results[task] = result
                logger.info(f" Completed {task}: R²={result['model_results'][result['best_model']]['r2']:.3f}")
            except Exception as e:
                logger.error(f" Failed {task}: {e}")
                pipeline_results[task] = {'error': str(e)}

        # Anomaly detection
        try:
            logger.info("Running anomaly detection...")
            anomaly_result = self.detect_anomalies('anomaly_detection', country_code)
            pipeline_results['anomaly_detection'] = anomaly_result
            logger.info(f" Anomaly detection complete: {anomaly_result['anomalies_detected']} anomalies")
        except Exception as e:
            logger.error(f" Anomaly detection failed: {e}")
            pipeline_results['anomaly_detection'] = {'error': str(e)}

        # Forecasting
        forecast_tasks = ['revenue_forecasting', 'expenditure_forecasting', 'deficit_forecasting']

        for task in forecast_tasks:
            if task in pipeline_results and 'error' not in pipeline_results[task]:
                try:
                    logger.info(f"Generating forecasts for {task}...")
                    forecasts = self.forecast_fiscal_data(task, country_code, years_ahead=5)
                    pipeline_results[f'{task}_forecasts'] = forecasts
                    logger.info(f" Generated {task} forecasts for 5 years")
                except Exception as e:
                    logger.error(f" Forecast generation failed for {task}: {e}")
                    pipeline_results[f'{task}_forecasts'] = {'error': str(e)}

        # Save pipeline results
        results_path = self.models_dir / f"pipeline_results_{country_code or 'global'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_path, 'w') as f:
            # Convert to JSON-serializable format
            json_results = {}
            for key, value in pipeline_results.items():
                if isinstance(value, dict):
                    if 'error' not in value:
                        json_results[key] = {
                            'status': 'success',
                            'data': {
                                k: v if not isinstance(v, np.floating) else float(v) if not pd.isna(v) else None
                                for k, v in value.items()
                            }
                        }
                    else:
                        json_results[key] = value
                else:
                    json_results[key] = value

            json.dump(json_results, f, indent=2)

        logger.info(f" Complete ML pipeline finished. Results saved to: {results_path}")

        # Summary
        successful_tasks = sum(1 for result in pipeline_results.values()
                            if isinstance(result, dict) and 'error' not in result)
        logger.info(f"Pipeline Summary: {successful_tasks}/{len(pipeline_results)} tasks successful")

        return pipeline_results

def main():
    """Main execution function"""
    # Data directory resolved from project utils
    data_dir = project_root() / "Technical" / "data"

    # Create and run ML pipeline
    ml_pipeline = FiscalMLPipeline(data_dir)

    # Run pipeline for global data
    results = ml_pipeline.run_complete_pipeline()

    # You can also run for specific countries:
    # results = ml_pipeline.run_complete_pipeline(country_code='US')

    return results

if __name__ == "__main__":
    results = main()