import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
from datetime import datetime
import time
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from .technical_indicators import TechnicalAnalysis

class MarketDataCollector:
    def __init__(self, api_key: str, api_secret: str):
        load_dotenv()
        use_testnet = os.getenv('USE_TESTNET', 'False').lower() == 'true'
        
        self.client = Client(api_key, api_secret, testnet=use_testnet)
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        if use_testnet:
            self.logger.info("Using Binance Testnet")
            
        self.technical_analyzer = TechnicalAnalysis()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def get_current_price(self, symbol: str) -> Dict[str, float]:
        try:
            # Récupérer le ticker et les statistiques 24h
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            stats = self.client.get_ticker(symbol=symbol)
            
            self.logger.info(f"Retrieved price for {symbol}: {ticker['price']}")
            return {
                'symbol': symbol,
                'last_price': float(ticker['price']),
                'volume_24h': float(stats['volume']),
                'timestamp': datetime.now().timestamp()
            }
        except BinanceAPIException as e:
            self.logger.error(f"Error fetching price for {symbol}: {str(e)}")
            raise

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close',
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except BinanceAPIException as e:
            self.logger.error(f"Error fetching klines for {symbol}: {str(e)}")
            raise

    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)
            return depth
        except BinanceAPIException as e:
            self.logger.error(f"Error fetching order book for {symbol}: {str(e)}")
            raise

    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Récupère les transactions récentes pour un symbole
        :param symbol: Symbole de la paire de trading (ex: 'BTCUSDT')
        :param limit: Nombre de transactions à récupérer
        :return: Liste des transactions récentes
        """
        try:
            trades = self.client.get_recent_trades(symbol=symbol, limit=limit)
            self.logger.info(f"Retrieved {len(trades)} recent trades for {symbol}")
            return trades
        except BinanceAPIException as e:
            self.logger.error(f"Error fetching recent trades for {symbol}: {str(e)}")
            raise

    def get_technical_analysis(self, symbol: str, interval: str = '1h', limit: int = 100) -> Dict[str, Any]:
        """
        Récupère les données et effectue une analyse technique complète
        :param symbol: Symbole de la paire de trading (ex: 'BTCUSDT')
        :param interval: Intervalle de temps pour les bougies (ex: '1h', '4h', '1d')
        :param limit: Nombre de bougies à récupérer
        :return: Dictionnaire contenant les indicateurs et signaux
        """
        try:
            # Récupérer les données historiques
            df = self.get_klines(symbol, interval, limit)
            
            # Obtenir l'analyse complète
            analysis = self.technical_analyzer.get_summary(df)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error performing technical analysis for {symbol}: {str(e)}")
            raise

    def get_market_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        Fournit une analyse complète du marché incluant prix actuel, analyse technique et carnet d'ordres
        :param symbol: Symbole de la paire de trading (ex: 'BTCUSDT')
        :return: Dictionnaire contenant toutes les informations d'analyse
        """
        try:
            current_price = self.get_current_price(symbol)
            technical_analysis = self.get_technical_analysis(symbol)
            order_book = self.get_order_book(symbol)
            
            analysis = {
                'current_price': current_price,
                'technical_analysis': technical_analysis,
                'order_book': order_book,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error performing market analysis for {symbol}: {str(e)}")
            raise
