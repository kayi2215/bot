import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from src.data_collector.market_data import MarketDataCollector
from src.database.mongodb_manager import MongoDBManager
from config.config import BINANCE_API_KEY, BINANCE_API_SECRET
import pandas as pd

class MarketUpdater:
    def __init__(self, symbols: List[str], db: Optional[MongoDBManager] = None, 
                 api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialise le service de mise à jour des données de marché
        
        Args:
            symbols: Liste des paires de trading à surveiller
            db: Instance optionnelle de MongoDBManager
            api_key: Clé API Binance (optionnelle, utilise la config par défaut si non fournie)
            api_secret: Secret API Binance (optionnel, utilise la config par défaut si non fourni)
        """
        self.symbols = symbols
        self.db = db or MongoDBManager()
        self.stop_event = threading.Event()
        self.shutdown_complete = threading.Event()
        self.collector = MarketDataCollector(
            api_key=api_key or BINANCE_API_KEY,
            api_secret=api_secret or BINANCE_API_SECRET
        )
        self.logger = logging.getLogger('market_updater')
        self.update_interval = 10  # Intervalle de mise à jour en secondes
        self.max_retries = 3  # Nombre maximum de tentatives en cas d'erreur
        
        # Dictionnaire pour suivre les erreurs par symbole
        self.error_counts: Dict[str, int] = {symbol: 0 for symbol in symbols}

    def update_market_data(self, symbol: str) -> bool:
        """Met à jour les données de marché pour un symbole donné"""
        try:
            # Récupération des données
            ticker_data = self.collector.get_current_price(symbol)
            klines_data = self.collector.get_klines(symbol, interval='1m', limit=100)
            orderbook_data = self.collector.get_order_book(symbol, limit=100)
            trades_data = self.collector.get_recent_trades(symbol, limit=50)

            # Préparation des données pour la sauvegarde
            market_data = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'ticker': ticker_data,
                'klines': klines_data.to_dict('records') if isinstance(klines_data, pd.DataFrame) else klines_data,
                'orderbook': orderbook_data,
                'trades': trades_data
            }

            # Sauvegarde des données
            self.db.store_market_data(market_data)

            # Réinitialisation du compteur d'erreurs
            self.error_counts[symbol] = 0
            return True

        except Exception as e:
            # Gestion des erreurs
            self.error_counts[symbol] += 1
            self.logger.error(f"Erreur lors de la mise à jour des données pour {symbol} (tentative {self.error_counts[symbol]}): {str(e)}")
            return False

    def run(self):
        """Lance la boucle de mise à jour des données"""
        self.logger.info("Démarrage du service de mise à jour des données")
        
        while not self.stop_event.is_set():
            try:
                for symbol in self.symbols:
                    if self.stop_event.is_set():
                        break
                        
                    # Mise à jour des données avec gestion des erreurs
                    if not self.update_market_data(symbol):
                        # Si trop d'erreurs pour ce symbole, on le met en pause temporaire
                        if self.error_counts[symbol] >= self.max_retries:
                            self.logger.warning(f"Trop d'erreurs pour {symbol}, mise en pause temporaire")
                            time.sleep(60)  # Pause d'une minute avant de réessayer
                            self.error_counts[symbol] = 0  # Réinitialisation du compteur
                    
                    time.sleep(self.update_interval)  # Pause entre chaque symbole
                    
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle principale: {str(e)}")
                time.sleep(30)  # Pause plus longue en cas d'erreur générale
                
        self.logger.info("Arrêt du service de mise à jour des données")
        self.shutdown_complete.set()

    def stop(self):
        """Arrête proprement le service de mise à jour"""
        self.logger.info("Demande d'arrêt du service de mise à jour")
        self.stop_event.set()
        
        # Attente de l'arrêt complet avec timeout
        if not self.shutdown_complete.wait(timeout=5):
            self.logger.warning("Le service de mise à jour ne s'est pas arrêté dans le délai imparti")
