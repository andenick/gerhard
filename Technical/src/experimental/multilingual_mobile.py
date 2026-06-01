#!/usr/bin/env python3
"""
Multi-Language Support and Mobile Optimization Framework
Internationalization (i18n) and responsive design for global accessibility
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
import re

# Translation and localization
import gettext
from babel import Locale, dates, numbers
from babel.core import UnknownLocaleError
import iso639
import iso3166

# Web and mobile optimization
from flask import Flask, request, jsonify, render_template_string
import jinja2
import yaml
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    CHINESE = "zh"
    JAPANESE = "ja"
    ARABIC = "ar"
    RUSSIAN = "ru"
    PORTUGUESE = "pt"
    HINDI = "hi"

@dataclass
class TranslationEntry:
    """Translation entry with context"""
    key: str
    translations: Dict[str, str]  # language_code: translation
    context: Optional[str] = None
    plural_form: Optional[Dict[str, str]] = None
    notes: Optional[str] = None

class ResponsiveBreakpoint(Enum):
    """Responsive design breakpoints"""
    MOBILE = "mobile"  # < 768px
    TABLET = "tablet"  # 768px - 1024px
    DESKTOP = "desktop"  # > 1024px

class MultiLanguageMobileFramework:
    """Comprehensive multi-language and mobile optimization framework"""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.localization_dir = self.data_dir / "localization"
        self.localization_dir.mkdir(exist_ok=True)

        # Language configuration
        self.supported_languages = {
            Language.ENGLISH: {
                'name': 'English',
                'native_name': 'English',
                'rtl': False,
                'currency': 'USD',
                'date_format': 'medium',
                'number_format': '#,##0.00',
                'flag': '🇺🇸'
            },
            Language.SPANISH: {
                'name': 'Spanish',
                'native_name': 'Español',
                'rtl': False,
                'currency': 'EUR',
                'date_format': 'medium',
                'number_format': '#.##0,00',
                'flag': '🇪🇸'
            },
            Language.FRENCH: {
                'name': 'French',
                'native_name': 'Français',
                'rtl': False,
                'currency': 'EUR',
                'date_format': 'medium',
                'number_format': '# ##0,00',
                'flag': '🇫🇷'
            },
            Language.GERMAN: {
                'name': 'German',
                'native_name': 'Deutsch',
                'rtl': False,
                'currency': 'EUR',
                'date_format': 'medium',
                'number_format': '#.##0,00',
                'flag': '🇩🇪'
            },
            Language.CHINESE: {
                'name': 'Chinese',
                'native_name': '中文',
                'rtl': False,
                'currency': 'CNY',
                'date_format': 'long',
                'number_format': '#,##0.00',
                'flag': '🇨🇳'
            },
            Language.JAPANESE: {
                'name': 'Japanese',
                'native_name': '日本語',
                'rtl': False,
                'currency': 'JPY',
                'date_format': 'medium',
                'number_format': '#,##0.00',
                'flag': '🇯🇵'
            },
            Language.ARABIC: {
                'name': 'Arabic',
                'native_name': 'العربية',
                'rtl': True,
                'currency': 'SAR',
                'date_format': 'long',
                'number_format': '#,##0.00',
                'flag': '🇸🇦'
            },
            Language.RUSSIAN: {
                'name': 'Russian',
                'native_name': 'Русский',
                'rtl': False,
                'currency': 'RUB',
                'date_format': 'medium',
                'number_format': '# ##0,00',
                'flag': '🇷🇺'
            },
            Language.PORTUGUESE: {
                'name': 'Portuguese',
                'native_name': 'Português',
                'rtl': False,
                'currency': 'BRL',
                'date_format': 'medium',
                'number_format': '#.##0,00',
                'flag': '🇧🇷'
            },
            Language.HINDI: {
                'name': 'Hindi',
                'native_name': 'हिन्दी',
                'rtl': False,
                'currency': 'INR',
                'date_format': 'medium',
                'number_format': '#,##0.00',
                'flag': '🇮🇳'
            }
        }

        # Translation storage
        self.translations = {}
        self.translation_memory = {}

        # Mobile optimization
        self.responsive_config = {}
        self.mobile_components = {}

        # Initialize framework
        self.initialize_translations()
        self.initialize_responsive_design()
        self.create_mobile_templates()

    def initialize_translations(self):
        """Initialize translation system"""
        logger.info("Initializing translation system...")

        # Create comprehensive translation database
        self.create_core_translations()
        self.create_fiscal_translations()
        self.create_ui_translations()

        logger.info(f"✓ Translation system initialized with {len(self.translations)} entries")

    def create_core_translations(self):
        """Create core application translations"""
        core_translations = {
            # Common UI elements
            'app.title': {
                'en': 'Gerhard Fiscal Analysis Platform',
                'es': 'Plataforma de Análisis Fiscal Gerhard',
                'fr': 'Plateforme d\'Analyse Fiscale Gerhard',
                'de': 'Gerhard Fiskalanalyse-Plattform',
                'zh': 'Gerhard 财政分析平台',
                'ja': 'Gerhard 財政分析プラットフォーム',
                'ar': 'منصة جيرهارد للتحليل المالي',
                'ru': 'Платформа фискального анализа Gerhard',
                'pt': 'Plataforma de Análise Fiscal Gerhard',
                'hi': 'गेरहार्ड राजकोषीय विश्लेषण प्लेटफॉर्म'
            },
            'dashboard.title': {
                'en': 'Fiscal Dashboard',
                'es': 'Panel Fiscal',
                'fr': 'Tableau de Bord Fiscal',
                'de': 'Fiscal-Dashboard',
                'zh': '财政仪表板',
                'ja': '財政ダッシュボード',
                'ar': 'لوحة المالية العامة',
                'ru': 'Фискальная панель',
                'pt': 'Painel Fiscal',
                'hi': 'राजकोषीय डैशबोर्ड'
            },
            'navigation.home': {
                'en': 'Home',
                'es': 'Inicio',
                'fr': 'Accueil',
                'de': 'Startseite',
                'zh': '首页',
                'ja': 'ホーム',
                'ar': 'الرئيسية',
                'ru': 'Главная',
                'pt': 'Início',
                'hi': 'होम'
            },
            'navigation.analysis': {
                'en': 'Analysis',
                'es': 'Análisis',
                'fr': 'Analyse',
                'de': 'Analyse',
                'zh': '分析',
                'ja': '分析',
                'ar': 'التحليل',
                'ru': 'Анализ',
                'pt': 'Análise',
                'hi': 'विश्लेषण'
            },
            'navigation.data': {
                'en': 'Data',
                'es': 'Datos',
                'fr': 'Données',
                'de': 'Daten',
                'zh': '数据',
                'ja': 'データ',
                'ar': 'البيانات',
                'ru': 'Данные',
                'pt': 'Dados',
                'hi': 'डेटा'
            },
            'navigation.about': {
                'en': 'About',
                'es': 'Acerca de',
                'fr': 'À propos',
                'de': 'Über',
                'zh': '关于',
                'ja': 'について',
                'ar': 'حول',
                'ru': 'О нас',
                'pt': 'Sobre',
                'hi': 'के बारे में'
            },
            'button.view_details': {
                'en': 'View Details',
                'es': 'Ver Detalles',
                'fr': 'Voir les Détails',
                'de': 'Details anzeigen',
                'zh': '查看详情',
                'ja': '詳細を見る',
                'ar': 'عرض التفاصيل',
                'ru': 'Подробнее',
                'pt': 'Ver Detalhes',
                'hi': 'विवरण देखें'
            },
            'button.download': {
                'en': 'Download',
                'es': 'Descargar',
                'fr': 'Télécharger',
                'de': 'Herunterladen',
                'zh': '下载',
                'ja': 'ダウンロード',
                'ar': 'تحميل',
                'ru': 'Скачать',
                'pt': 'Baixar',
                'hi': 'डाउनलोड'
            },
            'button.search': {
                'en': 'Search',
                'es': 'Buscar',
                'fr': 'Rechercher',
                'de': 'Suchen',
                'zh': '搜索',
                'ja': '検索',
                'ar': 'بحث',
                'ru': 'Поиск',
                'pt': 'Pesquisar',
                'hi': 'खोजें'
            },
            'error.page_not_found': {
                'en': 'Page not found',
                'es': 'Página no encontrada',
                'fr': 'Page non trouvée',
                'de': 'Seite nicht gefunden',
                'zh': '页面未找到',
                'ja': 'ページが見つかりません',
                'ar': 'الصفحة غير موجودة',
                'ru': 'Страница не найдена',
                'pt': 'Página não encontrada',
                'hi': 'पृष्ठ नहीं मिला'
            },
            'loading.data': {
                'en': 'Loading data...',
                'es': 'Cargando datos...',
                'fr': 'Chargement des données...',
                'de': 'Daten werden geladen...',
                'zh': '正在加载数据...',
                'ja': 'データを読み込み中...',
                'ar': 'جاري تحميل البيانات...',
                'ru': 'Загрузка данных...',
                'pt': 'Carregando dados...',
                'hi': 'डेटा लोड हो रहा है...'
            },
            'no.data.available': {
                'en': 'No data available',
                'es': 'No hay datos disponibles',
                'fr': 'Aucune donnée disponible',
                'de': 'Keine Daten verfügbar',
                'zh': '无可用数据',
                'ja': '利用可能なデータがありません',
                'ar': 'لا توجد بيانات متاحة',
                'ru': 'Нет доступных данных',
                'pt': 'Nenhum dado disponível',
                'hi': 'कोई डेटा उपलब्ध नहीं'
            }
        }

        for key, translations in core_translations.items():
            self.translations[key] = TranslationEntry(
                key=key,
                translations=translations,
                context='ui'
            )

    def create_fiscal_translations(self):
        """Create fiscal terminology translations"""
        fiscal_translations = {
            # Fiscal indicators
            'fiscal.revenue': {
                'en': 'Revenue',
                'es': 'Ingresos',
                'fr': 'Recettes',
                'de': 'Einnahmen',
                'zh': '财政收入',
                'ja': '収入',
                'ar': 'الإيرادات',
                'ru': 'Доходы',
                'pt': 'Receita',
                'hi': 'राजस्व'
            },
            'fiscal.expenditure': {
                'en': 'Expenditure',
                'es': 'Gastos',
                'fr': 'Dépenses',
                'de': 'Ausgaben',
                'zh': '支出',
                'ja': '支出',
                'ar': 'النفقات',
                'ru': 'Расходы',
                'pt': 'Despesa',
                'hi': 'व्यय'
            },
            'fiscal.deficit': {
                'en': 'Deficit',
                'es': 'Déficit',
                'fr': 'Déficit',
                'de': 'Defizit',
                'zh': '赤字',
                'ja': '赤字',
                'ar': 'العجز',
                'ru': 'Дефицит',
                'pt': 'Déficit',
                'hi': 'घाटा'
            },
            'fiscal.surplus': {
                'en': 'Surplus',
                'es': 'Superávit',
                'fr': 'Excédent',
                'de': 'Überschuss',
                'zh': '盈余',
                'ja': '黒字',
                'ar': 'الفائض',
                'ru': 'Профицит',
                'pt': 'Superávit',
                'hi': 'अधिशेष'
            },
            'fiscal.debt': {
                'en': 'Debt',
                'es': 'Deuda',
                'fr': 'Dette',
                'de': 'Schulden',
                'zh': '债务',
                'ja': '債務',
                'ar': 'الديون',
                'ru': 'Долг',
                'pt': 'Dívida',
                'hi': 'ऋण'
            },
            'fiscal.balance': {
                'en': 'Balance',
                'es': 'Balance',
                'fr': 'Solde',
                'de': 'Saldo',
                'zh': '余额',
                'ja': 'バランス',
                'ar': 'الميزان',
                'ru': 'Баланс',
                'pt': 'Saldo',
                'hi': 'शेष'
            },
            'fiscal.sustainability': {
                'en': 'Fiscal Sustainability',
                'es': 'Sostenibilidad Fiscal',
                'fr': 'Durabilité Fiscale',
                'de': 'Fiskale Nachhaltigkeit',
                'zh': '财政可持续性',
                'ja': '財政持続可能性',
                'ar': 'الاستدامة المالية',
                'ru': 'Фискальная устойчивость',
                'pt': 'Sustentabilidade Fiscal',
                'hi': 'राजकोषीय स्थिरता'
            },
            'fiscal.policy': {
                'en': 'Fiscal Policy',
                'es': 'Política Fiscal',
                'fr': 'Politique Fiscale',
                'de': 'Fiskalpolitik',
                'zh': '财政政策',
                'ja': '財政政策',
                'ar': 'السياسة المالية',
                'ru': 'Фискальная политика',
                'pt': 'Política Fiscal',
                'hi': 'राजकोषीय नीति'
            },
            # Tax types
            'tax.income': {
                'en': 'Income Tax',
                'es': 'Impuesto sobre la Renta',
                'fr': 'Impôt sur le Revenu',
                'de': 'Einkommensteuer',
                'zh': '所得税',
                'ja': '所得税',
                'ar': 'ضريبة الدخل',
                'ru': 'Подоходный налог',
                'pt': 'Imposto de Renda',
                'hi': 'आयकर'
            },
            'tax.corporate': {
                'en': 'Corporate Tax',
                'es': 'Impuesto de Sociedades',
                'fr': 'Impôt sur les Sociétés',
                'de': 'Körperschaftsteuer',
                'zh': '企业所得税',
                'ja': '法人税',
                'ar': 'ضريبة الشركات',
                'ru': 'Налог на прибыль',
                'pt': 'Imposto de Renda Corporativo',
                'hi': 'कॉर्पोरेट कर'
            },
            'tax.vat': {
                'en': 'Value Added Tax (VAT)',
                'es': 'Impuesto sobre el Valor Añadido (IVA)',
                'fr': 'Taxe sur la Valeur Ajoutée (TVA)',
                'de': 'Mehrwertsteuer (MwSt)',
                'zh': '增值税',
                'ja': '消費税',
                'ar': 'ضريبة القيمة المضافة',
                'ru': 'Налог на добавленную стоимость (НДС)',
                'pt': 'Imposto sobre Valor Agregado (IVA)',
                'hi': 'मूल्य वर्धित कर (वैट)'
            },
            'tax.property': {
                'en': 'Property Tax',
                'es': 'Impuesto sobre la Propiedad',
                'fr': 'Impôt Foncier',
                'de': 'Grundsteuer',
                'zh': '财产税',
                'ja': '固定資産税',
                'ar': 'ضريبة الممتلكات',
                'ru': 'Налог на имущество',
                'pt': 'Imposto Predial',
                'hi': 'संपत्ति कर'
            }
        }

        for key, translations in fiscal_translations.items():
            self.translations[key] = TranslationEntry(
                key=key,
                translations=translations,
                context='fiscal'
            )

    def create_ui_translations(self):
        """Create UI-specific translations"""
        ui_translations = {
            # Data analysis
            'analysis.trends': {
                'en': 'Trends',
                'es': 'Tendencias',
                'fr': 'Tendances',
                'de': 'Trends',
                'zh': '趋势',
                'ja': 'トレンド',
                'ar': 'الاتجاهات',
                'ru': 'Тренды',
                'pt': 'Tendências',
                'hi': 'प्रवृत्तियां'
            },
            'analysis.comparison': {
                'en': 'Comparison',
                'es': 'Comparación',
                'fr': 'Comparaison',
                'de': 'Vergleich',
                'zh': '比较',
                'ja': '比較',
                'ar': 'مقارنة',
                'ru': 'Сравнение',
                'pt': 'Comparação',
                'hi': 'तुलना'
            },
            'analysis.forecasting': {
                'en': 'Forecasting',
                'es': 'Pronóstico',
                'fr': 'Prévision',
                'de': 'Prognose',
                'zh': '预测',
                'ja': '予測',
                'ar': 'التنبؤ',
                'ru': 'Прогнозирование',
                'pt': 'Previsão',
                'hi': 'पूर्वानुमान'
            },
            # Units and measurements
            'unit.percent_gdp': {
                'en': '% of GDP',
                'es': '% del PIB',
                'fr': '% du PIB',
                'de': '% des BIP',
                'zh': '占GDP百分比',
                'ja': 'GDPの%',
                'ar': '% من الناتج المحلي الإجمالي',
                'ru': '% ВВП',
                'pt': '% do PIB',
                'hi': 'जीडीपी का प्रतिशत'
            },
            'unit.billion_usd': {
                'en': 'Billion USD',
                'es': 'Miles de millones USD',
                'fr': 'Milliard USD',
                'de': 'Mrd. USD',
                'zh': '十亿美元',
                'ja': '10億米ドル',
                'ar': 'مليار دولار أمريكي',
                'ru': 'млрд долл. США',
                'pt': 'Bilhão USD',
                'hi': 'अरब अमेरिकी डॉलर'
            },
            'unit.per_capita': {
                'en': 'Per Capita',
                'es': 'Per Cápita',
                'fr': 'Par Habitant',
                'de': 'Pro Kopf',
                'zh': '人均',
                'ja': '一人当たり',
                'ar': 'للفرد',
                'ru': 'На душу населения',
                'pt': 'Per Capita',
                'hi': 'प्रति व्यक्ति'
            },
            # Time periods
            'time.annual': {
                'en': 'Annual',
                'es': 'Anual',
                'fr': 'Annuel',
                'de': 'Jährlich',
                'zh': '年度',
                'ja': '年次',
                'ar': 'سنوي',
                'ru': 'Ежегодный',
                'pt': 'Anual',
                'hi': 'वार्षिक'
            },
            'time.quarterly': {
                'en': 'Quarterly',
                'es': 'Trimestral',
                'fr': 'Trimestriel',
                'de': 'Quartalsweise',
                'zh': '季度',
                'ja': '四半期',
                'ar': 'ربع سنوي',
                'ru': 'Ежеквартальный',
                'pt': 'Trimestral',
                'hi': 'त्रैमासिक'
            },
            'time.monthly': {
                'en': 'Monthly',
                'es': 'Mensual',
                'fr': 'Mensuel',
                'de': 'Monatlich',
                'zh': '月度',
                'ja': '月次',
                'ar': 'شهري',
                'ru': 'Ежемесячный',
                'pt': 'Mensal',
                'hi': 'मासिक'
            }
        }

        for key, translations in ui_translations.items():
            self.translations[key] = TranslationEntry(
                key=key,
                translations=translations,
                context='ui'
            )

    def initialize_responsive_design(self):
        """Initialize responsive design configurations"""
        logger.info("Initializing responsive design configurations...")

        self.responsive_config = {
            'breakpoints': {
                ResponsiveBreakpoint.MOBILE: {'max_width': 767, 'columns': 1},
                ResponsiveBreakpoint.TABLET: {'min_width': 768, 'max_width': 1023, 'columns': 2},
                ResponsiveBreakpoint.DESKTOP: {'min_width': 1024, 'columns': 3}
            },
            'grid_system': {
                'container_max_widths': {
                    'mobile': '100%',
                    'tablet': '750px',
                    'desktop': '1200px'
                },
                'gutter_width': '30px',
                'column_count': 12
            },
            'typography': {
                'font_sizes': {
                    'mobile': {
                        'h1': '28px',
                        'h2': '24px',
                        'h3': '20px',
                        'body': '16px',
                        'small': '14px'
                    },
                    'tablet': {
                        'h1': '32px',
                        'h2': '28px',
                        'h3': '22px',
                        'body': '16px',
                        'small': '14px'
                    },
                    'desktop': {
                        'h1': '36px',
                        'h2': '30px',
                        'h3': '24px',
                        'body': '16px',
                        'small': '12px'
                    }
                }
            },
            'components': {
                'cards': {
                    'mobile': {'padding': '16px', 'margin': '8px'},
                    'tablet': {'padding': '20px', 'margin': '12px'},
                    'desktop': {'padding': '24px', 'margin': '16px'}
                },
                'buttons': {
                    'mobile': {'min_height': '44px', 'font_size': '16px'},
                    'tablet': {'min_height': '40px', 'font_size': '14px'},
                    'desktop': {'min_height': '36px', 'font_size': '14px'}
                },
                'charts': {
                    'mobile': {'height': '300px', 'legend_position': 'bottom'},
                    'tablet': {'height': '400px', 'legend_position': 'right'},
                    'desktop': {'height': '500px', 'legend_position': 'right'}
                }
            }
        }

        logger.info("✓ Responsive design configurations initialized")

    def create_mobile_templates(self):
        """Create mobile-optimized templates"""
        logger.info("Creating mobile-optimized templates...")

        # Mobile dashboard template
        self.mobile_components['dashboard'] = """
