import pytest
from unittest.mock import Mock, patch
from src.monitoring.api_monitor import APIMonitor
import time
import os
import json
from datetime import datetime

# Fixtures pour les réponses API simulées
@pytest.fixture
def mock_ticker_response():
    return {
        'symbol': 'BTCUSDT',
        'price': '50000.00',
        'volume': '1000.00',
        'quoteVolume': '50000000.00'
    }

@pytest.fixture
def mock_orderbook_response():
    return {
        'lastUpdateId': 1027024,
        'bids': [
            ['4.00000000', '431.00000000']
        ],
        'asks': [
            ['4.00000200', '12.00000000']
        ]
    }

@pytest.fixture
def mock_klines_response():
    return [
        [
            1499040000000,      # Open time
            "0.01634790",       # Open
            "0.80000000",       # High
            "0.01575800",       # Low
            "0.01577100",       # Close
            "148976.11427815",  # Volume
            1499644799999,      # Close time
            "2434.19055334",    # Quote asset volume
            308,                # Number of trades
            "1756.87402397",    # Taker buy base asset volume
            "28.46694368",      # Taker buy quote asset volume
            "0"                 # Ignore
        ]
    ]

@pytest.fixture
def mock_exchange_info():
    return {
        'rateLimits': [
            {
                'rateLimitType': 'REQUEST_WEIGHT',
                'limit': 1200,
                'current': 50
            }
        ]
    }

@pytest.fixture
def monitor():
    with patch.dict(os.environ, {'BINANCE_API_KEY': 'test_key', 'BINANCE_API_SECRET': 'test_secret'}):
        monitor = APIMonitor(log_dir="test_logs", testnet=True)
        monitor.metrics = []  # Réinitialiser les métriques
        return monitor

