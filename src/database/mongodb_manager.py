from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
import time

class MongoDBManager:
    def __init__(self):
        """Initialise la connexion à MongoDB"""
        load_dotenv()
        
        # Configuration du logging
        self.logger = logging.getLogger(__name__)
        
        # Get MongoDB credentials from environment variables
        mongodb_user = os.getenv('MONGO_ROOT_USER', 'admin')
        mongodb_password = os.getenv('MONGO_ROOT_PASSWORD', 'secure_password')
        mongodb_database = os.getenv('MONGODB_DATABASE', 'trading_db')
        
        # Collections names from environment variables
        market_data_collection = os.getenv('MONGODB_COLLECTION_MARKET_DATA', 'market_data')
        indicators_collection = os.getenv('MONGODB_COLLECTION_INDICATORS', 'indicators')
        trades_collection = os.getenv('MONGODB_COLLECTION_TRADES', 'trades')
        monitoring_collection = os.getenv('MONGODB_COLLECTION_MONITORING', 'monitoring')
        api_metrics_collection = os.getenv('MONGODB_COLLECTION_API_METRICS', 'api_metrics')
        
        # Construction de l'URI MongoDB avec les identifiants
        mongodb_uri = f"mongodb://{mongodb_user}:{mongodb_password}@localhost:27017/"
        
        # Connexion à MongoDB avec retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
                # Test de la connexion
                self.client.admin.command('ping')
                self.logger.info("Successfully connected to MongoDB")
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    self.logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {str(e)}")
                    raise
                self.logger.warning(f"Failed to connect to MongoDB (attempt {retry_count}): {str(e)}")
                time.sleep(1)  # Wait before retrying
        
        # Sélection de la base de données
        self.db: Database = self.client[mongodb_database]
        
        # Collections
        self.market_data: Collection = self.db[market_data_collection]
        self.indicators: Collection = self.db[indicators_collection]
        self.trades: Collection = self.db[trades_collection]
        self.backtest_results: Collection = self.db['backtest_results']
        self.strategy_config: Collection = self.db['strategy_config']
        self.monitoring: Collection = self.db[monitoring_collection]
        self.api_metrics: Collection = self.db[api_metrics_collection]
        
        # Création des index
        self._setup_indexes()
        
        self.logger.info("MongoDB Manager initialized")

    def _setup_indexes(self):
        """Configure les index pour optimiser les requêtes"""
        # Index pour market_data
        self.market_data.create_index([("symbol", ASCENDING), ("timestamp", DESCENDING)])
        self.market_data.create_index([("timestamp", DESCENDING)])
        
        # Index pour indicators
        self.indicators.create_index([("symbol", ASCENDING), ("timestamp", DESCENDING)])
        
        # Index pour trades
        self.trades.create_index([("timestamp", DESCENDING)])
        self.trades.create_index([("symbol", ASCENDING), ("timestamp", DESCENDING)])
        
        # Index pour backtest_results
        self.backtest_results.create_index([("strategy_name", ASCENDING), ("timestamp", DESCENDING)])
        
        # Index pour strategy_config
        self.strategy_config.create_index([("strategy_name", ASCENDING)])

        # Index pour monitoring
        self.monitoring.create_index([("timestamp", DESCENDING)])
        self.monitoring.create_index([("endpoint", ASCENDING), ("timestamp", DESCENDING)])
        
        # Index pour api_metrics
        self.api_metrics.create_index([("timestamp", DESCENDING)])
        self.api_metrics.create_index([("endpoint", ASCENDING), ("metric_type", ASCENDING), ("timestamp", DESCENDING)])

    def store_market_data(self, symbol: str, data: Dict[str, Any]):
        """
        Stocke les données de marché
        :param symbol: Symbole de la paire de trading
        :param data: Données à stocker
        """
        try:
            document = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "data": data
            }
            self.market_data.insert_one(document)
            self.logger.debug(f"Stored market data for {symbol}")
        except Exception as e:
            self.logger.error(f"Error storing market data: {str(e)}")
            raise

    def store_indicators(self, symbol: str, indicators: Dict[str, Any]):
        """
        Stocke les indicateurs techniques
        :param symbol: Symbole de la paire de trading
        :param indicators: Indicateurs à stocker
        """
        try:
            document = {
                "symbol": symbol,
                "timestamp": datetime.now(),
                "indicators": indicators
            }
            self.indicators.insert_one(document)
            self.logger.debug(f"Stored indicators for {symbol}")
        except Exception as e:
            self.logger.error(f"Error storing indicators: {str(e)}")
            raise

    def store_trade(self, trade_data: Dict[str, Any]):
        """
        Stocke les informations d'une transaction
        :param trade_data: Données de la transaction
        """
        try:
            trade_data["timestamp"] = datetime.now()
            self.trades.insert_one(trade_data)
            self.logger.info(f"Stored trade for {trade_data.get('symbol')}")
        except Exception as e:
            self.logger.error(f"Error storing trade: {str(e)}")
            raise

    def store_backtest_result(self, strategy_name: str, result: Dict[str, Any]):
        """
        Stocke le résultat d'un backtest
        :param strategy_name: Nom de la stratégie
        :param result: Résultat du backtest
        """
        try:
            document = {
                "strategy_name": strategy_name,
                "timestamp": datetime.now(),
                "result": result
            }
            self.backtest_results.insert_one(document)
            self.logger.info(f"Stored backtest result for {strategy_name}")
        except Exception as e:
            self.logger.error(f"Error storing backtest result: {str(e)}")
            raise

    def store_strategy_config(self, strategy_name: str, config: Dict[str, Any]):
        """
        Stocke la configuration d'une stratégie
        :param strategy_name: Nom de la stratégie
        :param config: Configuration de la stratégie
        """
        try:
            document = {
                "strategy_name": strategy_name,
                "config": config,
                "timestamp": datetime.now()
            }
            self.strategy_config.insert_one(document)
            self.logger.info(f"Stored strategy config for {strategy_name}")
        except Exception as e:
            self.logger.error(f"Error storing strategy config: {str(e)}")
            raise

    def store_market_data_bulk(self, data_list: List[Dict[str, Any]]):
        """
        Stocke plusieurs données de marché en une seule opération
        :param data_list: Liste des données à stocker
        """
        try:
            if not data_list:
                return
            
            # Validate and prepare documents
            documents = []
            for data in data_list:
                if not isinstance(data, dict) or 'symbol' not in data or 'data' not in data:
                    raise ValueError("Invalid market data format")
                
                document = {
                    "symbol": data['symbol'],
                    "timestamp": datetime.now(),
                    "data": data['data']
                }
                documents.append(document)
            
            # Insert documents
            self.market_data.insert_many(documents)
            self.logger.debug(f"Stored {len(documents)} market data records")
        except Exception as e:
            self.logger.error(f"Error storing market data bulk: {str(e)}")
            raise

    def store_indicators_bulk(self, data_list: List[Dict[str, Any]]):
        """
        Stocke plusieurs indicateurs en une seule opération
        :param data_list: Liste des indicateurs à stocker
        """
        try:
            if not data_list:
                return
            
            documents = []
            for data in data_list:
                if not isinstance(data, dict) or 'symbol' not in data or 'indicators' not in data:
                    raise ValueError("Invalid indicators format")
                
                document = {
                    "symbol": data['symbol'],
                    "timestamp": datetime.now(),
                    "indicators": data['indicators']
                }
                documents.append(document)
            
            self.indicators.insert_many(documents)
            self.logger.debug(f"Stored {len(documents)} indicator records")
        except Exception as e:
            self.logger.error(f"Error storing indicators bulk: {str(e)}")
            raise

    def store_monitoring_data(self, data: Dict[str, Any]):
        """
        Stocke les données de monitoring
        :param data: Données de monitoring à stocker
        """
        try:
            data["timestamp"] = datetime.now()
            self.monitoring.insert_one(data)
            self.logger.debug("Stored monitoring data")
        except Exception as e:
            self.logger.error(f"Error storing monitoring data: {str(e)}")
            raise

    def store_api_metric(self, metric_data: Dict[str, Any]):
        """
        Stocke une métrique d'API
        :param metric_data: Données de la métrique à stocker
        """
        try:
            metric_data["timestamp"] = datetime.now()
            self.api_metrics.insert_one(metric_data)
            self.logger.debug(f"Stored API metric for {metric_data.get('endpoint')}")
        except Exception as e:
            self.logger.error(f"Error storing API metric: {str(e)}")
            raise

    def get_latest_market_data(self, symbol: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Récupère les dernières données de marché pour un symbole
        :param symbol: Symbole de la paire de trading
        :param limit: Nombre de documents à récupérer
        :return: Liste des données de marché
        """
        try:
            cursor = self.market_data.find(
                {"symbol": symbol}
            ).sort("timestamp", DESCENDING).limit(limit)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving market data: {str(e)}")
            raise

    def get_latest_indicators(self, symbol: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Récupère les derniers indicateurs pour un symbole
        :param symbol: Symbole de la paire de trading
        :param limit: Nombre de documents à récupérer
        :return: Liste des indicateurs
        """
        try:
            cursor = self.indicators.find(
                {"symbol": symbol}
            ).sort("timestamp", DESCENDING).limit(limit)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving indicators: {str(e)}")
            raise

    def get_trades_by_timeframe(self, start_time: datetime, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Récupère les transactions dans une période donnée
        :param start_time: Début de la période
        :param end_time: Fin de la période (par défaut: maintenant)
        :return: Liste des transactions
        """
        try:
            if end_time is None:
                end_time = datetime.now()
            
            cursor = self.trades.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", ASCENDING)
            
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving trades: {str(e)}")
            raise

    def get_latest_backtest_results(self, strategy_name: str, limit: int = 1) -> List[Dict[str, Any]]:
        """
        Récupère les derniers résultats de backtest pour une stratégie
        :param strategy_name: Nom de la stratégie
        :param limit: Nombre de résultats à récupérer
        :return: Liste des résultats de backtest
        """
        try:
            cursor = self.backtest_results.find(
                {"strategy_name": strategy_name}
            ).sort("timestamp", DESCENDING).limit(limit)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving backtest results: {str(e)}")
            raise

    def get_strategy_config(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la configuration d'une stratégie
        :param strategy_name: Nom de la stratégie
        :return: Configuration de la stratégie ou None si non trouvée
        """
        try:
            return self.strategy_config.find_one({"strategy_name": strategy_name})
        except Exception as e:
            self.logger.error(f"Error retrieving strategy config: {str(e)}")
            raise

    def get_monitoring_data(self, start_time: datetime, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Récupère les données de monitoring pour une période donnée
        :param start_time: Début de la période
        :param end_time: Fin de la période (par défaut: maintenant)
        :return: Liste des données de monitoring
        """
        try:
            if end_time is None:
                end_time = datetime.now()
            
            cursor = self.monitoring.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", ASCENDING)
            
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving monitoring data: {str(e)}")
            raise

    def get_api_metrics(self, endpoint: str = None, metric_type: str = None, 
                       start_time: datetime = None, end_time: datetime = None) -> List[Dict[str, Any]]:
        """
        Récupère les métriques d'API avec filtres optionnels
        :param endpoint: Filtre par endpoint
        :param metric_type: Filtre par type de métrique
        :param start_time: Début de la période
        :param end_time: Fin de la période
        :return: Liste des métriques d'API
        """
        try:
            query = {}
            if endpoint:
                query["endpoint"] = endpoint
            if metric_type:
                query["metric_type"] = metric_type
            if start_time or end_time:
                query["timestamp"] = {}
                if start_time:
                    query["timestamp"]["$gte"] = start_time
                if end_time:
                    query["timestamp"]["$lte"] = end_time
            
            cursor = self.api_metrics.find(query).sort("timestamp", ASCENDING)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Error retrieving API metrics: {str(e)}")
            raise

    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Nettoie les anciennes données
        :param days_to_keep: Nombre de jours de données à conserver
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Nettoyer les différentes collections
            collections = [
                self.market_data,
                self.indicators,
                self.monitoring,
                self.api_metrics
            ]
            
            for collection in collections:
                result = collection.delete_many({"timestamp": {"$lt": cutoff_date}})
                self.logger.info(f"Deleted {result.deleted_count} old records from {collection.name}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {str(e)}")
            raise

    def close(self):
        """Ferme la connexion à MongoDB"""
        try:
            self.client.close()
            self.logger.info("MongoDB connection closed")
        except Exception as e:
            self.logger.error(f"Error closing MongoDB connection: {str(e)}")
            raise