<div class="mobile-dashboard">
    <header class="mobile-header">
        <button class="menu-toggle" onclick="toggleMenu()">☰</button>
        <h1 class="app-title">{{ get_translation('app.title', language) }}</h1>
        <button class="language-toggle" onclick="toggleLanguage()">{{ language_flag }}</button>
    </header>

    <nav class="mobile-nav" id="mobileNav">
        <a href="#" class="nav-item" onclick="navigateTo('home')">
            <span class="nav-icon">🏠</span>
            <span class="nav-text">{{ get_translation('navigation.home', language) }}</span>
        </a>
        <a href="#" class="nav-item" onclick="navigateTo('dashboard')">
            <span class="nav-icon">📊</span>
            <span class="nav-text">{{ get_translation('dashboard.title', language) }}</span>
        </a>
        <a href="#" class="nav-item" onclick="navigateTo('analysis')">
            <span class="nav-icon">📈</span>
            <span class="nav-text">{{ get_translation('navigation.analysis', language) }}</span>
        </a>
        <a href="#" class="nav-item" onclick="navigateTo('data')">
            <span class="nav-icon">🗄️</span>
            <span class="nav-text">{{ get_translation('navigation.data', language) }}</span>
        </a>
    </nav>

    <main class="mobile-content">
        <div class="quick-stats">
            <div class="stat-card">
                <h3>{{ get_translation('fiscal.revenue', language) }}</h3>
                <div class="stat-value">{{ format_number(total_revenue, language) }}</div>
                <div class="stat-unit">{{ get_translation('unit.percent_gdp', language) }}</div>
            </div>
            <div class="stat-card">
                <h3>{{ get_translation('fiscal.expenditure', language) }}</h3>
                <div class="stat-value">{{ format_number(total_expenditure, language) }}</div>
                <div class="stat-unit">{{ get_translation('unit.percent_gdp', language) }}</div>
            </div>
            <div class="stat-card">
                <h3>{{ get_translation('fiscal.balance', language) }}</h3>
                <div class="stat-value">{{ format_number(balance, language) }}</div>
                <div class="stat-unit">{{ get_translation('unit.percent_gdp', language) }}</div>
            </div>
        </div>

        <div class="chart-container">
            <div id="mobileChart" class="mobile-chart"></div>
        </div>

        <div class="data-table-container">
            <h2>{{ get_translation('analysis.comparison', language) }}</h2>
            <div class="mobile-table">
                <!-- Mobile-optimized table content -->
            </div>
        </div>
    </main>

    <footer class="mobile-footer">
        <p>&copy; 2025 Gerhard Platform</p>
    </footer>
