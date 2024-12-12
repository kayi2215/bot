import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import pandas as pd

from src.data_collector.market_data import MarketDataCollector
from src.database.mongodb_manager import MongoDBManager
from src.monitoring.api_monitor import APIMonitor

class MarketUpdater:
    def __init__(
        self,
        symbols: List[str],
        db: Optional[MongoDBManager] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_testnet: bool = False
    ):
        """
        Initialise le service de mise à jour des données de marché
        
        Args:
            symbols: Liste des paires de trading à surveiller
            db: Instance optionnelle de MongoDBManager
            api_key: Clé API Binance (optionnelle, utilise la config par défaut si non fournie)
            api_secret: Secret API Binance (optionnel, utilise la config par défaut si non fourni)
            use_testnet: Utiliser le testnet Binance au lieu du mainnet
        """
        load_dotenv()
        
        # Configurer le testnet si nécessaire
        if use_testnet:
            os.environ['USE_TESTNET'] = 'true'
        
        self.symbols = symbols
        self.db = db or MongoDBManager()
        self.stop_event = threading.Event()
        self.shutdown_complete = threading.Event()
        
        # Configuration des clés API
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Les clés API Binance sont requises")
        
        # Initialisation des composants
        self.collector = MarketDataCollector(
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        self.api_monitor = APIMonitor(testnet=os.getenv('USE_TESTNET', 'false').lower() == 'true')
        
        # Configuration du logging et des paramètres
        self.logger = logging.getLogger(__name__)
        self.update_interval = 10  # Intervalle de mise à jour en secondes
        self.max_retries = 3  # Nombre maximum de tentatives en cas d'erreur
        
        # Dictionnaire pour suivre les erreurs par symbole
        self.error_counts: Dict[str, int] = {symbol: 0 for symbol in symbols}

    def update_market_data(self, symbol: str) -> bool:
        """Met à jour les données de marché pour un symbole donné"""
        try:
            # Vérifie d'abord la disponibilité de l'API
            health_status = self.api_monitor.check_api_health()
            if not health_status or health_status.get('status') != 'OK':
                raise Exception("API Binance is not healthy")

            # Récupération des données
            ticker_data = self.collector.get_current_price(symbol)
            klines_data = self.collector.get_klines(symbol, interval='1m', limit=100)
            orderbook_data = self.collector.get_order_book(symbol, limit=100)
            trades_data = self.collector.get_recent_trades(symbol, limit=50)
            
            # Préparation des données pour la sauvegarde
            market_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'data': {
                    'price': float(ticker_data.get('last_price', 0)),
                    'volume': float(ticker_data.get('volume_24h', 0))
                },
                'raw_data': {
                    'ticker': ticker_data,
                    'klines': klines_data.to_dict('records') if isinstance(klines_data, pd.DataFrame) else klines_data,
                    'orderbook': orderbook_data,
                    'trades': trades_data
                },
                'exchange': 'binance'
            }
            
            # Sauvegarde des données
            self.db.store_market_data(symbol, market_data)
            
            # Réinitialisation du compteur d'erreurs
            self.error_counts[symbol] = 0
            return True
            
        except Exception as e:
            # Gestion des erreurs
            self.error_counts[symbol] += 1
            self.logger.error(f"Erreur lors de la mise à jour des données pour {symbol} (tentative {self.error_counts[symbol]}): {str(e)}")
            return False

    def run(self):
        """Démarre la boucle de mise à jour des données"""
        while not self.stop_event.is_set():
            for symbol in self.symbols:
                if self.stop_event.is_set():
                    break
                    
                # Vérifier le nombre d'erreurs consécutives
                if self.error_counts[symbol] >= self.max_retries:
                    self.logger.error(f"Trop d'erreurs consécutives pour {symbol}, passage au symbole suivant")
                    continue
                    
                # Mise à jour des données
                self.update_market_data(symbol)
                
            # Attendre avant la prochaine mise à jour
            time.sleep(self.update_interval)
            
        self.shutdown_complete.set()

    def stop(self):
        """Arrête la boucle de mise à jour des données"""
        self.logger.info("Arrêt du service de mise à jour des données...")
        self.stop_event.set()
        
        # Attendre l'arrêt complet avec timeout
        if not self.shutdown_complete.wait(timeout=5):
            self.logger.warning("Le service de mise à jour ne s'est pas arrêté dans le délai imparti")
