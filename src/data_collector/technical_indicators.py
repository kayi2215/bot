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
        self.indicators['RSI'] = self.calculate_rsi(df['close'])

        # MACD
        macd, signal = self.calculate_macd(df['close'])
        self.indicators['MACD'] = macd
        self.indicators['MACD_Signal'] = signal
        self.indicators['MACD_Hist'] = macd - signal

        # Bandes de Bollinger
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df['close'])
        self.indicators['BB_Upper'] = bb_upper
        self.indicators['BB_Middle'] = bb_middle
        self.indicators['BB_Lower'] = bb_lower

        # Moyennes Mobiles
        self.indicators['SMA_20'] = self.calculate_sma(df['close'], 20)
        self.indicators['EMA_20'] = self.calculate_ema(df['close'], 20)

        return self.indicators

    def get_signals(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Génère des signaux de trading basés sur les indicateurs
        :param df: DataFrame avec les données OHLCV
        :return: Dictionnaire contenant les signaux de trading
        """
        indicators = self.calculate_all(df)
        signals = {}
        
        # Signal RSI
        last_rsi = indicators['RSI'].iloc[-1]
        signals['RSI'] = 'Survente' if last_rsi < 30 else 'Surachat' if last_rsi > 70 else 'Neutre'

        # Signal MACD
        last_macd = indicators['MACD'].iloc[-1]
        last_signal = indicators['MACD_Signal'].iloc[-1]
        signals['MACD'] = 'Achat' if last_macd > last_signal else 'Vente'

        # Signal Bollinger
        last_close = float(df['close'].iloc[-1])
        last_bb_upper = indicators['BB_Upper'].iloc[-1]
        last_bb_lower = indicators['BB_Lower'].iloc[-1]
        if last_close > last_bb_upper:
            signals['BB'] = 'Surachat'
        elif last_close < last_bb_lower:
            signals['BB'] = 'Survente'
        else:
            signals['BB'] = 'Neutre'

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
        summary.append(f"RSI: {signals['RSI']}")
        
        # Analyse MACD
        summary.append(f"MACD: Signal de {signals['MACD']}")
        
        # Analyse Bandes de Bollinger
        summary.append(f"Bandes de Bollinger: {signals['BB']}")
        
        return "\n".join(summary)