use crate::data::Bar;

/// Exponential Moving Average of bar closes.
/// First valid value = SMA of the first `period` closes (index `period - 1`).
/// Values before that are f64::NAN.
/// Multiplier k = 2 / (period + 1)  (standard EMA).
pub fn ema(bars: &[Bar], period: usize) -> Vec<f64> {
    let n = bars.len();
    let mut out = vec![f64::NAN; n];
    if n < period || period == 0 {
        return out;
    }

    let k = 2.0 / (period as f64 + 1.0);

    // Seed: SMA of first `period` closes
    let seed: f64 = bars[..period].iter().map(|b| b.close).sum::<f64>() / period as f64;
    out[period - 1] = seed;

    for i in period..n {
        out[i] = out[i - 1] + k * (bars[i].close - out[i - 1]);
    }
    out
}

/// Average True Range using Wilder's smoothing (k = 1 / period).
/// True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|).
/// First ATR value = SMA of the first `period` TRs (index `period - 1`).
pub fn atr(bars: &[Bar], period: usize) -> Vec<f64> {
    let n = bars.len();
    let mut out = vec![f64::NAN; n];
    if n < 2 || period == 0 {
        return out;
    }

    // True Range vector
    let mut tr = vec![0.0_f64; n];
    tr[0] = bars[0].high - bars[0].low;
    for i in 1..n {
        let hl = bars[i].high - bars[i].low;
        let hc = (bars[i].high - bars[i - 1].close).abs();
        let lc = (bars[i].low  - bars[i - 1].close).abs();
        tr[i] = hl.max(hc).max(lc);
    }

    if n < period {
        return out;
    }

    // Seed: SMA of first `period` TRs
    let seed: f64 = tr[..period].iter().sum::<f64>() / period as f64;
    out[period - 1] = seed;

    // Wilder smoothing
    let k = 1.0 / period as f64;
    for i in period..n {
        out[i] = out[i - 1] + k * (tr[i] - out[i - 1]);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bars_from_closes(closes: &[f64]) -> Vec<Bar> {
        closes.iter().enumerate().map(|(i, &c)| Bar {
            ts: i as i64 * 60,
            open: c, high: c * 1.001, low: c * 0.999, close: c, volume: 1.0,
        }).collect()
    }

    #[test]
    fn ema_seed_is_sma() {
        // For period=3, first EMA value (index 2) should equal SMA(3)
        let closes = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let bars = bars_from_closes(&closes);
        let e = ema(&bars, 3);
        assert!(e[0].is_nan());
        assert!(e[1].is_nan());
        let expected_seed = (1.0 + 2.0 + 3.0) / 3.0;  // 2.0
        assert!((e[2] - expected_seed).abs() < 1e-10, "seed={} expected={}", e[2], expected_seed);
    }

    #[test]
    fn ema_recurrence() {
        let closes = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let bars = bars_from_closes(&closes);
        let e = ema(&bars, 3);
        // k = 2/(3+1) = 0.5
        // e[2] = 2.0 (SMA)
        // e[3] = 2.0 + 0.5 * (4.0 - 2.0) = 3.0
        assert!((e[3] - 3.0).abs() < 1e-10, "e[3]={}", e[3]);
        // e[4] = 3.0 + 0.5 * (5.0 - 3.0) = 4.0
        assert!((e[4] - 4.0).abs() < 1e-10, "e[4]={}", e[4]);
    }

    #[test]
    fn atr_all_flat() {
        // If all bars have the same close and no intrabar range, ATR = 0
        let closes = vec![1.0; 20];
        let bars: Vec<Bar> = closes.iter().enumerate().map(|(i, &c)| Bar {
            ts: i as i64 * 60,
            open: c, high: c, low: c, close: c, volume: 1.0,
        }).collect();
        let a = atr(&bars, 14);
        // All TRs are 0, so ATR should be 0 after warm-up
        assert!((a[13]).abs() < 1e-10, "atr[13]={}", a[13]);
    }
}
