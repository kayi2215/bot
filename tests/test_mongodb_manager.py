import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.database.mongodb_manager import MongoDBManager
import time

class TestMongoDBManager(unittest.TestCase):
    def setUp(self):
        """Configure le gestionnaire MongoDB pour les tests"""
        self.mongodb_manager = MongoDBManager()
        
    def tearDown(self):
        """Nettoie après les tests"""
        if hasattr(self.mongodb_manager, 'client'):
            self.mongodb_manager.client.close()

    def test_store_and_retrieve_market_data(self):
        """Teste le stockage et la récupération des données de marché"""
        # Données de test
        symbol = "BTCUSDT"
        test_data = {
            "price": 50000.0,
            "volume": 100.0
        }
        
        # Stockage des données
        self.mongodb_manager.store_market_data(symbol, test_data)
        
        # Récupération des données
        retrieved_data = self.mongodb_manager.get_latest_market_data(symbol, limit=1)
        
        # Vérifications
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(len(retrieved_data), 1)
        self.assertEqual(retrieved_data[0]["symbol"], symbol)
        self.assertEqual(retrieved_data[0]["data"], test_data)

    def test_store_and_retrieve_indicators(self):
        """Teste le stockage et la récupération des indicateurs"""
        # Données de test
        symbol = "BTCUSDT"
        test_indicators = {
            "rsi": 65.5,
            "macd": {"value": 100.0, "signal": 95.0}
        }
        
        # Stockage des indicateurs
        self.mongodb_manager.store_indicators(symbol, test_indicators)
        
        # Récupération des indicateurs
        retrieved_indicators = self.mongodb_manager.get_latest_indicators(symbol, limit=1)
        
        # Vérifications
        self.assertIsNotNone(retrieved_indicators)
        self.assertEqual(len(retrieved_indicators), 1)
        self.assertEqual(retrieved_indicators[0]["symbol"], symbol)
        self.assertEqual(retrieved_indicators[0]["indicators"], test_indicators)

    def test_store_and_retrieve_trades(self):
        """Teste le stockage et la récupération des transactions"""
        # Données de test
        trade_data = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "price": 50000.0,
            "quantity": 1.0
        }
        
        # Stockage de la transaction
        self.mongodb_manager.store_trade(trade_data)
        
        # Récupération des transactions
        start_time = datetime.now() - timedelta(minutes=1)
        trades = self.mongodb_manager.get_trades_by_timeframe(start_time)
        
        # Vérifications
        self.assertEqual(len(trades), 1)
        retrieved_trade = trades[0]
        self.assertEqual(retrieved_trade["symbol"], trade_data["symbol"])
        self.assertEqual(retrieved_trade["side"], trade_data["side"])
        self.assertEqual(retrieved_trade["price"], trade_data["price"])
        self.assertEqual(retrieved_trade["quantity"], trade_data["quantity"])

    def test_store_and_retrieve_monitoring_data(self):
        """Teste le stockage et la récupération des données de monitoring"""
        # Données de test
        monitoring_data = {
            "endpoint": "market_data",
            "response_time": 0.5,
            "status": "success"
        }
        
        # Stockage des données
        self.mongodb_manager.store_monitoring_data(monitoring_data)
        
        # Récupération des données
        start_time = datetime.now() - timedelta(minutes=1)
        retrieved_data = self.mongodb_manager.get_monitoring_data(start_time)
        
        # Vérifications
        self.assertEqual(len(retrieved_data), 1)
        self.assertEqual(retrieved_data[0]["endpoint"], monitoring_data["endpoint"])
        self.assertEqual(retrieved_data[0]["response_time"], monitoring_data["response_time"])
        self.assertEqual(retrieved_data[0]["status"], monitoring_data["status"])

    def test_store_and_retrieve_api_metrics(self):
        """Teste le stockage et la récupération des métriques d'API"""
        # Données de test
        metric_data = {
            "endpoint": "/api/v1/trades",
            "metric_type": "latency",
            "value": 0.2
        }
        
        # Stockage des métriques
        self.mongodb_manager.store_api_metric(metric_data)
        
        # Récupération des métriques
        retrieved_metrics = self.mongodb_manager.get_api_metrics(
            endpoint=metric_data["endpoint"],
            metric_type=metric_data["metric_type"]
        )
        
        # Vérifications
        self.assertEqual(len(retrieved_metrics), 1)
        self.assertEqual(retrieved_metrics[0]["endpoint"], metric_data["endpoint"])
        self.assertEqual(retrieved_metrics[0]["metric_type"], metric_data["metric_type"])
        self.assertEqual(retrieved_metrics[0]["value"], metric_data["value"])

    def test_store_and_retrieve_strategy_config(self):
        """Teste le stockage et la récupération de la configuration de stratégie"""
        # Données de test
        strategy_name = "RSI_Strategy"
        config_data = {
            "rsi_period": 14,
            "overbought": 70,
            "oversold": 30
        }
        
        # Stockage de la configuration
        self.mongodb_manager.store_strategy_config(strategy_name, config_data)
        
        # Récupération de la configuration
        retrieved_config = self.mongodb_manager.get_strategy_config(strategy_name)
        
        # Vérifications
        self.assertIsNotNone(retrieved_config)
        self.assertEqual(retrieved_config["strategy_name"], strategy_name)
        self.assertEqual(retrieved_config["config"], config_data)

    def test_bulk_operations(self):
        """Teste les opérations en masse"""
        # Données de test pour market data
        market_data_list = [
            {
                "symbol": "BTCUSDT",
                "data": {"price": 50000.0, "volume": 100.0}
            },
            {
                "symbol": "ETHUSDT",
                "data": {"price": 3000.0, "volume": 200.0}
            }
        ]
        
        # Test du stockage en masse des données de marché
        self.mongodb_manager.store_market_data_bulk(market_data_list)
        
        # Vérification des données stockées
        for data in market_data_list:
            retrieved_data = self.mongodb_manager.get_latest_market_data(data["symbol"], limit=1)
            self.assertEqual(len(retrieved_data), 1)
            self.assertEqual(retrieved_data[0]["data"], data["data"])

    def test_cleanup_old_data(self):
        """Teste le nettoyage des anciennes données"""
        # Stockage de données de test
        symbol = "BTCUSDT"
        test_data = {"price": 45000.0, "volume": 90.0}
        self.mongodb_manager.store_market_data(symbol, test_data)
        
        # Stockage de données de monitoring
        monitoring_data = {"endpoint": "test", "status": "success"}
        self.mongodb_manager.store_monitoring_data(monitoring_data)
        
        # Attendre un peu pour s'assurer que les données sont stockées
        time.sleep(0.5)
        
        # Nettoyage des données
        self.mongodb_manager.cleanup_old_data(days_to_keep=0)
        
        # Attendre un peu pour s'assurer que les données sont supprimées
        time.sleep(0.5)
        
        # Vérification que les données ont été supprimées
        retrieved_market_data = self.mongodb_manager.get_latest_market_data(symbol, limit=1)
        self.assertEqual(len(retrieved_market_data), 0)
        
        start_time = datetime.now() - timedelta(minutes=1)
        retrieved_monitoring = self.mongodb_manager.get_monitoring_data(start_time)
        self.assertEqual(len(retrieved_monitoring), 0)

if __name__ == '__main__':
    unittest.main()
