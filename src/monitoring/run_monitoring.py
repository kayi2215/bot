import threading
from src.monitoring.api_monitor import APIMonitor
import time
import logging
import signal
import sys
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

class MonitoringService:
    def __init__(self, check_interval=60, testnet=False):
        """
        Initialise le service de monitoring
        :param check_interval: Intervalle entre les vérifications en secondes (défaut: 60s)
        :param testnet: Utiliser le testnet Binance (défaut: False)
        """
        load_dotenv()
        self.monitor = APIMonitor(testnet=testnet)
        self.check_interval = check_interval
        self.stop_event = threading.Event()
        self.running = False
        self.last_metrics_summary = datetime.now()
        self.metrics_summary_interval = 300  # 5 minutes
        self.shutdown_complete = threading.Event()  # Nouvel événement pour la synchronisation
        
        # Configuration des endpoints Binance à surveiller
        self.endpoints = [
            {
                "endpoint": "/api/v3/ticker/24hr",
                "method": "get_ticker",
                "params": {"symbol": "BTCUSDT"}
            },
            {
                "endpoint": "/api/v3/depth",
                "method": "get_order_book",
                "params": {"symbol": "BTCUSDT", "limit": 50}
            },
            {
                "endpoint": "/api/v3/klines",
                "method": "get_klines",
                "params": {"symbol": "BTCUSDT", "interval": "1", "limit": 100}  # Harmonisé avec Bybit
            }
        ]
        
        self.last_check = {}
        for endpoint in self.endpoints:
            self.last_check[endpoint["endpoint"]] = datetime.now() - timedelta(seconds=check_interval)
        
        self.logger = logging.getLogger('binance_monitoring_service')
        self._setup_logging()

    def _setup_logging(self):
        """Configure le système de logging"""
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Handler pour la console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
        # Handler pour le fichier
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(log_dir, 'binance_monitoring_service.log'))
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def signal_handler(self, signum, frame):
        """Gestionnaire pour l'arrêt propre du service"""
        self.logger.info("\nArrêt du service de monitoring Binance...")
        self.stop()

    def should_check_endpoint(self, endpoint: str) -> bool:
        """Vérifie si un endpoint doit être testé en fonction de son dernier check"""
        now = datetime.now()
        if (now - self.last_check[endpoint]).total_seconds() >= self.check_interval:
            self.last_check[endpoint] = now
            return True
        return False

    def should_print_metrics_summary(self) -> bool:
        """Vérifie si on doit afficher le résumé des métriques"""
        now = datetime.now()
        if (now - self.last_metrics_summary).total_seconds() >= self.metrics_summary_interval:
            self.last_metrics_summary = now
            return True
        return False

    def check_alerts(self):
        """Vérifie et affiche les alertes actives"""
        alerts = self.monitor.get_alerts()
        if alerts:
            self.logger.warning("=== Alertes Actives ===")
            for alert in alerts:
                self.logger.warning(f"Type: {alert['type']}, Valeur: {alert['value']}")

    def print_metrics_summary(self):
        """Affiche un résumé des métriques"""
        metrics = self.monitor.get_metrics_summary()
        self.logger.info("\n=== Résumé des Métriques ===")
        for endpoint, data in metrics.items():
            self.logger.info(f"\nEndpoint: {endpoint}")
            self.logger.info(f"Latence moyenne: {data['avg_latency']:.2f}ms")
            self.logger.info(f"Taux de succès: {data['success_rate']:.1f}%")
            self.logger.info(f"Nombre d'erreurs: {data['error_count']}")

    def run(self):
        """Lance la boucle principale du service de monitoring"""
        try:
            self.logger.info("Démarrage du service de monitoring Binance...")
            self.running = True
            
            while not self.stop_event.is_set():
                try:
                    # Vérification des endpoints
                    for endpoint_config in self.endpoints:
                        if self.stop_event.is_set():
                            break
                            
                        endpoint = endpoint_config["endpoint"]
                        if self.should_check_endpoint(endpoint):
                            self.logger.info(f"Vérification de l'endpoint: {endpoint}")
                            start_time = time.time()
                            
                            try:
                                method = getattr(self.monitor, endpoint_config["method"])
                                method(**endpoint_config["params"])
                                
                                latency = (time.time() - start_time) * 1000
                                self.logger.info(f"Latence pour {endpoint}: {latency:.2f}ms")
                                
                            except Exception as e:
                                self.logger.error(f"Erreur lors de la vérification de {endpoint}: {str(e)}")
                    
                    # Vérification et affichage des alertes
                    self.check_alerts()
                    
                    # Affichage périodique du résumé des métriques
                    if self.should_print_metrics_summary():
                        self.print_metrics_summary()
                    
                    time.sleep(1)  # Pause courte pour éviter une utilisation excessive du CPU
                    
                except Exception as e:
                    self.logger.error(f"Erreur dans la boucle principale: {str(e)}")
                    time.sleep(5)  # Pause plus longue en cas d'erreur
                    
        except KeyboardInterrupt:
            self.logger.info("Interruption détectée, arrêt du service...")
        finally:
            self.running = False
            self.shutdown_complete.set()

    def stop(self):
        """Arrête proprement le service de monitoring"""
        self.logger.info("Arrêt du service de monitoring...")
        self.stop_event.set()
        
        # Attente de l'arrêt complet avec timeout
        if not self.shutdown_complete.wait(timeout=5):
            self.logger.warning("Le service ne s'est pas arrêté dans le délai imparti")
        else:
            self.logger.info("Service arrêté avec succès")


def main():
    """Point d'entrée principal du service de monitoring"""
    # Configuration du logging au niveau racine
    logging.basicConfig(level=logging.INFO)
    
    # Création et démarrage du service
    service = MonitoringService()
    
    # Configuration du gestionnaire de signal
    signal.signal(signal.SIGINT, service.signal_handler)
    signal.signal(signal.SIGTERM, service.signal_handler)
    
    # Démarrage du service
    service.run()


if __name__ == "__main__":
    main()
