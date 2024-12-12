import pandas as pd
import numpy as np
from typing import Dict, Any

class TechnicalAnalysis:
    def __init__(self):
        self.indicators = {}

    def calculate_rsi(self, data: pd.Series, periods: int = 14) -> pd.Series:
        """Calcule le RSI (Relative Strength Index)"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_sma(self, data: pd.Series, periods: int) -> pd.Series:
        """Calcule la moyenne mobile simple"""
        return data.rolling(window=periods).mean()

    def calculate_ema(self, data: pd.Series, periods: int) -> pd.Series:
        """Calcule la moyenne mobile exponentielle"""
        return data.ewm(span=periods, adjust=False).mean()

    def calculate_macd(self, data: pd.Series) -> tuple:
        """Calcule le MACD (Moving Average Convergence Divergence)"""
        exp1 = data.ewm(span=12, adjust=False).mean()
        exp2 = data.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def calculate_bollinger_bands(self, data: pd.Series, periods: int = 20) -> tuple:
        """Calcule les bandes de Bollinger"""
        sma = self.calculate_sma(data, periods)
        std = data.rolling(window=periods).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        return upper_band, sma, lower_band

    def calculate_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule tous les indicateurs techniques principaux
        :param df: DataFrame avec les colonnes OHLCV
        :return: Dictionnaire contenant tous les indicateurs calculés
        """
        # Convertir uniquement les colonnes numériques en float
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # RSI
        rsi_series = self.calculate_rsi(df['close'])
        self.indicators['RSI'] = float(rsi_series.iloc[-1])

        # MACD
        macd, signal = self.calculate_macd(df['close'])
        self.indicators['MACD'] = float(macd.iloc[-1])
        self.indicators['MACD_Signal'] = float(signal.iloc[-1])
        self.indicators['MACD_Hist'] = float(macd.iloc[-1] - signal.iloc[-1])

        # Bandes de Bollinger
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df['close'])
        self.indicators['BB_upper'] = float(bb_upper.iloc[-1])
        self.indicators['BB_middle'] = float(bb_middle.iloc[-1])
        self.indicators['BB_lower'] = float(bb_lower.iloc[-1])

        # Moyennes Mobiles
        self.indicators['SMA_20'] = float(self.calculate_sma(df['close'], 20).iloc[-1])
        self.indicators['EMA_20'] = float(self.calculate_ema(df['close'], 20).iloc[-1])

        return self.indicators

    def get_signals(self, df: pd.DataFrame) -> Dict[str, bool]:
        """
        Génère des signaux de trading basés sur les indicateurs
        :param df: DataFrame avec les données OHLCV
        :return: Dictionnaire contenant les signaux de trading
        """
        indicators = self.calculate_all(df)
        signals = {}
        
        # Signal RSI
        signals['RSI_OVERSOLD'] = indicators['RSI'] < 30
        signals['RSI_OVERBOUGHT'] = indicators['RSI'] > 70

        # Signal MACD
        signals['MACD_BULLISH'] = indicators['MACD'] > indicators['MACD_Signal']
        signals['MACD_BEARISH'] = indicators['MACD'] < indicators['MACD_Signal']

        # Signal Bollinger
        last_close = float(df['close'].iloc[-1])
        signals['BB_UPPER_CROSS'] = last_close > indicators['BB_upper']
        signals['BB_LOWER_CROSS'] = last_close < indicators['BB_lower']

        return signals

    def get_summary(self, df: pd.DataFrame) -> str:
        """
        Génère un résumé de l'analyse technique
        :param df: DataFrame avec les données OHLCV
        :return: Résumé textuel de l'analyse
        """
        signals = self.get_signals(df)
        
        summary = []
        summary.append("=== Résumé de l'analyse technique ===")
        summary.append(f"Prix actuel: {df['close'].iloc[-1]:.2f}")
        
        # Analyse RSI
        if signals['RSI_OVERSOLD']:
            summary.append("RSI: Survente")
        elif signals['RSI_OVERBOUGHT']:
            summary.append("RSI: Surachat")
        else:
            summary.append("RSI: Neutre")
        
        # Analyse MACD
        if signals['MACD_BULLISH']:
            summary.append("MACD: Signal d'achat")
        elif signals['MACD_BEARISH']:
            summary.append("MACD: Signal de vente")
        else:
            summary.append("MACD: Neutre")
        
        # Analyse Bandes de Bollinger
        if signals['BB_UPPER_CROSS']:
            summary.append("Bandes de Bollinger: Surachat")
        elif signals['BB_LOWER_CROSS']:
            summary.append("Bandes de Bollinger: Survente")
        else:
            summary.append("Bandes de Bollinger: Neutre")
        
        return "\n".join(summary)
