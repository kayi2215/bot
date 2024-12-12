# Architecture du Trading Bot Binance

## Vue d'ensemble du système

```mermaid
classDiagram
    class TradingBot {
        -logger
        -symbols: List[str]
        -db: MongoDBManager
        -market_data: MarketDataCollector
        -monitoring_service: MonitoringService
        -data_updater: MarketUpdater
        -is_running: bool
        +__init__(symbols, db)
        +setup_logging()
        +start_monitoring()
        +trading_loop()
        +start_trading()
        +start()
        +stop()
    }

    class MarketDataCollector {
        -client: BinanceClient
        -logger
        -technical_analyzer: TechnicalAnalysis
        +__init__(api_key, api_secret)
        +get_current_price(symbol)
        +get_klines(symbol, interval, limit)
        +get_order_book(symbol, limit)
        +get_recent_trades(symbol, limit)
        +get_technical_analysis(symbol, interval, limit)
        +get_market_analysis(symbol)
        +get_ticker(symbol)
    }

    class TechnicalAnalysis {
        -indicators: dict
        +calculate_rsi(data, periods)
        +calculate_sma(data, periods)
        +calculate_ema(data, periods)
        +calculate_macd(data)
        +calculate_bollinger_bands(data, periods)
        +calculate_all(df)
        +get_signals(df)
        +get_summary(df)
    }

    class MongoDBManager {
        -client: MongoClient
        -db: Database
        -market_data: Collection
        -indicators: Collection
        -trades: Collection
        -monitoring: Collection
        -api_metrics: Collection
        +store_market_data(symbol, data)
        +store_indicators(symbol, indicators)
        +store_trade(trade_data)
        +get_latest_market_data(symbol, limit)
        +get_latest_indicators(symbol, limit)
        +cleanup_old_data()
    }

    class APIMonitor {
        -metrics: List
        -alert_thresholds: Dict
        -client: BinanceClient
        -consecutive_failures: int
        +measure_latency()
        +check_availability()
        +get_metrics_summary()
        +record_metric()
    }

    class MonitoringService {
        -api_monitor: APIMonitor
        -is_running: bool
        +run()
        +stop()
        +check_api_health()
    }

    class MarketUpdater {
        -symbols: List[str]
        -db: MongoDBManager
        -market_data: MarketDataCollector
        -api_key: str
        -api_secret: str
        +update_market_data(symbol)
        +run()
        +stop()
    }

    TradingBot --> MarketDataCollector : uses
    TradingBot --> MongoDBManager : uses
    TradingBot --> MonitoringService : uses
    TradingBot --> MarketUpdater : uses
    MarketDataCollector --> TechnicalAnalysis : uses
    MonitoringService --> APIMonitor : uses
    MarketUpdater --> MarketDataCollector : uses
    MarketUpdater --> MongoDBManager : uses

    note for TradingBot "Orchestrateur principal du système"
    note for MarketDataCollector "Interface avec l'API Binance"
    note for MongoDBManager "Gestion de la persistance"
    note for TechnicalAnalysis "Analyse technique"
    note for APIMonitor "Surveillance de l'API Binance"
    note for MarketUpdater "Mise à jour des données"
```

## Structure des Données

```mermaid
graph TB
    subgraph "Structure de Données MongoDB"
        MD[Market Data Collection]
        IND[Indicators Collection]
        TR[Trades Collection]
        MON[Monitoring Collection]
        API[API Metrics Collection]
        
        MD -->|Contient| MDD[Document]
        MDD -->|Champs| S1[symbol]
        MDD -->|Champs| T1[timestamp]
        MDD -->|Champs| D1[data]
        D1 -->|Contient| P[last_price]
        D1 -->|Contient| V[volume_24h]
        D1 -->|Contient| RD[raw_data]
        
        IND -->|Contient| INDD[Document]
        INDD -->|Champs| S2[symbol]
        INDD -->|Champs| T2[timestamp]
        INDD -->|Champs| D2[indicators]
        
        TR -->|Contient| TRD[Document]
        TRD -->|Champs| S3[symbol]
        TRD -->|Champs| T3[timestamp]
        TRD -->|Champs| D3[trade_data]
    end
```

## Description des Composants

### TradingBot
- Composant central qui orchestre tout le système
- Gère les cycles de trading et la coordination des services
- Maintient l'état global du système
- Gère les threads de trading, monitoring et mise à jour des données

### MarketDataCollector
- Interface directe avec l'API Binance via binance.client.Client
- Collecte les données de marché en temps réel
- Intègre l'analyse technique via TechnicalAnalysis
- Gère les formats de données spécifiques à Binance (24h stats, etc.)

### TechnicalAnalysis
- Calcule les indicateurs techniques (RSI, MACD, Bollinger Bands)
- Fournit des signaux de trading
- Analyse les tendances du marché
- Génère des résumés d'analyse technique

### MongoDBManager
- Gère toutes les opérations de base de données
- Maintient plusieurs collections pour différents types de données
- Gère le nettoyage et l'optimisation des données
- Fournit des méthodes d'accès standardisées

### APIMonitor & MonitoringService
- Surveille la santé de l'API Binance
- Mesure la latence et la disponibilité
- Gère les alertes et les métriques
- Assure la fiabilité du système
- Gère les limites de taux spécifiques à Binance

### MarketUpdater
- Met à jour les données de marché périodiquement
- Coordonne la collecte et le stockage des données
- Gère les erreurs de mise à jour
- Maintient la fraîcheur des données
- Utilise les clés API Binance pour l'authentification