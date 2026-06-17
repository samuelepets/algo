use crate::data::Bar;

/// Round-trip transaction cost in price units (0.8 pip for EURUSD).
pub const SPREAD: f64 = 0.00008;

/// ATR period for stop placement.
pub const ATR_PERIOD: usize = 14;

#[derive(Clone, Debug)]
pub struct Params {
    pub fast_ema: usize,
    pub slow_ema: usize,
    pub atr_stop_mult: f64,
    pub rr_ratio: f64,
    pub tf_min: u32,
}

#[derive(Clone, Debug, Default)]
pub struct Metrics {
    pub sharpe: f64,
    pub profit_factor: f64,
    /// Maximum peak-to-trough decline of the cumulative-R equity curve,
    /// expressed in **absolute R units** (always ≥ 0). The equity curve starts
    /// at 0 R, so a strategy that only loses has its peak pinned at the 0-R
    /// starting baseline and its max drawdown equals its worst cumulative loss.
    pub max_drawdown_r: f64,
    pub total_return: f64,  // sum of R multiples
    pub n_trades: usize,
}

/// Run a full backtest over `bars` with pre-computed indicators.
///
/// Returns per-trade P&L expressed in **R multiples** (risk-adjusted units):
///   R = PnL / stop_distance
/// so a full stop-hit = −1R, a 2:1 target hit = +2R.
///
/// Sharpe is annualised using the frequency of trades relative to
/// the total data span.
pub fn backtest(
    bars: &[Bar],
    fast: &[f64],
    slow: &[f64],
    atr_vals: &[f64],
    params: &Params,
) -> Metrics {
    let n = bars.len();
    if n < 2 {
        return Metrics::default();
    }

    let mut trades: Vec<f64> = Vec::with_capacity(256);

    // ── Position state ──────────────────────────────────────────────────
    let mut in_pos   = false;
    let mut is_long  = false;
    let mut entry    = 0.0_f64;
    let mut stop     = 0.0_f64;
    let mut target   = 0.0_f64;
    let mut risk_r   = 0.0_f64; // stop_distance (in price units)

    // Warm-up: need at least `slow_ema` valid EMA values and 14 ATR values.
    let warm = params.slow_ema.max(ATR_PERIOD) + 1;

    for i in warm..n {
        // ── Guard: require valid indicators ──────────────────────────────
        if fast[i].is_nan() || slow[i].is_nan() || atr_vals[i].is_nan()
            || fast[i - 1].is_nan() || slow[i - 1].is_nan()
        {
            continue;
        }

        let fast_now  = fast[i];
        let fast_prev = fast[i - 1];
        let slow_now  = slow[i];
        let slow_prev = slow[i - 1];

        // ── Exit check ───────────────────────────────────────────────────
        let mut just_exited = false;
        if in_pos {
            let exit_r: Option<f64> = if is_long {
                if bars[i].low <= stop {
                    // Stop hit — exit at stop price
                    Some((stop - entry - SPREAD) / risk_r)
                } else if bars[i].high >= target {
                    // Target hit — exit at target price
                    Some((target - entry - SPREAD) / risk_r)
                } else if fast_prev > slow_prev && fast_now < slow_now {
                    // Opposite (bear) crossover — exit at bar close
                    Some((bars[i].close - entry - SPREAD) / risk_r)
                } else {
                    None
                }
            } else {
                // Short position
                if bars[i].high >= stop {
                    Some((entry - stop - SPREAD) / risk_r)
                } else if bars[i].low <= target {
                    Some((entry - target - SPREAD) / risk_r)
                } else if fast_prev < slow_prev && fast_now > slow_now {
                    // Bull crossover exits short
                    Some((entry - bars[i].close - SPREAD) / risk_r)
                } else {
                    None
                }
            };

            if let Some(r) = exit_r {
                trades.push(r);
                in_pos = false;
                just_exited = true;
            }
        }

        // ── Entry check (only if flat; never enter on the same bar as exit) ─
        if !in_pos && !just_exited {
            let bull_cross = fast_prev < slow_prev && fast_now > slow_now;
            let bear_cross = fast_prev > slow_prev && fast_now < slow_now;
            let fast_up    = fast_now > fast_prev;
            let fast_dn    = fast_now < fast_prev;
            let slow_up    = slow_now > slow_prev;
            let slow_dn    = slow_now < slow_prev;

            let atr_v = atr_vals[i];

            if bull_cross && fast_up && slow_up {
                let dist = atr_v * params.atr_stop_mult;
                if dist > 1e-10 {
                    entry   = bars[i].close;
                    stop    = entry - dist;
                    target  = entry + dist * params.rr_ratio;
                    risk_r  = dist;
                    is_long = true;
                    in_pos  = true;
                }
            } else if bear_cross && fast_dn && slow_dn {
                let dist = atr_v * params.atr_stop_mult;
                if dist > 1e-10 {
                    entry   = bars[i].close;
                    stop    = entry + dist;
                    target  = entry - dist * params.rr_ratio;
                    risk_r  = dist;
                    is_long = false;
                    in_pos  = true;
                }
            }
        }
    }

    // Close any open position at end of data
    if in_pos && risk_r > 1e-10 {
        let last = &bars[n - 1];
        let r = if is_long {
            (last.close - entry - SPREAD) / risk_r
        } else {
            (entry - last.close - SPREAD) / risk_r
        };
        trades.push(r);
    }

    compute_metrics(&trades, bars, params)
}

