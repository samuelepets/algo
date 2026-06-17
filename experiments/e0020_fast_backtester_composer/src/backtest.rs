use crate::bar::Bar;
use crate::metrics::{self, Metrics};

/// Outcome of a single vectorized backtest run.
#[derive(Debug, Clone, PartialEq)]
pub struct BacktestResult {
    pub returns: Vec<f64>,
    pub equity: Vec<f64>,
    pub position: Vec<f64>,
    pub metrics: Metrics,
}

/// Run a vectorized backtest.
///
/// Execution convention (aligned with e0010): `signal[t]` uses information up to
/// and including `Close(t)`; the position held over `[Open(t), Open(t+1))` is
/// `signal[t-1]`. Per-bar return is open-to-open: `Open(t+1) / Open(t) - 1`.
pub fn backtest(bars: &[Bar], signal: &[f64], cost_per_turnover: f64) -> BacktestResult {
    let n = bars.len().min(signal.len());
    if n < 2 {
        return BacktestResult {
            returns: Vec::new(),
            equity: Vec::new(),
            position: Vec::new(),
            metrics: metrics::compute_metrics(&[], &[], &[], 60.0),
        };
    }

    let mut returns = Vec::with_capacity(n - 1);
    let mut equity = Vec::with_capacity(n - 1);
    let mut position_out = Vec::with_capacity(n - 1);
    let mut turnover_out = Vec::with_capacity(n - 1);

    let mut prev_position = 0.0;
    let mut cumulative_equity = 1.0;

    for i in 0..(n - 1) {
        let position = if i == 0 {
            0.0
        } else {
            signal[i - 1].clamp(-1.0, 1.0)
        };
        let bar_ret = bars[i + 1].open / bars[i].open - 1.0;
        let turnover = (position - prev_position).abs();
        let gross = position * bar_ret;
        let net = gross - turnover * cost_per_turnover;

        cumulative_equity *= 1.0 + net;
        returns.push(net);
        equity.push(cumulative_equity);
        position_out.push(position);
        turnover_out.push(turnover);
        prev_position = position;
    }

    let timestamps: Vec<_> = bars.iter().take(n).map(|b| b.timestamp).collect();
    let spacing = metrics::infer_bar_spacing_secs(&timestamps);
    let metrics = metrics::compute_metrics(&returns, &position_out, &turnover_out, spacing);

    BacktestResult {
        returns,
        equity,
        position: position_out,
        metrics,
    }
}

#[cfg(test)]
mod tests {
    use chrono::{FixedOffset, TimeZone};

    use super::*;

    fn bar(minute: u32, open: f64, close: f64) -> Bar {
        let tz = FixedOffset::east_opt(2 * 3600).unwrap();
        Bar {
            timestamp: tz.with_ymd_and_hms(2024, 1, 2, 0, minute, 0).unwrap(),
            open,
            high: open,
            low: open,
            close,
            volume: 1.0,
        }
    }

    #[test]
    fn flat_signal_has_zero_return() {
        let bars = vec![bar(0, 1.0, 1.0), bar(1, 1.1, 1.1), bar(2, 1.0, 1.0)];
        let signal = vec![0.0, 0.0, 0.0];
        let result = backtest(&bars, &signal, 0.0);
        assert!(result.returns.iter().all(|r| r.abs() < f64::EPSILON));
    }

    #[test]
    fn long_signal_tracks_open_to_open() {
        let bars = vec![bar(0, 1.0, 1.0), bar(1, 1.1, 1.1), bar(2, 1.21, 1.21)];
        let signal = vec![1.0, 1.0, 1.0];
        let result = backtest(&bars, &signal, 0.0);
        assert_eq!(result.returns.len(), 2);
        assert!(result.returns[0].abs() < f64::EPSILON);
        assert!((result.returns[1] - 0.1).abs() < 1e-12);
    }
}