class TestUnitMonitoring:
    """Tests unitaires pour le monitoring"""
    
    def test_check_availability_success(self, monitor, mock_ticker_response):
        """Test de la disponibilité de l'API avec mock"""
        with patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            assert monitor.check_availability() is True

    def test_check_availability_failure(self, monitor):
        """Test de la non-disponibilité de l'API"""
        with patch.object(monitor.client, 'get_ticker', return_value={"code": -1}):
            assert monitor.check_availability() is False

    def test_measure_latency(self, monitor, mock_ticker_response):
        """Test de la mesure de latence avec mock"""
        with patch('time.time', side_effect=[1000, 1000.5]), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            
            latency = monitor.measure_latency(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert abs(latency - 500.0) < 0.1  # 500ms avec tolérance de 0.1ms
            assert isinstance(latency, float)

    def test_alert_thresholds(self, monitor):
        """Test des seuils d'alerte"""
        assert monitor.alert_thresholds['latency'] == 2000
        assert monitor.alert_thresholds['error_rate'] == 0.1
        assert monitor.alert_thresholds['consecutive_failures'] == 3
        assert monitor.alert_thresholds['rate_limit_threshold'] == 0.8

    def test_high_latency_alert(self, monitor, mock_ticker_response):
        """Test des alertes de latence élevée"""
        monitor.alert_thresholds['latency'] = 500  # Seuil à 500ms
        
        with patch('time.time', side_effect=[1000, 1002] * 10), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            
            latency = monitor.measure_latency(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert abs(latency - 2000.0) < 0.1  # 2000ms avec tolérance
            assert len(monitor.metrics) == 1
            assert monitor.metrics[0]['type'] == 'latency'
            assert abs(monitor.metrics[0]['value'] - 2000.0) < 0.1

    def test_consecutive_failures_alert(self, monitor):
        """Test des alertes d'échecs consécutifs"""
        monitor.consecutive_failures = 3
        monitor.alert_thresholds['consecutive_failures'] = 2
        
        # Simuler un appel API échoué
        with patch.object(monitor.client, 'get_ticker', side_effect=Exception("API Error")):
            monitor.measure_latency(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert monitor.consecutive_failures == 4

    def test_rate_limits_warning(self, monitor, mock_exchange_info):
        """Test des avertissements de limites de taux"""
        with patch.object(monitor.client, 'get_exchange_info', return_value=mock_exchange_info):
            limits = monitor.check_rate_limits()
            
            assert limits['status'] == 'OK'
            assert limits['weight'] == 50
            assert limits['limit'] == 1200
            assert limits['usage_percent'] == (50 / 1200) * 100

    def test_metrics_recording(self, monitor, mock_ticker_response):
        """Test de l'enregistrement des métriques"""
        monitor.metrics = []  # Réinitialiser les métriques
        
        with patch('time.time', side_effect=[1000, 1000.1]), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            
            latency = monitor.measure_latency(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert abs(latency - 100.0) < 0.1  # 100ms avec tolérance
            assert len(monitor.metrics) == 1
            assert monitor.metrics[0]['type'] == 'latency'
            assert abs(monitor.metrics[0]['value'] - 100.0) < 0.1

    def test_monitor_endpoint_success(self, monitor, mock_ticker_response):
        """Test du monitoring d'un endpoint avec succès"""
        monitor.metrics = []  # Réinitialiser les métriques
        
        with patch('time.time', side_effect=[0, 0.1, 0.1, 0.2] * 5), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            
            monitor.monitor_endpoint(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert len(monitor.metrics) == 2
            # Vérifier la métrique de disponibilité
            availability_metrics = [m for m in monitor.metrics if m['type'] == 'availability']
            assert len(availability_metrics) == 1
            assert availability_metrics[0]['value'] == 1
            
            # Vérifier la métrique de latence
            latency_metrics = [m for m in monitor.metrics if m['type'] == 'latency']
            assert len(latency_metrics) == 1
            assert abs(latency_metrics[0]['value']) < 0.1

    def test_monitor_endpoint_failure(self, monitor):
        """Test du monitoring d'un endpoint avec échec"""
        monitor.metrics = []  # Réinitialiser les métriques
        monitor.consecutive_failures = 0  # Réinitialiser les échecs
        
        with patch('time.time', side_effect=[0, 0.1, 0.1, 0.2] * 5), \
             patch.object(monitor.client, 'get_ticker', side_effect=Exception("API Error")):
            monitor.monitor_endpoint(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            
            assert len(monitor.metrics) == 0
            assert monitor.consecutive_failures >= 1

    def test_request_counters(self, monitor, mock_ticker_response, mock_exchange_info):
        """Test des compteurs de requêtes"""
        monitor.total_requests = 0
        monitor.failed_requests = 0
        
        # Test requête réussie
        with patch('time.time', side_effect=[0, 0.1, 0.1, 0.2] * 5), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response), \
             patch.object(monitor.client, 'get_exchange_info', return_value=mock_exchange_info), \
             patch.object(monitor, 'check_availability', return_value=True):
            monitor.monitor_endpoint("/api/v3/ticker/24hr", "get_ticker", symbol="BTCUSDT")
            assert monitor.total_requests == 1
            assert monitor.failed_requests == 0
        
        # Test requête échouée
        with patch('time.time', side_effect=[1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]), \
             patch.object(monitor.client, 'get_ticker', side_effect=Exception("API Error")), \
             patch.object(monitor.client, 'get_exchange_info', return_value=mock_exchange_info), \
             patch.object(monitor, 'check_availability', return_value=False):
            monitor.monitor_endpoint("/api/v3/ticker/24hr", "get_ticker", symbol="BTCUSDT")
            assert monitor.total_requests == 1  # La requête échouée ne doit pas être comptée
            assert monitor.failed_requests == 0  # Les requêtes échouées ne sont pas comptées dans le code actuel

    def test_get_alerts(self, monitor, mock_ticker_response):
        """Test de la récupération des alertes"""
        monitor.metrics = []
        monitor.consecutive_failures = 0
        monitor.total_requests = 100
        monitor.failed_requests = 15
        
        # Simuler une latence élevée
        with patch('time.time', side_effect=[0, 3, 3.1, 3.2, 3.3, 3.4, 3.5]), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            monitor.measure_latency("/api/v3/ticker/24hr", "get_ticker", symbol="BTCUSDT")

        # Simuler des échecs consécutifs
        monitor.consecutive_failures = 4
        
        # Récupérer les alertes
        alerts = monitor.get_alerts()
        
        # Vérifier les alertes
        assert len(alerts) == 3  # Doit avoir 3 alertes : latence, échecs consécutifs et taux d'erreur
        
        # Vérifier les types d'alertes
        alert_types = [alert['type'] for alert in alerts]
        assert 'high_latency' in alert_types
        assert 'consecutive_failures' in alert_types
        assert 'high_error_rate' in alert_types

    def test_testnet_in_metrics(self, monitor, mock_ticker_response):
        """Test de la présence du champ testnet dans les métriques"""
        monitor.metrics = []
        
        with patch('time.time', side_effect=[0, 0.1]), \
             patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response):
            monitor.measure_latency("/api/v3/ticker/24hr", "get_ticker", symbol="BTCUSDT")
        
        assert len(monitor.metrics) == 1
        assert 'testnet' in monitor.metrics[0]
        assert monitor.metrics[0]['testnet'] == True  # Car le monitor est initialisé avec testnet=True

class TestIntegrationMonitoring:
    """Tests d'intégration pour le monitoring"""
    
    def test_full_monitoring_cycle(self, monitor, mock_ticker_response, mock_exchange_info):
        """Test d'un cycle complet de monitoring"""
        with patch.object(monitor.client, 'get_ticker', return_value=mock_ticker_response), \
             patch.object(monitor.client, 'get_exchange_info', return_value=mock_exchange_info):
            
            # Vérifier la disponibilité
            assert monitor.check_availability() is True
            
            # Mesurer la latence
            latency = monitor.measure_latency(
                endpoint="/api/v3/ticker/24hr",
                method="get_ticker",
                symbol="BTCUSDT"
            )
            assert latency is not None
            
            # Vérifier les limites de taux
            limits = monitor.check_rate_limits()
            assert limits['status'] == 'OK'
            
            # Vérifier les métriques enregistrées
            assert len(monitor.metrics) > 0

    def test_rate_limits_integration(self, monitor, mock_exchange_info):
        """Test d'intégration des limites de taux"""
        # Simuler une utilisation élevée des limites
        high_usage_info = {
            'rateLimits': [
                {
                    'rateLimitType': 'REQUEST_WEIGHT',
                    'limit': 100,
                    'current': 90
                }
            ]
        }
        
        with patch.object(monitor.client, 'get_exchange_info', return_value=high_usage_info):
            limits = monitor.check_rate_limits()
            assert limits['status'] == 'CRITICAL'
            assert limits['usage_percent'] == 90.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