fn compute_metrics(trades: &[f64], bars: &[Bar], _params: &Params) -> Metrics {
    let n = trades.len();
    if n < 2 {
        return Metrics::default();
    }

    // ── Sharpe ──────────────────────────────────────────────────────────
    let mean_r: f64 = trades.iter().sum::<f64>() / n as f64;
    let var_r: f64  = trades.iter().map(|r| (r - mean_r).powi(2)).sum::<f64>()
                      / (n as f64 - 1.0);
    let std_r = var_r.sqrt();

    // Annualise by trade frequency relative to calendar span
    let span_years = if bars.len() >= 2 {
        let secs = (bars[bars.len() - 1].ts - bars[0].ts) as f64;
        secs / (365.25 * 24.0 * 3600.0)
    } else {
        1.0
    };
    let trades_per_year = n as f64 / span_years.max(0.01);
    let sharpe = if std_r > 1e-12 {
        (mean_r / std_r) * trades_per_year.sqrt()
    } else {
        0.0
    };

    // ── Profit factor ────────────────────────────────────────────────────
    let gross_win:  f64 = trades.iter().filter(|&&r| r > 0.0).sum();
    let gross_loss: f64 = trades.iter().filter(|&&r| r < 0.0).map(|r| r.abs()).sum();
    let profit_factor = if gross_loss > 1e-12 {
        gross_win / gross_loss
    } else if gross_win > 0.0 {
        f64::INFINITY
    } else {
        0.0
    };

    // ── Max drawdown (absolute R units) ──────────────────────────────────
    // Equity curve is measured in cumulative R and starts at 0. The running
    // peak is also seeded at 0, so it represents the high-water mark relative
    // to the initial baseline. Drawdown is `peak - cum_r` (no division), which
    // is always ≥ 0 and avoids the divide-by-near-zero artifacts of a
    // normalised definition. A strategy that never recovers above its starting
    // point keeps `peak == 0`, so its max drawdown equals its deepest loss.
    let mut cum_r  = 0.0_f64;
    let mut peak   = 0.0_f64;
    let mut max_dd = 0.0_f64;
    for &r in trades {
        cum_r += r;
        if cum_r > peak { peak = cum_r; }
        let dd = peak - cum_r;
        if dd > max_dd { max_dd = dd; }
    }

    Metrics {
        sharpe,
        profit_factor,
        max_drawdown_r: max_dd,
        total_return: trades.iter().sum(),
        n_trades: n,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::Bar;

    fn flat_bars(n: usize, price: f64) -> Vec<Bar> {
        (0..n).map(|i| Bar {
            ts: i as i64 * 300, // 5-min spacing
            open: price, high: price * 1.001,
            low: price * 0.999, close: price, volume: 1.0,
        }).collect()
    }

    #[test]
    fn no_trades_on_flat_bars() {
        // With a constant price, EMAs never cross → no trades
        let bars = flat_bars(200, 1.1000);
        use crate::indicators::{ema, atr};
        let fast = ema(&bars, 9);
        let slow = ema(&bars, 21);
        let atr_v = atr(&bars, 14);
        let params = Params { fast_ema: 9, slow_ema: 21, atr_stop_mult: 1.5, rr_ratio: 2.0, tf_min: 5 };
        let m = backtest(&bars, &fast, &slow, &atr_v, &params);
        assert_eq!(m.n_trades, 0, "Expected 0 trades on flat bars");
    }
}
