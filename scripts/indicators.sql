-- Moving Averages & Volume Spike & RSI prep
CREATE OR REPLACE VIEW indicators AS
WITH base AS (
    SELECT
        ticker,
        date,
        close,
        volume,
        AVG(close) OVER (
            PARTITION BY ticker ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS ma_20,
        AVG(close) OVER (
            PARTITION BY ticker ORDER BY date
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) AS ma_50,
        AVG(volume) OVER (
            PARTITION BY ticker ORDER BY date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS avg_volume_20,
        close - LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS price_change
    FROM ohlcv
),
rsi_calc AS (
    SELECT *,
        AVG(CASE WHEN price_change > 0 THEN price_change END) OVER (
            PARTITION BY ticker ORDER BY date
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_gain,
        AVG(CASE WHEN price_change < 0 THEN ABS(price_change) END) OVER (
            PARTITION BY ticker ORDER BY date
            ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) AS avg_loss
    FROM base
)
SELECT
    ticker,
    date,
    ROUND(close, 2)                                         AS price,
    ROUND(ma_20, 2)                                         AS ma_20,
    ROUND(ma_50, 2)                                         AS ma_50,
    ROUND(volume / avg_volume_20, 2)                        AS volume_ratio,
    ROUND(100 - (100 / (1 + avg_gain / NULLIF(avg_loss,0))),1) AS rsi,
    CASE
        WHEN close > ma_20 AND close > ma_50 THEN 'Bullish'
        WHEN close < ma_20 AND close < ma_50 THEN 'Bearish'
        ELSE 'Neutral'
    END AS signal
FROM rsi_calc;