import unittest
from src.data_collector.market_data import MarketDataCollector
from config.config import BINANCE_API_KEY, BINANCE_API_SECRET

class TestMarketDataCollector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialisation avant tous les tests"""
        cls.collector = MarketDataCollector(BINANCE_API_KEY, BINANCE_API_SECRET)
        cls.symbol = 'BTCUSDT'

    def test_get_current_price(self):
        """Test de la récupération du prix actuel"""
        price_data = self.collector.get_current_price(self.symbol)
        
        self.assertIsInstance(price_data, dict)
        self.assertIn('last_price', price_data)
        self.assertIn('volume_24h', price_data)
        self.assertIsInstance(price_data['last_price'], float)
        self.assertIsInstance(price_data['volume_24h'], float)
        self.assertGreater(price_data['last_price'], 0)
        self.assertGreater(price_data['volume_24h'], 0)

    def test_get_klines(self):
        """Test de la récupération des données historiques"""
        klines = self.collector.get_klines(self.symbol, '1h', limit=5)
        
        self.assertIsNotNone(klines)
        self.assertEqual(len(klines), 5)
        self.assertIn('close', klines.columns)
        self.assertIn('volume', klines.columns)

    def test_get_order_book(self):
        """Test de la récupération du carnet d'ordres"""
        order_book = self.collector.get_order_book(self.symbol, limit=5)
        
        self.assertIsInstance(order_book, dict)
        self.assertIn('bids', order_book)
        self.assertIn('asks', order_book)
        self.assertLessEqual(len(order_book['bids']), 5)
        self.assertLessEqual(len(order_book['asks']), 5)

    def test_get_technical_analysis(self):
        """Test de l'analyse technique"""
        technical_analysis = self.collector.get_technical_analysis(self.symbol)
        
        self.assertIsInstance(technical_analysis, dict)
        self.assertIn('indicators', technical_analysis)
        self.assertIn('signals', technical_analysis)
        self.assertIn('summary', technical_analysis)

        required_indicators = ['RSI', 'MACD', 'BB_Upper', 'BB_Lower', 'SMA_20', 'EMA_20']
        required_signals = ['RSI', 'MACD', 'BB']
        
        for indicator in required_indicators:
            self.assertIn(indicator, technical_analysis['indicators'])
        
        for signal in required_signals:
            self.assertIn(signal, technical_analysis['signals'])

    def test_get_market_analysis(self):
        """Test de l'analyse complète du marché"""
        market_analysis = self.collector.get_market_analysis(self.symbol)
        
        self.assertIsInstance(market_analysis, dict)
        self.assertIn('current_price', market_analysis)
        self.assertIn('technical_analysis', market_analysis)
        self.assertIn('order_book', market_analysis)
        self.assertIn('timestamp', market_analysis)

        # Vérification du prix actuel
        self.assertIsInstance(market_analysis['current_price'], dict)
        self.assertIn('last_price', market_analysis['current_price'])
        self.assertIn('volume_24h', market_analysis['current_price'])

        # Vérification de l'analyse technique
        self.assertIsInstance(market_analysis['technical_analysis'], dict)
        self.assertIn('indicators', market_analysis['technical_analysis'])
        self.assertIn('signals', market_analysis['technical_analysis'])
        self.assertIn('summary', market_analysis['technical_analysis'])

        # Vérification du carnet d'ordres
        self.assertIsInstance(market_analysis['order_book'], dict)
        self.assertIn('bids', market_analysis['order_book'])
        self.assertIn('asks', market_analysis['order_book'])

if __name__ == '__main__':
    unittest.main()
