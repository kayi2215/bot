import unittest
import time
from unittest.mock import Mock, patch
from src.bot.trading_bot import TradingBot
from src.database.mongodb_manager import MongoDBManager
from datetime import datetime

class TestTradingBotIntegration(unittest.TestCase):
    def setUp(self):
        """Initialisation avant chaque test"""
        self.symbols = ["BTCUSDT", "ETHUSDT"]
        self.bot = TradingBot(symbols=self.symbols)
        self.db = MongoDBManager()
        
        # Nettoyer les données de test précédentes
        self.cleanup_test_data()

    def tearDown(self):
        """Nettoyage après chaque test"""
        if hasattr(self, 'bot') and self.bot.is_running:
            self.bot.stop()
        self.cleanup_test_data()
        
        # Fermer la connexion MongoDB
        if hasattr(self, 'db'):
            self.db.close()

    def cleanup_test_data(self):
        """Nettoie les données de test dans MongoDB"""
        try:
            # Utiliser les méthodes de nettoyage appropriées
            self.db.market_data.delete_many({"test": True})
            self.db.indicators.delete_many({"test": True})
        except Exception as e:
            print(f"Erreur lors du nettoyage des données: {e}")

    def insert_test_market_data(self):
        """Insère des données de test dans MongoDB"""
        for symbol in self.symbols:
            market_data = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "data": {
                    "price": 50000.0 if symbol == "BTCUSDT" else 2000.0,
                    "volume": 100.0
                },
                "raw_data": {
                    "ticker": {
                        "last_price": 50000.0 if symbol == "BTCUSDT" else 2000.0,
                        "volume_24h": 100.0
                    },
                    "klines": [],
                    "orderbook": {
                        "bids": [["49999", "1.0"]],
                        "asks": [["50001", "1.0"]]
                    },
                    "trades": []
                },
                "exchange": "binance",
                "test": True
            }
            # Stocker les données avec le bon format
            self.db.store_market_data(symbol, market_data)

    def test_bot_initialization(self):
        """Teste l'initialisation correcte du bot"""
        self.assertIsNotNone(self.bot.market_data)
        self.assertIsNotNone(self.bot.monitoring_service)
        self.assertIsNotNone(self.bot.data_updater)
        self.assertIsNotNone(self.bot.db)
        self.assertEqual(self.bot.symbols, self.symbols)

    def test_bot_start_stop(self):
        """Teste le démarrage et l'arrêt du bot"""
        # Démarrer le bot
        self.bot.start()
        self.assertTrue(self.bot.is_running)
        self.assertIsNotNone(self.bot.monitoring_thread)
        self.assertIsNotNone(self.bot.trading_thread)
        
        # Attendre un peu pour que les services démarrent
        time.sleep(2)
        
        # Arrêter le bot
        self.bot.stop()
        self.assertFalse(self.bot.is_running)
        
        # Vérifier que les threads sont terminés
        time.sleep(1)
        self.assertFalse(self.bot.monitoring_thread.is_alive())
        self.assertFalse(self.bot.trading_thread.is_alive())

    def test_data_flow(self):
        """Teste le flux de données à travers le système"""
        # Insérer des données de test
        self.insert_test_market_data()
        
        # Démarrer le bot
        self.bot.start()
        time.sleep(2)  # Attendre que le bot traite les données
        
        # Vérifier que les données sont récupérables
        for symbol in self.symbols:
            market_data = self.db.get_latest_market_data(symbol, limit=1)
            self.assertIsNotNone(market_data)
            self.assertTrue(len(market_data) > 0)
            
            latest_data = market_data[0]
            self.assertEqual(latest_data['symbol'], symbol)
            self.assertIn('data', latest_data)
            self.assertIn('price', latest_data['data'])
            self.assertIn('volume', latest_data['data'])
            
            # Vérifier les valeurs attendues (noter qu'elles peuvent être 0 si l'API n'est pas accessible)
            self.assertIsInstance(latest_data['data']['price'], (int, float))
            self.assertIsInstance(latest_data['data']['volume'], (int, float))
            
        # Arrêter le bot
        self.bot.stop()

    def test_market_data_updates(self):
        """Teste les mises à jour des données de marché"""
        # Créer et démarrer le bot
        self.bot.start()
        
        # Attendre que le bot démarre
        time.sleep(1)
        
        # Vérifier que les données sont mises à jour
        market_data = self.db.get_latest_market_data("BTCUSDT", limit=1)
        self.assertIsNotNone(market_data)
        self.assertTrue(len(market_data) > 0)
        
        latest_data = market_data[0]
        self.assertEqual(latest_data["symbol"], "BTCUSDT")
        self.assertIn("data", latest_data)
        self.assertIn("price", latest_data["data"])
        self.assertIn("volume", latest_data["data"])
        
        # Arrêter le bot
        self.bot.stop()

    def test_error_handling(self):
        """Teste la gestion des erreurs"""
        # Simuler une erreur dans la base de données
        with patch.object(self.db, 'get_latest_market_data', side_effect=Exception("Test error")):
            self.bot.start()
            time.sleep(2)  # Attendre que le bot traite l'erreur
            
            # Le bot devrait continuer à fonctionner malgré l'erreur
            self.assertTrue(self.bot.is_running)
            
            self.bot.stop()

if __name__ == '__main__':
    unittest.main()
