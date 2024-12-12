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
        self.indicators['BB_Upper'] = float(bb_upper.iloc[-1])
        self.indicators['BB_Middle'] = float(bb_middle.iloc[-1])
        self.indicators['BB_Lower'] = float(bb_lower.iloc[-1])

        # Moyennes Mobiles
        self.indicators['SMA_20'] = float(self.calculate_sma(df['close'], 20).iloc[-1])
        self.indicators['EMA_20'] = float(self.calculate_ema(df['close'], 20).iloc[-1])

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
        if indicators['RSI'] < 30:
            signals['RSI'] = 'Survente'
        elif indicators['RSI'] > 70:
            signals['RSI'] = 'Surachat'
        else:
            signals['RSI'] = 'Neutre'

        # Signal MACD
        if indicators['MACD'] > indicators['MACD_Signal']:
            signals['MACD'] = 'Achat'
        else:
            signals['MACD'] = 'Vente'

        # Signal Bollinger
        last_close = float(df['close'].iloc[-1])
        if last_close > indicators['BB_Upper']:
            signals['BB'] = 'Surachat'
        elif last_close < indicators['BB_Lower']:
            signals['BB'] = 'Survente'
        else:
            signals['BB'] = 'Neutre'

        # Signal global
        signals['GLOBAL'] = 'Achat' if signals['MACD'] == 'Achat' and signals['RSI'] == 'Survente' else 'Vente'

        return signals

    def get_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Génère un résumé de l'analyse technique
        :param df: DataFrame avec les données OHLCV
        :return: Dictionnaire contenant les indicateurs, signaux et résumé
        """
        indicators = self.calculate_all(df)
        signals = self.get_signals(df)
        
        # Création du résumé textuel
        summary = []
        
        # Résumé RSI
        summary.append(f"RSI ({indicators['RSI']:.2f}): {signals['RSI']}")
        
        # Résumé MACD
        summary.append(f"MACD: {signals['MACD']} (MACD: {indicators['MACD']:.2f}, Signal: {indicators['MACD_Signal']:.2f})")
        
        # Résumé Bollinger
        last_close = float(df['close'].iloc[-1])
        summary.append(f"Bollinger: {signals['BB']} (Prix: {last_close:.2f}, Haut: {indicators['BB_Upper']:.2f}, Bas: {indicators['BB_Lower']:.2f})")
        
        # Résumé global
        summary.append(f"Signal Global: {signals['GLOBAL']}")
        
        return {
            'indicators': indicators,
            'signals': signals,
            'summary': '\n'.join(summary)
        }
