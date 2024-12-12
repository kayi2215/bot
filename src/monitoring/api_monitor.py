import time
import logging
import requests
from datetime import datetime
from typing import Dict, Optional, List
import json
import os
from pathlib import Path
from binance.client import Client
from dotenv import load_dotenv

class APIMonitor:
    def __init__(self, log_dir: str = "logs", testnet: bool = False):
        # Créer le répertoire de logs s'il n'existe pas
        self.log_dir = os.path.abspath(log_dir)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        self._setup_logging()
        self.metrics: List[Dict] = []
        self.alert_thresholds = {
            'latency': 2000,  # ms - aligné avec Bybit
            'error_rate': 0.1,  # 10%
            'consecutive_failures': 3,
            'rate_limit_threshold': 0.8  # 80% de la limite d'utilisation
        }
        self.consecutive_failures = 0
        self.testnet = testnet
        self.exchange = "binance"
        
        # Initialiser les compteurs de requêtes
        self.total_requests = 0
        self.failed_requests = 0
        
        # Charger les clés API depuis les variables d'environnement
        load_dotenv()
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        
        # Initialiser le client Binance
        if self.api_key and self.api_secret:
            self.client = Client(
                self.api_key,
                self.api_secret,
                testnet=testnet
            )
        else:
            self.logger.warning("API credentials not found. Running in public API mode only.")
            self.client = None

    def _setup_logging(self):
        """Configure le système de logging"""
        self.logger = logging.getLogger('binance_api_monitor')
        self.logger.setLevel(logging.INFO)
        
        # Handler pour le fichier
        fh = logging.FileHandler(f"{self.log_dir}/binance_api_monitor.log")
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

    def is_valid_response(self, response: Dict) -> bool:
        """Vérifie si la réponse de l'API est valide"""
        if not isinstance(response, dict):
            return False
        return not response.get('code')

    def measure_latency(self, endpoint: str, method: str = "GET", **kwargs) -> Optional[float]:
        """Mesure la latence d'un appel API Binance"""
        try:
            start_time = time.time()
            
            if not self.client:
                base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"
                response = requests.get(f"{base_url}{endpoint}")
            else:
                method_map = {
                    "get_ticker": self.client.get_ticker,
                    "get_orderbook": self.client.get_order_book,
                    "get_klines": self.client.get_klines
                }
                
                if method not in method_map:
                    raise ValueError(f"Unsupported method: {method}")
                
                response = method_map[method](**kwargs)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convertir en millisecondes
            
            if self.is_valid_response(response):
                self.record_metric('latency', latency, endpoint)
                self.consecutive_failures = 0
                return latency
            else:
                self.consecutive_failures += 1
                self.record_metric('error', 1, endpoint)
                self.logger.warning(f"API call failed: {response}")
                return None
                
        except Exception as e:
            self.consecutive_failures += 1
            self.record_metric('error', 1, endpoint)
            self.logger.error(f"Error measuring latency: {str(e)}")
            return None

    def check_availability(self, endpoint: str = "/api/v3/ticker/24hr") -> bool:
        """Vérifie si l'API Binance est disponible"""
        try:
            if not self.client:
                base_url = "https://testnet.binance.vision" if self.testnet else "https://api.binance.com"
                response = requests.get(f"{base_url}{endpoint}", params={"symbol": "BTCUSDT"})
                success = response.status_code == 200 and self.is_valid_response(response.json())
            else:
                response = self.client.get_ticker(symbol="BTCUSDT")
                success = self.is_valid_response(response)
            
            if success:
                self.consecutive_failures = 0
                self.record_metric('availability', 1, endpoint)
                return True
            else:
                self.consecutive_failures += 1
                self.record_metric('availability', 0, endpoint)
                return False
                
        except Exception as e:
            self.consecutive_failures += 1
            self.record_metric('availability', 0, endpoint)
            self.logger.error(f"Error checking availability: {str(e)}")
            return False

    def check_rate_limits(self) -> Dict:
        """Vérifie les limites de taux d'utilisation de l'API"""
        if not self.client:
            return {}
        
        try:
            exchange_info = self.client.get_exchange_info()
            rate_limits = exchange_info.get('rateLimits', [])
            
            max_usage_percent = 0
            current_weight = 0
            max_weight = 0
            
            for limit in rate_limits:
                if limit['rateLimitType'] == 'REQUEST_WEIGHT':
                    current = limit.get('current', 0)
                    max_limit = limit['limit']
                    usage_percent = (current / max_limit) * 100 if max_limit > 0 else 0
                    
                    if usage_percent > max_usage_percent:
                        max_usage_percent = usage_percent
                        current_weight = current
                        max_weight = max_limit
            
            result = {
                'weight': current_weight,
                'limit': max_weight,
                'usage_percent': max_usage_percent,
                'status': 'CRITICAL' if max_usage_percent > self.alert_thresholds['rate_limit_threshold'] * 100 else 'OK'
            }
            
            self.record_metric('rate_limit', max_usage_percent, 'rate_limits')
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking rate limits: {str(e)}")
            return {}

    def record_metric(self, metric_type: str, value: float, endpoint: str):
        """Enregistre une métrique"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'type': metric_type,
            'value': value,
            'endpoint': endpoint,
            'testnet': self.testnet,
            'exchange': self.exchange
        }
        self.metrics.append(metric)
        self._save_metrics()
        self._check_alerts(metric)

    def _save_metrics(self):
        """Sauvegarde les métriques dans un fichier JSON"""
        metrics_file = os.path.join(self.log_dir, 'metrics.json')
        try:
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics, f)
        except Exception as e:
            self.logger.error(f"Error saving metrics: {str(e)}")

    def _check_alerts(self, metric: Dict):
        """Vérifie si une métrique déclenche une alerte"""
        if metric['type'] == 'latency' and metric['value'] > self.alert_thresholds['latency']:
            self.logger.warning(f"High latency detected: {metric['value']}ms for {metric['endpoint']}")
        
        elif metric['type'] == 'error':
            error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0
            if error_rate > self.alert_thresholds['error_rate']:
                self.logger.warning(f"High error rate detected: {error_rate:.2%}")
        
        if self.consecutive_failures >= self.alert_thresholds['consecutive_failures']:
            self.logger.error(f"Multiple consecutive failures detected: {self.consecutive_failures}")

    def get_alerts(self) -> List[Dict]:
        """Récupère les alertes actives"""
        alerts = []
        
        # Vérifier la latency moyenne
        latency_metrics = [m['value'] for m in self.metrics if m['type'] == 'latency']
        if latency_metrics:
            avg_latency = sum(latency_metrics) / len(latency_metrics)
            if avg_latency > self.alert_thresholds['latency']:
                alerts.append({
                    'type': 'latency',
                    'message': f"High average latency: {avg_latency:.2f}ms",
                    'threshold': self.alert_thresholds['latency'],
                    'value': avg_latency,
                    'timestamp': datetime.now().isoformat()
                })

        # Vérifier le taux d'erreur
        error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0
        if error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'error_rate',
                'message': f"High error rate: {error_rate:.2%}",
                'threshold': self.alert_thresholds['error_rate'],
                'value': error_rate,
                'timestamp': datetime.now().isoformat()
            })

        # Vérifier les échecs consécutifs
        if self.consecutive_failures >= self.alert_thresholds['consecutive_failures']:
            alerts.append({
                'type': 'consecutive_failures',
                'message': f"Multiple consecutive failures: {self.consecutive_failures}",
                'threshold': self.alert_thresholds['consecutive_failures'],
                'value': self.consecutive_failures,
                'timestamp': datetime.now().isoformat()
            })

        return alerts

    def get_metrics_summary(self) -> Dict:
        """Génère un résumé des métriques"""
        summary = {
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'error_rate': self.failed_requests / self.total_requests if self.total_requests > 0 else 0,
            'consecutive_failures': self.consecutive_failures,
            'alerts': self.get_alerts(),
            'last_update': datetime.now().isoformat()
        }
        
        # Calculer les statistiques de latence
        latency_metrics = [m['value'] for m in self.metrics if m['type'] == 'latency']
        if latency_metrics:
            summary.update({
                'avg_latency': sum(latency_metrics) / len(latency_metrics),
                'min_latency': min(latency_metrics),
                'max_latency': max(latency_metrics)
            })
        
        return summary

    def check_api_health(self, api_endpoint: str) -> bool:
        """
        Vérifie la santé de l'API en contrôlant sa disponibilité et sa latence
        :param api_endpoint: URL de l'endpoint à vérifier
        :return: True si l'API est en bonne santé, False sinon
        """
        try:
            # Vérifier la disponibilité
            if not self.check_availability(api_endpoint):
                self.logger.warning(f"API {api_endpoint} is not available")
                return False
            
            # Mesurer la latence
            latency = self.measure_latency(api_endpoint)
            if latency is None or latency > self.alert_thresholds['latency']:
                self.logger.warning(f"API {api_endpoint} latency is too high or failed: {latency}ms")
                return False
            
            # Vérifier les échecs consécutifs
            if self.consecutive_failures >= self.alert_thresholds['consecutive_failures']:
                self.logger.warning(f"API {api_endpoint} has too many consecutive failures")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking API health: {str(e)}")
            return False

    def monitor_endpoint(self, endpoint: str, method: str = "GET", **kwargs):
        """Surveille un endpoint API Binance"""
        self.logger.info(f"Monitoring Binance endpoint: {endpoint} ({method})")
        
        # Vérifier la disponibilité
        available = self.check_availability(endpoint)
        if not available:
            self.logger.error(f"Binance API endpoint {endpoint} is not available")
            return
        
        # Mettre à jour les compteurs
        self.total_requests += 1
        
        # Mesurer la latence
        latency = self.measure_latency(endpoint, method, **kwargs)
        
        if latency is None:
            self.failed_requests += 1
        else:
            self.logger.info(f"Latency for {endpoint}: {latency}ms")
        
        # Vérifier les limites de taux
        rate_limits = self.check_rate_limits()
        if rate_limits:
            self.logger.info(f"Rate limits status: {json.dumps(rate_limits, indent=2)}")
        
        # Obtenir et logger le résumé des métriques
        summary = self.get_metrics_summary()
        if summary:
            self.logger.info(f"Metrics summary: {json.dumps(summary, indent=2)}")
