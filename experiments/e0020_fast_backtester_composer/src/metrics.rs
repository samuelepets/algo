/// Summary statistics for a per-bar net return stream.
#[derive(Debug, Clone, PartialEq)]
pub struct Metrics {
    pub total_return: f64,
    pub ann_return: f64,
    pub ann_vol: f64,
    pub sharpe: f64,
    pub max_drawdown: f64,
    pub hit_rate: f64,
    pub ann_turnover: f64,
    pub n_bars: usize,
}

const SECONDS_PER_YEAR: f64 = 365.25 * 24.0 * 3600.0;

pub fn compute_metrics(
    returns: &[f64],
    position: &[f64],
    turnover: &[f64],
    bar_spacing_secs: f64,
) -> Metrics {
    let n = returns.len();
    if n == 0 {
        return Metrics {
            total_return: 0.0,
            ann_return: 0.0,
            ann_vol: 0.0,
            sharpe: 0.0,
            max_drawdown: 0.0,
            hit_rate: f64::NAN,
            ann_turnover: 0.0,
            n_bars: 0,
        };
    }

    let periods_per_year = SECONDS_PER_YEAR / bar_spacing_secs;
    let total_return = returns.iter().fold(1.0, |acc, r| acc * (1.0 + r)) - 1.0;
    let log_growth: f64 = returns.iter().map(|r| (1.0 + r).ln()).sum();
    let exp_arg = (log_growth * periods_per_year / n as f64).min(700.0);
    let ann_return = exp_arg.exp_m1();

    let mean = returns.iter().sum::<f64>() / n as f64;
    let variance = returns.iter().map(|r| (r - mean).powi(2)).sum::<f64>() / n as f64;
    let std = variance.sqrt();
    let ann_vol = std * periods_per_year.sqrt();
    let sharpe = if std > 0.0 {
        mean / std * periods_per_year.sqrt()
    } else {
        0.0
    };

    let mut equity = 1.0_f64;
    let mut peak = 1.0_f64;
    let mut max_drawdown = 0.0_f64;
    for r in returns {
        equity *= 1.0 + r;
        peak = peak.max(equity);
        max_drawdown = max_drawdown.min(equity / peak - 1.0);
    }

    let active: Vec<f64> = returns
        .iter()
        .zip(position.iter())
        .filter_map(|(r, p)| (*p != 0.0).then_some(*r))
        .collect();
    let hit_rate = if active.is_empty() {
        f64::NAN
    } else {
        active.iter().filter(|r| **r > 0.0).count() as f64 / active.len() as f64
    };

    let ann_turnover = turnover.iter().sum::<f64>() * periods_per_year / n as f64;

    Metrics {
        total_return,
        ann_return,
        ann_vol,
        sharpe,
        max_drawdown,
        hit_rate,
        ann_turnover,
        n_bars: n,
    }
}

/// Infer bar spacing in seconds from consecutive timestamps.
pub fn infer_bar_spacing_secs(timestamps: &[chrono::DateTime<chrono::FixedOffset>]) -> f64 {
    if timestamps.len() < 2 {
        return 60.0;
    }
    let mut deltas: Vec<i64> = timestamps
        .windows(2)
        .map(|w| (w[1] - w[0]).num_seconds())
        .filter(|&d| d > 0)
        .collect();
    if deltas.is_empty() {
        return 60.0;
    }
    deltas.sort_unstable();
    deltas[deltas.len() / 2] as f64
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_returns_zero_metrics() {
        let m = compute_metrics(&[], &[], &[], 60.0);
        assert_eq!(m.n_bars, 0);
        assert_eq!(m.total_return, 0.0);
    }

    #[test]
    fn constant_positive_return() {
        let returns = vec![0.001; 100];
        let position = vec![1.0; 100];
        let turnover = vec![0.0; 100];
        let m = compute_metrics(&returns, &position, &turnover, 60.0);
        assert!(m.total_return > 0.0);
        assert!(m.sharpe > 0.0);
    }
}