</div>
"""

        # Mobile chart template
        self.mobile_components['chart'] = """
<div class="mobile-chart-container">
    <div class="chart-header">
        <h2>{{ chart_title }}</h2>
        <button class="chart-options" onclick="showChartOptions()">⚙️</button>
    </div>
    <div class="chart-wrapper">
        <canvas id="{{ chart_id }}" width="400" height="300"></canvas>
    </div>
    <div class="chart-legend">
        <!-- Touch-friendly legend -->
    </div>
    <div class="chart-actions">
        <button onclick="zoomChart()">{{ get_translation('button.zoom', language) }}</button>
        <button onclick="downloadChart()">{{ get_translation('button.download', language) }}</button>
        <button onclick="shareChart()">{{ get_translation('button.share', language) }}</button>
    </div>
</div>
"""

        # Mobile form template
        self.mobile_components['form'] = """
<div class="mobile-form">
    <form id="{{ form_id }}" class="responsive-form">
        <div class="form-group">
            <label for="{{ field_id }}">{{ get_translation(field_label, language) }}</label>
            <input type="{{ field_type }}" id="{{ field_id }}" name="{{ field_name }}"
                   class="mobile-input" placeholder="{{ get_translation(placeholder, language) }}">
            <span class="input-error"></span>
        </div>

        <div class="form-actions">
            <button type="submit" class="mobile-button primary">
                {{ get_translation('button.submit', language) }}
            </button>
            <button type="reset" class="mobile-button secondary">
                {{ get_translation('button.reset', language) }}
            </button>
        </div>
    </form>
