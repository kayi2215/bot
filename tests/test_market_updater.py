import unittest
from unittest.mock import Mock, patch
import time
from datetime import datetime

from src.services.market_updater import MarketDataUpdater

class TestMarketDataUpdater(unittest.TestCase):
    def setUp(self):
        """Configure l'environnement de test"""
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        self.updater = MarketDataUpdater(
            symbols=self.symbols,
            update_interval=1,  # 1 seconde pour les tests
            max_retries=2
        )

    def tearDown(self):
        """Nettoyage après chaque test"""
        if hasattr(self, 'updater'):
            self.updater.stop()
            if hasattr(self.updater, 'db'):
                self.updater.db.close()

    @patch('src.services.market_updater.MarketDataCollector')
    @patch('src.services.market_updater.MongoDBManager')
    def test_market_data_update(self, mock_db, mock_collector):
        """Teste la mise à jour des données de marché"""
        # Configuration des mocks
        mock_collector_instance = mock_collector.return_value
        mock_collector_instance.get_current_price.return_value = 50000.0
        mock_collector_instance.get_order_book.return_value = {
            "bids": [[49999.0, 1.0]],
            "asks": [[50001.0, 1.0]]
        }
        mock_collector_instance.get_recent_trades.return_value = [
            {"price": 50000.0, "qty": 1.0}
        ]

        # Mock the API monitor
        with patch('src.services.market_updater.APIMonitor') as mock_monitor:
            mock_monitor_instance = mock_monitor.return_value
            mock_monitor_instance.check_api_health.return_value = True
            
            # Create updater with shorter interval for testing
            self.updater = MarketDataUpdater(
                symbols=self.symbols,
                update_interval=0.1  # 100ms for faster testing
            )
            
            # Démarre le service
            self.updater.start()
            
            # Attend quelques cycles de mise à jour
            time.sleep(0.5)  # Should allow for multiple updates
            
            # Arrête le service
            self.updater.stop()
            
            # Vérifie que les données ont été collectées et stockées
            mock_collector_instance.get_current_price.assert_called()
            mock_collector_instance.get_order_book.assert_called()
            mock_collector_instance.get_recent_trades.assert_called()
            mock_db.return_value.store_market_data.assert_called()

    @patch('src.services.market_updater.APIMonitor')
    def test_api_availability_check(self, mock_monitor):
        """Teste la vérification de la disponibilité de l'API"""
        # Configure le mock pour simuler une API indisponible
        mock_monitor_instance = mock_monitor.return_value
        mock_monitor_instance.check_api_health.return_value = False
        
        # Create updater with shorter interval for testing
        self.updater = MarketDataUpdater(
            symbols=self.symbols,
            update_interval=0.1  # 100ms for faster testing
        )
        
        # Démarre le service
        self.updater.start()
        
        # Attend quelques cycles
        time.sleep(0.3)  # Should allow for multiple checks
        
        # Arrête le service
        self.updater.stop()
        
        # Vérifie que la vérification a été effectuée avec le bon endpoint
        mock_monitor_instance.check_api_health.assert_called_with("https://api.binance.com/api/v3/ping")

    @patch('src.services.market_updater.MarketDataCollector')
    @patch('src.services.market_updater.MongoDBManager')
    def test_calculate_indicators(self, mock_db, mock_collector):
        """Test le calcul des indicateurs techniques"""
        symbol = "BTCUSDT"
        
        # Mock des données historiques
        historical_data = [
            {
                "timestamp": datetime.now(),
                "open": "50000",
                "high": "51000", 
                "low": "49000",
                "close": "50500",
                "volume": "100"
            }
        ]
        
        mock_collector.return_value.get_klines.return_value = historical_data
        
        # Test avec des données valides
        result = self.updater._calculate_indicators(symbol, {})
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], symbol)
        self.assertIn("timestamp", result)
        self.assertIn("calculations", result)
        
        # Test avec aucune donnée historique
        mock_collector.return_value.get_klines.return_value = []
        result = self.updater._calculate_indicators(symbol, {})
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["symbol"], symbol)
        self.assertIn("timestamp", result)
        self.assertEqual(result["calculations"], {})

    def test_service_control(self):
        """Teste le contrôle du service (démarrage/arrêt)"""
        # Vérifie l'état initial
        self.assertFalse(self.updater.is_running)
        
        # Démarre le service
        self.updater.start()
        self.assertTrue(self.updater.is_running)
        
        # Arrête le service
        self.updater.stop()
        self.assertFalse(self.updater.is_running)

if __name__ == '__main__':
    unittest.main()
