import threading
import time
from typing import Optional
from src.data_collector.market_data import MarketDataCollector
from src.monitoring.api_monitor import APIMonitor
from src.monitoring.run_monitoring import MonitoringService
from src.services.market_updater import MarketUpdater
from src.database.mongodb_manager import MongoDBManager
from config.config import BINANCE_API_KEY, BINANCE_API_SECRET
import logging
from datetime import datetime

class TradingBot:
    def __init__(self, symbols=None, db=None):
        # Configuration du logging
        self.setup_logging()
        
        # Liste des symboles à trader
        self.symbols = symbols or ["BTCUSDT"]
        
        # Initialisation de la base de données
        self.db = db if db is not None else MongoDBManager()
        
        # Initialisation des composants
        self.market_data = MarketDataCollector(BINANCE_API_KEY, BINANCE_API_SECRET)
        self.monitoring_service = MonitoringService(check_interval=60)
        self.data_updater = MarketUpdater(
            self.symbols,
            self.db
        )
        
        # État du bot
        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.trading_thread: Optional[threading.Thread] = None
        self.data_update_thread: Optional[threading.Thread] = None
        
        self.logger.info("Bot de trading initialisé")

    def setup_logging(self):
        """Configure le système de logging pour le bot"""
        self.logger = logging.getLogger('trading_bot')
        self.logger.setLevel(logging.INFO)
        
        # Handler pour le fichier
        fh = logging.FileHandler('logs/trading_bot.log')
        fh.setLevel(logging.INFO)
        
        # Handler pour la console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def start_monitoring(self):
        """Démarre le service de monitoring dans un thread séparé"""
        def run_monitoring():
            self.logger.info("Service de monitoring démarré")
            self.monitoring_service.run()
        
        self.monitoring_thread = threading.Thread(target=run_monitoring)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

    def trading_loop(self):
        """Boucle principale de trading"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.is_running:
            try:
                # Vérification de la santé de l'API via le monitoring
                monitoring_metrics = self.monitoring_service.monitor.get_metrics_summary()
                if monitoring_metrics.get('error_rate', 0) > 0.1:  # Plus de 10% d'erreurs
                    self.logger.warning("Taux d'erreur API élevé, trading en pause")
                    time.sleep(1)  # Pause courte pour vérifier is_running plus souvent
                    continue

                for symbol in self.symbols:
                    if not self.is_running:
                        break
                        
                    try:
                        # Récupération des dernières données depuis MongoDB
                        market_data = self.db.get_latest_market_data(symbol, limit=1)
                        if not market_data or len(market_data) == 0:
                            self.logger.warning(f"Pas de données récentes pour {symbol}")
                            continue

                        latest_data = market_data[0]
                        # Vérification de la structure des données
                        if 'data' not in latest_data or 'price' not in latest_data['data']:
                            self.logger.error(f"Structure de données invalide pour {symbol}")
                            continue

                        # Traitement des données de marché avec la nouvelle structure
                        self.process_market_data(latest_data)
                        
                        consecutive_errors = 0  # Réinitialisation du compteur d'erreurs
                        
                    except Exception as e:
                        self.logger.error(f"Erreur lors du traitement de {symbol}: {str(e)}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            self.logger.error("Trop d'erreurs consécutives, arrêt du bot")
                            self.is_running = False  # Marquer l'arrêt sans appeler stop() directement
                            break
                
                # Petite pause entre les cycles
                time.sleep(1)  # Pause courte pour vérifier is_running plus souvent
                
            except Exception as e:
                self.logger.error(f"Erreur dans la boucle de trading: {str(e)}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.error("Trop d'erreurs consécutives, arrêt du bot")
                    self.is_running = False  # Marquer l'arrêt sans appeler stop() directement
                    break
                time.sleep(1)  # Pause courte pour vérifier is_running plus souvent

    def process_market_data(self, market_data):
        """Traite les données de marché pour prendre des décisions de trading"""
        try:
            symbol = market_data['symbol']
            current_price = market_data['data']['price']
            current_volume = market_data['data']['volume']
            
            # Log des informations importantes
            self.logger.info(f"Traitement des données pour {symbol}: Prix={current_price}, Volume={current_volume}")
            
            # Accès aux données brutes si nécessaire
            raw_data = market_data.get('raw_data', {})
            
            # Logique de trading ici...
            
        except KeyError as e:
            self.logger.error(f"Erreur lors du traitement des données: {str(e)}")
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors du traitement: {str(e)}")

    def _analyze_and_trade(self, symbol, market_info):
        # TODO: Implémenter la logique d'analyse et de trading
        pass

    def start_trading(self):
        """Démarre la boucle de trading dans un thread séparé"""
        def run_trading():
            self.logger.info("Boucle de trading démarrée")
            self.trading_loop()
        
        self.trading_thread = threading.Thread(target=run_trading)
        self.trading_thread.daemon = True
        self.trading_thread.start()

    def start_data_updates(self):
        """Démarre la mise à jour des données dans un thread séparé"""
        def run_updates():
            last_update = 0
            update_interval = 60  # Mettre à jour toutes les 60 secondes
            
            while self.is_running:
                try:
                    current_time = time.time()
                    if current_time - last_update >= update_interval:
                        for symbol in self.symbols:
                            if not self.is_running:
                                break
                            # Utiliser le MarketUpdater pour mettre à jour les données
                            self.data_updater.update_market_data(symbol)
                        last_update = current_time
                    time.sleep(1)  # Vérifier toutes les secondes
                except Exception as e:
                    self.logger.error(f"Erreur lors de la mise à jour des données: {str(e)}")
                    time.sleep(1)

        self.data_update_thread = threading.Thread(target=run_updates)
        self.data_update_thread.daemon = True
        self.data_update_thread.start()

    def start(self):
        """Démarre le bot (monitoring + trading + mise à jour des données)"""
        self.logger.info("Démarrage du bot...")
        self.is_running = True

        # Démarrer le service de monitoring
        self.start_monitoring()

        # Démarrer la boucle de trading
        self.start_trading()

        # Démarrer la mise à jour des données dans un thread séparé
        self.start_data_updates()

    def stop(self):
        """Arrête tous les services du bot"""
        self.logger.info("Arrêt du bot...")
        self.is_running = False
        
        # Attendre que les threads se terminent avec timeout
        timeout = 5  # timeout de 5 secondes
        current_thread = threading.current_thread()
        
        # Forcer l'arrêt des services
        if hasattr(self, 'monitoring_service'):
            self.monitoring_service.stop()
        if hasattr(self, 'data_updater'):
            self.data_updater.stop()
        
        # Attendre que les threads se terminent
        threads = [
            (self.monitoring_thread, "monitoring"),
            (self.trading_thread, "trading"),
            (self.data_update_thread, "data update")
        ]
        
        for thread, name in threads:
            if thread and thread.is_alive() and current_thread != thread:
                self.logger.info(f"Attente de l'arrêt du thread {name}...")
                thread.join(timeout=timeout)
                if thread.is_alive():
                    self.logger.warning(f"Le thread {name} ne s'est pas arrêté dans le délai imparti")
            
        self.logger.info("Bot arrêté avec succès")

if __name__ == "__main__":
    # Créer et démarrer le bot
    bot = TradingBot(symbols=["BTCUSDT", "ETHUSDT"])
    try:
        bot.start()
        # Maintenir le programme en vie
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()
