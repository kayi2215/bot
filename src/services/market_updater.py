import time
import logging
from datetime import datetime
from threading import Thread
from typing import List, Dict, Any

from src.database.mongodb_manager import MongoDBManager
from src.data_collector.market_data import MarketDataCollector
from src.monitoring.api_monitor import APIMonitor
from config.config import BINANCE_API_KEY, BINANCE_API_SECRET

class MarketDataUpdater:
    def __init__(
        self,
        symbols: List[str],
        update_interval: int = 60,  # Par défaut, mise à jour toutes les 60 secondes
        max_retries: int = 3
    ):
        """
        Initialise le service de mise à jour des données de marché
        
        Args:
            symbols: Liste des paires de trading à surveiller
            update_interval: Intervalle de mise à jour en secondes
            max_retries: Nombre maximum de tentatives en cas d'échec
        """
        self.symbols = symbols
        self.update_interval = update_interval
        self.max_retries = max_retries
        
        # Initialisation des composants
        self.db = MongoDBManager()
        self.data_collector = MarketDataCollector(
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET
        )
        self.api_monitor = APIMonitor()
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        
        # Flag pour contrôler l'exécution
        self.is_running = False
        self.update_thread = None

    def start(self):
        """Démarre le service de mise à jour"""
        if self.is_running:
            self.logger.warning("Market data updater is already running")
            return
            
        self.is_running = True
        self.update_thread = Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        self.logger.info("Market data updater started")

    def stop(self):
        """Arrête le service de mise à jour"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
        self.logger.info("Market data updater stopped")

    def _update_loop(self):
        """Boucle principale de mise à jour"""
        while self.is_running:
            try:
                # Vérifie d'abord la disponibilité de l'API
                api_endpoint = "https://api.binance.com/api/v3/ping"  # Endpoint de test Binance
                if not self.api_monitor.check_api_health(api_endpoint):
                    self.logger.error("API is not healthy, skipping update")
                    time.sleep(self.update_interval)
                    continue

                # Mise à jour pour chaque symbole
                for symbol in self.symbols:
                    self._update_symbol_data(symbol)

                # Attente jusqu'à la prochaine mise à jour
                time.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"Error in update loop: {str(e)}")
                time.sleep(self.update_interval)

    def _update_symbol_data(self, symbol: str) -> bool:
        """
        Met à jour les données pour un symbole spécifique
        
        Args:
            symbol: Symbole de la paire de trading
            
        Returns:
            bool: True si la mise à jour est réussie, False sinon
        """
        retries = 0
        while retries < self.max_retries:
            try:
                # Récupération des données
                market_data = self._collect_market_data(symbol)
                if not market_data:
                    raise Exception("No market data received")

                # Stockage dans la base de données
                self.db.store_market_data(symbol, market_data)
                
                # Calcul et stockage des indicateurs
                indicators = self._calculate_indicators(symbol, market_data)
                if indicators:
                    self.db.store_indicators(symbol, indicators)

                self.logger.info(f"Successfully updated data for {symbol}")
                return True

            except Exception as e:
                retries += 1
                self.logger.error(f"Error updating {symbol} (attempt {retries}/{self.max_retries}): {str(e)}")
                if retries < self.max_retries:
                    time.sleep(2 ** retries)  # Backoff exponentiel
                
        return False

    def _collect_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Collecte les données de marché pour un symbole
        
        Args:
            symbol: Symbole de la paire de trading
            
        Returns:
            Dict contenant les données de marché
        """
        try:
            # Récupération du prix actuel
            current_price = self.data_collector.get_current_price(symbol)
            
            # Récupération du carnet d'ordres
            order_book = self.data_collector.get_order_book(symbol)
            
            # Récupération des dernières transactions
            recent_trades = self.data_collector.get_recent_trades(symbol)
            
            # Construction du dictionnaire de données
            market_data = {
                "timestamp": datetime.now(),
                "price": current_price,
                "order_book": order_book,
                "recent_trades": recent_trades
            }
            
            return market_data

        except Exception as e:
            self.logger.error(f"Error collecting market data for {symbol}: {str(e)}")
            raise

    def _calculate_indicators(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcule les indicateurs techniques
        
        Args:
            symbol: Symbole de la paire de trading
            market_data: Données de marché actuelles
            
        Returns:
            Dict contenant les indicateurs calculés
        """
        try:
            # Récupération des données historiques pour le calcul des indicateurs
            historical_data = self.data_collector.get_klines(
                symbol=symbol,
                interval="1h",
                limit=100
            )
            
            if not historical_data or len(historical_data) == 0:
                self.logger.warning(f"No historical data available for {symbol}")
                return {
                    "timestamp": datetime.now(),
                    "symbol": symbol,
                    "calculations": {}
                }
            
            # TODO: Implémenter le calcul des indicateurs techniques
            # Cette partie devrait être identique pour Bybit et Binance
            indicators = {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "calculations": {}
            }
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {str(e)}")
            return {
                "timestamp": datetime.now(),
                "symbol": symbol,
                "calculations": {}
            }

    def get_latest_data(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère les dernières données de marché pour un symbole
        
        Args:
            symbol: Symbole de la paire de trading
            
        Returns:
            Dict contenant les dernières données de marché
        """
        try:
            # Récupération des dernières données depuis MongoDB
            latest_data = self.db.get_latest_market_data(symbol)
            
            if not latest_data:
                self.logger.warning(f"No latest data found for {symbol}")
                return {
                    "symbol": symbol,
                    "timestamp": datetime.now(),
                    "price": None,
                    "volume": None
                }
                
            return latest_data
            
        except Exception as e:
            self.logger.error(f"Error getting latest data for {symbol}: {str(e)}")
            return {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "price": None,
                "volume": None
            }
