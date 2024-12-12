import pytest
import numpy as np
from src.data_collector.market_data import MarketDataCollector
from config.config import BINANCE_API_KEY, BINANCE_API_SECRET

class TestTechnicalIndicators:
    @pytest.fixture
    def collector(self):
        return MarketDataCollector(BINANCE_API_KEY, BINANCE_API_SECRET)

    @pytest.fixture
    def analysis(self, collector):
        return collector.get_technical_analysis('BTCUSDT')

    def test_rsi_calculation(self, analysis):
        """Test du RSI et de ses limites"""
        rsi = analysis['indicators']['RSI']
        assert isinstance(rsi, (float, int)), "Le RSI doit être un nombre"
        assert 0 <= rsi <= 100, f"Le RSI doit être entre 0 et 100, valeur actuelle: {rsi}"

    def test_macd_calculation(self, analysis):
        """Test du MACD et de son signal"""
        macd = analysis['indicators']['MACD']
        macd_signal = analysis['indicators']['MACD_Signal']
        macd_hist = analysis['indicators']['MACD_Hist']
        
        assert isinstance(macd, (float, int)), "Le MACD doit être un nombre"
        assert isinstance(macd_signal, (float, int)), "Le signal MACD doit être un nombre"
        assert isinstance(macd_hist, (float, int)), "L'histogramme MACD doit être un nombre"

    def test_bollinger_bands(self, analysis):
        """Test des bandes de Bollinger et leurs relations"""
        bb_upper = analysis['indicators']['BB_Upper']
        bb_middle = analysis['indicators']['BB_Middle']
        bb_lower = analysis['indicators']['BB_Lower']
        
        assert bb_upper > bb_middle > bb_lower, "Les bandes de Bollinger ne sont pas dans le bon ordre"
        assert isinstance(bb_upper, (float, int)), "BB upper doit être un nombre"
        assert isinstance(bb_middle, (float, int)), "BB middle doit être un nombre"
        assert isinstance(bb_lower, (float, int)), "BB lower doit être un nombre"

    def test_all_indicators_present(self, analysis):
        """Test de la présence de tous les indicateurs"""
        required_indicators = {
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
            'BB_Upper', 'BB_Middle', 'BB_Lower'
        }
        assert all(indicator in analysis['indicators'] for indicator in required_indicators), \
            "Certains indicateurs sont manquants"

    def test_signals_format(self, analysis):
        """Test du format des signaux"""
        signals = analysis['signals']
        assert isinstance(signals, dict), "Les signaux doivent être un dictionnaire"
        
        # Vérifier que chaque signal est une chaîne de caractères
        for signal_name, signal_value in signals.items():
            assert isinstance(signal_value, str), f"Le signal {signal_name} doit être une chaîne de caractères"
            assert len(signal_value) > 0, f"Le signal {signal_name} ne peut pas être vide"

    def test_summary_format(self, analysis):
        """Test du format du résumé"""
        assert 'summary' in analysis, "L'analyse doit contenir un résumé"
        assert isinstance(analysis['summary'], str), "Le résumé doit être une chaîne de caractères"
        assert len(analysis['summary']) > 0, "Le résumé ne peut pas être vide"

    def test_numerical_values(self, analysis):
        """Test de la validité des valeurs numériques"""
        for indicator, value in analysis['indicators'].items():
            assert isinstance(value, (float, int)), f"L'indicateur {indicator} doit être un nombre"
            assert not np.isnan(value), f"L'indicateur {indicator} ne doit pas être NaN"
            assert not np.isinf(value), f"L'indicateur {indicator} ne doit pas être infini"

    def test_analysis_structure(self, analysis):
        """Test de la structure complète de l'analyse"""
        required_keys = {'indicators', 'signals', 'summary'}
        assert all(key in analysis for key in required_keys), \
            "L'analyse doit contenir tous les éléments requis (indicators, signals, summary)"

if __name__ == "__main__":
    pytest.main([__file__])