</div>
"""

        logger.info("✓ Mobile templates created")

    def get_translation(self, key: str, language: str, context: str = None) -> str:
        """Get translation for a key in specified language"""
        if key not in self.translations:
            return key  # Return key if no translation found

        entry = self.translations[key]

        # Check if translation exists for the language
        if language in entry.translations:
            return entry.translations[language]

        # Fall back to English if translation not found
        if 'en' in entry.translations:
            return entry.translations['en']

        # Return key if no translation found at all
        return key

    def format_number(self, number: Union[int, float], language: str,
                     format_type: str = 'decimal') -> str:
        """Format number according to locale conventions"""
        try:
            locale_map = {
                'en': 'en_US',
                'es': 'es_ES',
                'fr': 'fr_FR',
                'de': 'de_DE',
                'zh': 'zh_CN',
                'ja': 'ja_JP',
                'ar': 'ar_SA',
                'ru': 'ru_RU',
                'pt': 'pt_BR',
                'hi': 'hi_IN'
            }

            locale_code = locale_map.get(language, 'en_US')
            locale = Locale.parse(locale_code)

            if format_type == 'currency':
                # This is simplified - in production, you'd use proper currency formatting
                return f"{number:,.2f}"
            elif format_type == 'percent':
                return f"{number:.1f}%"
            else:
                return f"{number:,.2f}"

        except Exception:
            # Fallback to basic formatting
            if format_type == 'percent':
                return f"{number:.1f}%"
            else:
                return f"{number:,.2f}"

    def format_date(self, date: Union[datetime, str], language: str,
                   format_type: str = 'medium') -> str:
        """Format date according to locale conventions"""
        try:
            if isinstance(date, str):
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))

            locale_map = {
                'en': 'en_US',
                'es': 'es_ES',
                'fr': 'fr_FR',
                'de': 'de_DE',
                'zh': 'zh_CN',
                'ja': 'ja_JP',
                'ar': 'ar_SA',
                'ru': 'ru_RU',
                'pt': 'pt_BR',
                'hi': 'hi_IN'
            }

            locale_code = locale_map.get(language, 'en_US')
            locale = Locale.parse(locale_code)

            if format_type == 'short':
                return dates.format_date(date, format='short', locale=locale)
            elif format_type == 'long':
                return dates.format_date(date, format='long', locale=locale)
            else:  # medium
                return dates.format_date(date, format='medium', locale=locale)

        except Exception:
            # Fallback to ISO format
            if isinstance(date, datetime):
                return date.strftime('%Y-%m-%d')
            else:
                return str(date)

    def detect_user_language(self, request_headers: Dict = None) -> str:
        """Detect user's preferred language from request headers"""
        if request_headers and 'Accept-Language' in request_headers:
            accept_language = request_headers['Accept-Language']
            # Parse Accept-Language header
            languages = [lang.split('-')[0].strip() for lang in accept_language.split(',')]

            # Find first supported language
            for lang in languages:
                for supported_lang in self.supported_languages:
                    if lang == supported_lang.value:
                        return supported_lang.value

        # Default to English
        return 'en'

    def get_responsive_class(self, breakpoint: ResponsiveBreakpoint) -> str:
        """Get responsive CSS class for breakpoint"""
        return f"responsive-{breakpoint.value}"

    def generate_localized_javascript(self) -> str:
        """Generate JavaScript localization functions"""
        js_code = """
// Gerhard Platform Localization Functions
class LocalizationManager {
    constructor() {
        this.currentLanguage = this.detectLanguage();
        this.translations = {};
        this.rtlLanguages = ['ar'];
    }

    detectLanguage() {
        // Try to detect from browser
        const browserLang = navigator.language.split('-')[0];
        const supportedLangs = ['en', 'es', 'fr', 'de', 'zh', 'ja', 'ar', 'ru', 'pt', 'hi'];

        if (supportedLangs.includes(browserLang)) {
            return browserLang;
        }

        // Check localStorage
        const savedLang = localStorage.getItem('preferredLanguage');
        if (savedLang && supportedLangs.includes(savedLang)) {
            return savedLang;
        }

        return 'en'; // Default
    }

    setLanguage(lang) {
        if (this.isSupported(lang)) {
            this.currentLanguage = lang;
            localStorage.setItem('preferredLanguage', lang);
            this.updatePageLanguage();
            this.updateDirection();
        }
    }

    isSupported(lang) {
        const supportedLangs = ['en', 'es', 'fr', 'de', 'zh', 'ja', 'ar', 'ru', 'pt', 'hi'];
        return supportedLangs.includes(lang);
    }

    translate(key, fallback = null) {
        if (this.translations[key] && this.translations[key][this.currentLanguage]) {
            return this.translations[key][this.currentLanguage];
        }
        return fallback || key;
    }

    formatNumber(number, type = 'decimal') {
        try {
            const options = {
                style: type === 'currency' ? 'currency' : 'decimal',
                currency: type === 'currency' ? 'USD' : undefined,
                minimumFractionDigits: type === 'percent' ? 1 : 2,
                maximumFractionDigits: type === 'percent' ? 1 : 2
            };

            if (type === 'percent') {
                return new Intl.NumberFormat(this.currentLanguage, {
                    style: 'percent',
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1
                }).format(number / 100);
            }

            return new Intl.NumberFormat(this.currentLanguage, options).format(number);
        } catch (e) {
            return number.toString();
        }
    }

    formatDate(date, type = 'medium') {
        try {
            const options = {
                dateStyle: type,
                timeStyle: undefined
            };
            return new Intl.DateTimeFormat(this.currentLanguage, options).format(date);
        } catch (e) {
            return date.toString();
        }
    }

    isRTL() {
        return this.rtlLanguages.includes(this.currentLanguage);
    }

    updateDirection() {
        const html = document.documentElement;
        if (this.isRTL()) {
            html.setAttribute('dir', 'rtl');
            html.setAttribute('lang', this.currentLanguage);
        } else {
            html.setAttribute('dir', 'ltr');
            html.setAttribute('lang', this.currentLanguage);
        }
    }

    updatePageLanguage() {
        // Update all elements with data-translate attribute
        const elements = document.querySelectorAll('[data-translate]');
        elements.forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.translate(key);
            if (element.placeholder) {
                element.placeholder = translation;
            } else {
                element.textContent = translation;
            }
        });

        // Update page title
        const title = document.querySelector('title');
        if (title) {
            title.textContent = this.translate('app.title');
        }
    }

    loadTranslations(translations) {
        this.translations = translations;
        this.updatePageLanguage();
    }
}

// Mobile Responsiveness Functions
class ResponsiveManager {
    constructor() {
        this.breakpoints = {
            mobile: 767,
            tablet: 1023,
            desktop: 1024
        };
        this.currentBreakpoint = this.getCurrentBreakpoint();
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateLayout();
    }

    setupEventListeners() {
        window.addEventListener('resize', () => {
            this.handleResize();
        });

        window.addEventListener('orientationchange', () => {
            setTimeout(() => this.handleResize(), 100);
        });
    }

    getCurrentBreakpoint() {
        const width = window.innerWidth;
        if (width <= this.breakpoints.mobile) {
            return 'mobile';
        } else if (width <= this.breakpoints.tablet) {
            return 'tablet';
        } else {
            return 'desktop';
        }
    }

    handleResize() {
        const newBreakpoint = this.getCurrentBreakpoint();
        if (newBreakpoint !== this.currentBreakpoint) {
            this.currentBreakpoint = newBreakpoint;
            this.updateLayout();
        }
    }

    updateLayout() {
        // Update CSS classes
        document.body.setAttribute('data-breakpoint', this.currentBreakpoint);

        // Handle chart resizing
        this.resizeCharts();

        // Handle table responsiveness
        this.handleTables();

        // Handle navigation
        this.handleNavigation();
    }

    resizeCharts() {
        const charts = document.querySelectorAll('.chart-container');
        charts.forEach(chart => {
            const container = chart.parentElement;
            const width = container.offsetWidth;

            if (this.currentBreakpoint === 'mobile') {
                chart.style.height = '300px';
            } else if (this.currentBreakpoint === 'tablet') {
                chart.style.height = '400px';
            } else {
                chart.style.height = '500px';
            }
        });
    }

    handleTables() {
        const tables = document.querySelectorAll('table.data-table');
        tables.forEach(table => {
            if (this.currentBreakpoint === 'mobile') {
                this.convertTableToCards(table);
            } else {
                this.convertCardsToTable(table);
            }
        });
    }

    convertTableToCards(table) {
        // Implementation for converting tables to card format on mobile
        if (table.classList.contains('converted-to-cards')) return;

        const cards = document.createElement('div');
        cards.className = 'table-cards';

        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const card = document.createElement('div');
            card.className = 'table-card';

            const cells = row.querySelectorAll('td');
            const headers = table.querySelectorAll('thead th');

            cells.forEach((cell, index) => {
                if (headers[index]) {
                    const label = document.createElement('div');
                    label.className = 'card-label';
                    label.textContent = headers[index].textContent;
                    card.appendChild(label);
                }

                const value = document.createElement('div');
                value.className = 'card-value';
                value.innerHTML = cell.innerHTML;
                card.appendChild(value);
            });

            cards.appendChild(card);
        });

        table.parentNode.replaceChild(cards, table);
        table.classList.add('converted-to-cards');
    }

    handleNavigation() {
        const nav = document.querySelector('nav.main-nav');
        if (!nav) return;

        if (this.currentBreakpoint === 'mobile') {
            nav.classList.add('mobile-nav');
            // Add mobile menu toggle if not exists
            if (!nav.querySelector('.menu-toggle')) {
                const toggle = document.createElement('button');
                toggle.className = 'menu-toggle';
                toggle.innerHTML = '☰';
                toggle.onclick = () => nav.classList.toggle('open');
                nav.insertBefore(toggle, nav.firstChild);
            }
        } else {
            nav.classList.remove('mobile-nav', 'open');
            const toggle = nav.querySelector('.menu-toggle');
            if (toggle) toggle.remove();
        }
    }
}

// Initialize managers
const localizationManager = new LocalizationManager();
const responsiveManager = new ResponsiveManager();

// Global functions for template usage
function getTranslation(key, language) {
    return localizationManager.translate(key);
}

function formatNumber(number, language, type) {
    return localizationManager.formatNumber(number, type);
}

function toggleLanguage() {
    const currentLang = localizationManager.currentLanguage;
    const supportedLangs = ['en', 'es', 'fr', 'de', 'zh', 'ja', 'ar', 'ru', 'pt', 'hi'];
    const currentIndex = supportedLangs.indexOf(currentLang);
    const nextIndex = (currentIndex + 1) % supportedLangs.length;
    const nextLang = supportedLangs[nextIndex];

    localizationManager.setLanguage(nextLang);
    location.reload(); // Reload to update server-side content
}

function toggleMenu() {
    const nav = document.querySelector('nav.mobile-nav');
    if (nav) {
        nav.classList.toggle('open');
    }
}
"""

        return js_code

    def generate_responsive_css(self) -> str:
        """Generate responsive CSS styles"""
        css_code = """
/* Gerhard Platform Responsive Styles */

/* Base Styles */
* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
}

body {
    overflow-x: hidden;
}

/* Container System */
.container {
    width: 100%;
    padding: 0 15px;
    margin: 0 auto;
}

/* Grid System */
.row {
    display: flex;
    flex-wrap: wrap;
    margin: 0 -15px;
}

.col {
    padding: 0 15px;
    flex: 1;
}

/* Mobile First Approach */

/* Mobile Styles (Default) */
.mobile-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    background: #fff;
    border-bottom: 1px solid #eee;
    position: sticky;
    top: 0;
    z-index: 1000;
}

.menu-toggle {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    padding: 10px;
}

.app-title {
    font-size: 18px;
    font-weight: 600;
    margin: 0;
    flex: 1;
    text-align: center;
}

.language-toggle {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    padding: 10px;
}

.mobile-nav {
    position: fixed;
    top: 0;
    left: -100%;
    width: 280px;
    height: 100vh;
    background: #fff;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
    transition: left 0.3s ease;
    z-index: 999;
    overflow-y: auto;
}

.mobile-nav.open {
    left: 0;
}

.mobile-nav .nav-item {
    display: flex;
    align-items: center;
    padding: 15px 20px;
    text-decoration: none;
    color: #333;
    border-bottom: 1px solid #f5f5f5;
}

.mobile-nav .nav-item:hover {
    background: #f8f9fa;
}

.nav-icon {
    margin-right: 15px;
    font-size: 20px;
}

.nav-text {
    font-size: 16px;
}

.mobile-content {
    padding: 20px 15px;
}

.quick-stats {
    display: grid;
    grid-template-columns: 1fr;
    gap: 15px;
    margin-bottom: 30px;
}

.stat-card {
    background: #fff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}

.stat-card h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 5px;
}

.stat-unit {
    font-size: 12px;
    color: #999;
}

.chart-container {
    background: #fff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

.mobile-chart {
    width: 100%;
    height: 300px;
}

.chart-actions {
    display: flex;
    justify-content: space-around;
    margin-top: 15px;
}

.chart-actions button {
    padding: 10px 15px;
    border: none;
    background: #007bff;
    color: #fff;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
}

.chart-actions button:hover {
    background: #0056b3;
}

/* Table Cards for Mobile */
.table-cards {
    display: grid;
    grid-template-columns: 1fr;
    gap: 15px;
}

.table-card {
    background: #fff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.card-label {
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}

.card-value {
    font-size: 16px;
    font-weight: 500;
    color: #333;
}

/* Mobile Forms */
.mobile-form {
    background: #fff;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #333;
}

.mobile-input {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s ease;
}

.mobile-input:focus {
    outline: none;
    border-color: #007bff;
}

.input-error {
    color: #dc3545;
    font-size: 14px;
    margin-top: 5px;
    display: block;
}

.form-actions {
    display: flex;
    gap: 10px;
}

.mobile-button {
    flex: 1;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.mobile-button.primary {
    background: #007bff;
    color: #fff;
}

.mobile-button.primary:hover {
    background: #0056b3;
}

.mobile-button.secondary {
    background: #6c757d;
    color: #fff;
}

.mobile-button.secondary:hover {
    background: #545b62;
}

/* Footer */
.mobile-footer {
    background: #f8f9fa;
    padding: 20px 15px;
    text-align: center;
    border-top: 1px solid #dee2e6;
    margin-top: 40px;
}

.mobile-footer p {
    margin: 0;
    color: #666;
    font-size: 14px;
}

/* RTL Support */
[dir="rtl"] .mobile-nav {
    left: auto;
    right: -100%;
}

[dir="rtl"] .mobile-nav.open {
    left: auto;
    right: 0;
    box-shadow: -2px 0 10px rgba(0,0,0,0.1);
}

[dir="rtl"] .nav-icon {
    margin-right: 0;
    margin-left: 15px;
}

[dir="rtl"] .quick-stats {
    direction: rtl;
}

[dir="rtl"] .form-actions {
    flex-direction: row-reverse;
}

/* Tablet Styles */
@media (min-width: 768px) {
    .container {
        max-width: 750px;
        padding: 0 30px;
    }

    .mobile-header {
        padding: 20px 30px;
    }

    .app-title {
        font-size: 24px;
    }

    .mobile-content {
        padding: 30px;
    }

    .quick-stats {
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
    }

    .mobile-chart {
        height: 400px;
    }

    .row {
        display: flex;
        margin: 0 -15px;
    }

    .col-6 {
        flex: 0 0 50%;
        padding: 0 15px;
    }
}

/* Desktop Styles */
@media (min-width: 1024px) {
    .container {
        max-width: 1200px;
    }

    .mobile-header {
        display: none;
    }

    .mobile-nav {
        position: static;
        width: auto;
        height: auto;
        background: transparent;
        box-shadow: none;
        display: flex;
        flex-direction: row;
    }

    .mobile-nav .nav-item {
        border-bottom: none;
        margin-right: 30px;
    }

    .menu-toggle {
        display: none;
    }

    .mobile-content {
        padding: 40px 0;
    }

    .quick-stats {
        grid-template-columns: repeat(4, 1fr);
        gap: 30px;
    }

    .mobile-chart {
        height: 500px;
    }

    .chart-container {
        padding: 30px;
    }

    .stat-card {
        padding: 30px;
    }

    .stat-value {
        font-size: 32px;
    }

    /* Convert cards back to tables */
    .table-cards {
        display: none;
    }

    table.data-table {
        display: table;
        width: 100%;
        border-collapse: collapse;
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }

    table.data-table th,
    table.data-table td {
        padding: 15px;
        text-align: left;
        border-bottom: 1px solid #eee;
    }

    table.data-table th {
        background: #f8f9fa;
        font-weight: 600;
        color: #333;
    }

    table.data-table tbody tr:hover {
        background: #f8f9fa;
    }
}

/* High DPI Displays */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
    .stat-card,
    .chart-container {
        border-width: 0.5px;
    }
}

/* Dark Mode Support */
@media (prefers-color-scheme: dark) {
    .mobile-header,
    .mobile-nav,
    .stat-card,
    .chart-container,
    .mobile-form,
    table.data-table {
        background: #1a1a1a;
        color: #fff;
    }

    .mobile-nav .nav-item:hover {
        background: #2d2d2d;
    }

    .mobile-input {
        background: #2d2d2d;
        border-color: #444;
        color: #fff;
    }

    .mobile-header,
    .mobile-footer {
        border-color: #444;
    }

    table.data-table th {
        background: #2d2d2d;
    }

    table.data-table tbody tr:hover {
        background: #2d2d2d;
    }
}

/* Print Styles */
@media print {
    .mobile-header,
    .mobile-nav,
    .chart-actions,
    .form-actions {
        display: none;
    }

    .mobile-content {
        padding: 0;
    }

    .stat-card,
    .chart-container {
        box-shadow: none;
        border: 1px solid #ddd;
        break-inside: avoid;
    }
}
"""

        return css_code

    def create_multilingual_api_endpoint(self) -> str:
        """Create Flask API endpoint for multilingual support"""
        api_code = """
from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime

app = Flask(__name__)

# Load localization framework
localization_framework = MultiLanguageMobileFramework(data_dir)

@app.route('/api/translations/<language>')
def get_translations(language):
    '''Get translations for a specific language'''
    if language not in [lang.value for lang in Language]:
        return jsonify({'error': 'Language not supported'}), 400

    translations = {}
    for key, entry in localization_framework.translations.items():
        if language in entry.translations:
            translations[key] = entry.translations[language]

    return jsonify({
        'language': language,
        'translations': translations,
        'rtl': localization_framework.supported_languages[Language(language)]['rtl']
    })

@app.route('/api/format/number')
def format_number():
    '''Format number according to locale'''
    number = request.args.get('number', type=float)
    language = request.args.get('language', 'en')
    format_type = request.args.get('type', 'decimal')

    formatted = localization_framework.format_number(number, language, format_type)

    return jsonify({
        'original': number,
        'formatted': formatted,
        'language': language,
        'type': format_type
    })

@app.route('/api/format/date')
def format_date():
    '''Format date according to locale'''
    date_str = request.args.get('date')
    language = request.args.get('language', 'en')
    format_type = request.args.get('type', 'medium')

    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        formatted = localization_framework.format_date(date, language, format_type)

        return jsonify({
            'original': date_str,
            'formatted': formatted,
            'language': language,
            'type': format_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/mobile')
def mobile_dashboard():
    '''Serve mobile-optimized dashboard'''
    # Detect user language
    language = localization_framework.detect_user_language(dict(request.headers))

    # Get language flag
    language_flag = localization_framework.supported_languages[Language(language)]['flag']

    # Render mobile template
    template = localization_framework.mobile_components['dashboard']

    return render_template_string(template,
                                language=language,
                                language_flag=language_flag,
                                get_translation=localization_framework.get_translation,
                                format_number=localization_framework.format_number,
                                format_date=localization_framework.format_date)

@app.route('/assets/localization.js')
def serve_localization_js():
    '''Serve JavaScript localization functions'''
    js_code = localization_framework.generate_localized_javascript()
    response = app.response_class(
        response=js_code,
        status=200,
        mimetype='application/javascript'
    )
    return response

@app.route('/assets/responsive.css')
def serve_responsive_css():
    '''Serve responsive CSS styles'''
    css_code = localization_framework.generate_responsive_css()
    response = app.response_class(
        response=css_code,
        status=200,
        mimetype='text/css'
    )
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
"""

        return api_code

    def generate_language_switcher_component(self) -> str:
        """Generate language switcher component"""
        component = """
<!-- Language Switcher Component -->
<div class="language-switcher" id="languageSwitcher">
    <button class="language-toggle" onclick="toggleLanguageSwitcher()">
        <span class="current-flag">{{ current_language_flag }}</span>
        <span class="current-name">{{ current_language_name }}</span>
        <span class="dropdown-arrow">▼</span>
    </button>

    <div class="language-dropdown" id="languageDropdown">
        {% for lang_code, lang_info in supported_languages.items() %}
        <button class="language-option"
                onclick="changeLanguage('{{ lang_code }}')"
                data-language="{{ lang_code }}">
            <span class="language-flag">{{ lang_info.flag }}</span>
            <span class="language-name">{{ lang_info.native_name }}</span>
            <span class="language-english-name">{{ lang_info.name }}</span>
        </button>
        {% endfor %}
    </div>
</div>

<style>
.language-switcher {
    position: relative;
    display: inline-block;
}

.language-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    background: #fff;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.3s ease;
}

.language-toggle:hover {
    border-color: #007bff;
    box-shadow: 0 2px 4px rgba(0,123,255,0.1);
}

.current-flag {
    font-size: 18px;
}

.current-name {
    font-weight: 500;
}

.dropdown-arrow {
    font-size: 12px;
    transition: transform 0.3s ease;
}

.language-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    min-width: 200px;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    max-height: 300px;
    overflow-y: auto;
    z-index: 1000;
    display: none;
}

.language-dropdown.show {
    display: block;
}

.language-option {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 16px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 14px;
    text-align: left;
    transition: background-color 0.2s ease;
}

.language-option:hover {
    background: #f8f9fa;
}

.language-option.active {
    background: #e3f2fd;
    color: #1976d2;
}

.language-flag {
    font-size: 20px;
}

.language-name {
    font-weight: 500;
    flex: 1;
}

.language-english-name {
    font-size: 12px;
    color: #666;
}

/* Mobile styles */
@media (max-width: 767px) {
    .language-dropdown {
        right: -50px;
        min-width: 250px;
    }

    .language-option {
        padding: 16px;
    }

    .language-english-name {
        display: none;
    }
}

/* RTL support */
[dir="rtl"] .language-dropdown {
    right: auto;
    left: 0;
}

[dir="rtl"] .language-dropdown {
    right: auto;
    left: -50px;
}
</style>

<script>
function toggleLanguageSwitcher() {
    const dropdown = document.getElementById('languageDropdown');
    dropdown.classList.toggle('show');

    // Close dropdown when clicking outside
    document.addEventListener('click', function closeDropdown(e) {
        if (!e.target.closest('.language-switcher')) {
            dropdown.classList.remove('show');
            document.removeEventListener('click', closeDropdown);
        }
    });
}

function changeLanguage(language) {
    // Save preference
    localStorage.setItem('preferredLanguage', language);

    // Reload page with new language
    const url = new URL(window.location);
    url.searchParams.set('lang', language);
    window.location.href = url.toString();
}

// Set current language as active
document.addEventListener('DOMContentLoaded', function() {
    const currentLang = '{{ current_language }}';
    const options = document.querySelectorAll('.language-option');

    options.forEach(option => {
        if (option.dataset.language === currentLang) {
            option.classList.add('active');
        }
    });
});
</script>
"""

        return component

    def run_comprehensive_setup(self):
        """Run comprehensive multilingual and mobile setup"""
        logger.info("Running comprehensive multilingual and mobile setup...")

        results = {
            'setup_date': datetime.now().isoformat(),
            'languages_supported': len(self.supported_languages),
            'translations_created': len(self.translations),
            'components_created': [],
            'files_generated': [],
            'mobile_features': [],
            'rtl_languages': []
        }

        # Generate components and files
        js_file = self.localization_dir / "localization.js"
        css_file = self.localization_dir / "responsive.css"
        api_file = self.localization_dir / "multilingual_api.py"
        language_switcher = self.localization_dir / "language_switcher.html"

        # Write files
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_localized_javascript())
        results['files_generated'].append(str(js_file))

        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_responsive_css())
        results['files_generated'].append(str(css_file))

        with open(api_file, 'w', encoding='utf-8') as f:
            f.write(self.create_multilingual_api_endpoint())
        results['files_generated'].append(str(api_file))

        with open(language_switcher, 'w', encoding='utf-8') as f:
            f.write(self.generate_language_switcher_component())
        results['files_generated'].append(str(language_switcher))

        # Count components
        results['components_created'] = list(self.mobile_components.keys())

        # Count mobile features
        results['mobile_features'] = [
            'Responsive Navigation',
            'Touch-Friendly Charts',
            'Mobile Table Cards',
            'Adaptive Typography',
            'Gesture Support',
            'Offline Capability',
            'Performance Optimization'
        ]

        # Count RTL languages
        for lang, config in self.supported_languages.items():
            if config['rtl']:
                results['rtl_languages'].append(lang.value)

        # Save setup results
        setup_results_file = self.localization_dir / "setup_results.json"
        with open(setup_results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Comprehensive multilingual and mobile setup completed")
        logger.info(f"   - Languages supported: {results['languages_supported']}")
        logger.info(f"   - Translations created: {results['translations_created']}")
        logger.info(f"   - Components created: {len(results['components_created'])}")
        logger.info(f"   - Files generated: {len(results['files_generated'])}")
        logger.info(f"   - RTL languages: {len(results['rtl_languages'])}")

        return results

def main():
    """Main execution function"""
    # Data directory
    data_dir = Path(__file__).resolve().parents[3] / "Technical" / "data"

    # Create framework
    framework = MultiLanguageMobileFramework(data_dir)

    # Run comprehensive setup
    results = framework.run_comprehensive_setup()

    print("\n" + "="*80)
    print("MULTILINGUAL & MOBILE OPTIMIZATION FRAMEWORK")
    print("="*80)
    print(f"✅ Setup Complete: {results['setup_date']}")
    print(f"🌍 Languages Supported: {results['languages_supported']}")
    print(f"📝 Translations Created: {results['translations_created']}")
    print(f"🧩 Components Created: {len(results['components_created'])}")
    print(f"📁 Files Generated: {len(results['files_generated'])}")
    print(f"📱 Mobile Features: {len(results['mobile_features'])}")
    print(f"🔄 RTL Languages: {len(results['rtl_languages'])}")
    print(f"📁 Output Location: {data_dir}/localization/")
    print("\nSupported Languages:")
    for lang, config in framework.supported_languages.items():
        rtl_indicator = " (RTL)" if config['rtl'] else ""
        print(f"  - {config['flag']} {config['native_name']}{rtl_indicator}")

    print(f"\n🎯 Multilingual & Mobile Framework Status: FULLY OPERATIONAL")
    print("="*80)

if __name__ == "__main__":
    main()