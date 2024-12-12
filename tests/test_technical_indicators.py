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
        assert abs(macd - macd_signal) == pytest.approx(abs(macd_hist), rel=1e-5), "La relation MACD-Signal-Hist n'est pas cohérente"

    def test_bollinger_bands(self, analysis):
        """Test des bandes de Bollinger et leurs relations"""
        bb_upper = analysis['indicators']['BB_upper']
        bb_middle = analysis['indicators']['BB_middle']
        bb_lower = analysis['indicators']['BB_lower']
        
        assert bb_upper > bb_middle > bb_lower, "Les bandes de Bollinger ne sont pas dans le bon ordre"
        assert isinstance(bb_upper, (float, int)), "BB upper doit être un nombre"
        assert isinstance(bb_middle, (float, int)), "BB middle doit être un nombre"
        assert isinstance(bb_lower, (float, int)), "BB lower doit être un nombre"

    def test_all_indicators_present(self, analysis):
        """Test de la présence de tous les indicateurs"""
        required_indicators = {
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
            'BB_upper', 'BB_middle', 'BB_lower'
        }
        assert all(indicator in analysis['indicators'] for indicator in required_indicators), \
            "Certains indicateurs sont manquants"

    def test_signals_consistency(self, analysis):
        """Test de la cohérence des signaux"""
        signals = analysis['signals']
        assert isinstance(signals, dict), "Les signaux doivent être un dictionnaire"
        
        # Vérification des signaux opposés
        if signals.get('RSI_OVERSOLD', False):
            assert not signals.get('RSI_OVERBOUGHT', False), "Le RSI ne peut pas être suracheté et survendu en même temps"
        
        if signals.get('MACD_BULLISH', False):
            assert not signals.get('MACD_BEARISH', False), "Le MACD ne peut pas être haussier et baissier en même temps"

    def test_summary_format(self, analysis):
        """Test du format du résumé"""
        summary = analysis['summary']
        assert isinstance(summary, str), "Le résumé doit être une chaîne de caractères"
        assert len(summary) > 0, "Le résumé ne peut pas être vide"
        
        # Vérifier que le résumé contient des informations sur les indicateurs clés
        key_terms = ['RSI', 'MACD', 'Bollinger']
        assert any(term.lower() in summary.lower() for term in key_terms), \
            "Le résumé doit mentionner au moins un des indicateurs principaux"

    def test_numerical_consistency(self, collector):
        """Test de la cohérence numérique des calculs"""
        # Obtenir les données historiques
        df = collector.get_klines('BTCUSDT', '1h', limit=100)
        analysis = collector.get_technical_analysis('BTCUSDT')
        
        # Vérifier que les valeurs ne sont pas NaN
        for indicator, value in analysis['indicators'].items():
            assert not np.isnan(value), f"L'indicateur {indicator} ne doit pas être NaN"
            assert not np.isinf(value), f"L'indicateur {indicator} ne doit pas être infini"

    def test_technical_analysis_execution(self, collector):
        """Test de l'exécution complète de l'analyse technique"""
        analysis = collector.get_technical_analysis('BTCUSDT')
        
        assert 'indicators' in analysis, "L'analyse doit contenir des indicateurs"
        assert 'signals' in analysis, "L'analyse doit contenir des signaux"
        assert 'summary' in analysis, "L'analyse doit contenir un résumé"
