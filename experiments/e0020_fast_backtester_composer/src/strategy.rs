use crate::bar::Bar;
use crate::indicators::sma;

/// Dual-SMA crossover with fixed holding period: at most one open position at a
/// time; each entry lasts exactly `hold_bars` bars, then returns to flat.
#[derive(Debug, Clone, Copy)]
pub struct DualSmaCrossover {
    pub fast_period: usize,
    pub slow_period: usize,
    pub hold_bars: usize,
}

impl Default for DualSmaCrossover {
    fn default() -> Self {
        Self {
            fast_period: 50,
            slow_period: 200,
            hold_bars: 60,
        }
    }
}

impl DualSmaCrossover {
    pub fn new(fast_period: usize, slow_period: usize, hold_bars: usize) -> Self {
        Self {
            fast_period,
            slow_period,
            hold_bars,
        }
    }

    /// Target position in `[-1, 1]` using close prices up to and including bar `t`.
    pub fn generate_signal(&self, bars: &[Bar]) -> Vec<f64> {
        let closes: Vec<f64> = bars.iter().map(|b| b.close).collect();
        let fast = sma(&closes, self.fast_period);
        let slow = sma(&closes, self.slow_period);
        let n = closes.len();

        let mut signal = vec![0.0; n];
        let mut position = 0.0_f64;
        let mut bars_left = 0_usize;

        for t in 0..n {
            if bars_left > 0 {
                if bars_left == 1 {
                    position = 0.0;
                    bars_left = 0;
                } else {
                    bars_left -= 1;
                }
            } else if self.hold_bars > 0 && t > 0 {
                let (f_prev, s_prev) = (fast[t - 1], slow[t - 1]);
                let (f, s) = (fast[t], slow[t]);
                if !f_prev.is_nan() && !s_prev.is_nan() && !f.is_nan() && !s.is_nan() {
                    if f > s && f_prev <= s_prev {
                        position = 1.0;
                        bars_left = self.hold_bars;
                    } else if f < s && f_prev >= s_prev {
                        position = -1.0;
                        bars_left = self.hold_bars;
                    }
                }
            }

            signal[t] = position;
        }

        signal
    }
}

#[cfg(test)]
mod tests {
    use chrono::{Duration, FixedOffset, TimeZone};

    use super::*;

    fn count_nonzero(signal: &[f64]) -> usize {
        signal.iter().filter(|&&s| s != 0.0).count()
    }

    fn bar(offset_minutes: i64, close: f64) -> Bar {
        let tz = FixedOffset::east_opt(2 * 3600).unwrap();
        let base = tz.with_ymd_and_hms(2024, 1, 2, 0, 0, 0).unwrap();
        Bar {
            timestamp: base + Duration::minutes(offset_minutes),
            open: close,
            high: close,
            low: close,
            close,
            volume: 1.0,
        }
    }

    #[test]
    fn holds_long_for_fixed_bars_then_flattens() {
        let mut bars: Vec<Bar> = (0..250).map(|i| bar(i, 1.0)).collect();
        for (i, b) in bars.iter_mut().enumerate().skip(200) {
            b.close = 1.0 + (i - 200) as f64 * 0.05;
            b.open = b.close;
            b.high = b.close;
            b.low = b.close;
        }

        let strategy = DualSmaCrossover {
            hold_bars: 5,
            ..Default::default()
        };
        let signal = strategy.generate_signal(&bars);
        assert_eq!(count_nonzero(&signal), 5, "exactly one trade of 5 bars");
        assert!(signal.windows(5).any(|w| w.iter().all(|&s| s == 1.0)));
    }

    #[test]
    fn each_trade_lasts_exactly_hold_bars() {
        let mut bars: Vec<Bar> = (0..500).map(|i| bar(i, 1.0)).collect();
        for (i, b) in bars.iter_mut().enumerate().skip(200) {
            b.close = 1.0 + (i - 200) as f64 * 0.01;
            b.open = b.close;
            b.high = b.close;
            b.low = b.close;
        }

        let strategy = DualSmaCrossover {
            hold_bars: 30,
            ..Default::default()
        };
        let signal = strategy.generate_signal(&bars);

        let mut run_len = 0_usize;
        let mut run_sign = 0.0_f64;
        for &s in &signal {
            if s == 0.0 {
                if run_len > 0 {
                    assert_eq!(run_len, strategy.hold_bars);
                    run_len = 0;
                }
            } else if run_len == 0 {
                run_sign = s;
                run_len = 1;
            } else {
                assert_eq!(s, run_sign);
                run_len += 1;
            }
        }
        if run_len > 0 {
            assert_eq!(run_len, strategy.hold_bars);
        }
    }

    #[test]
    fn flat_without_crossover() {
        let bars: Vec<Bar> = (0..250).map(|i| bar(i, 1.0)).collect();
        let strategy = DualSmaCrossover::default();
        let signal = strategy.generate_signal(&bars);
        assert!(signal.iter().all(|&s| s == 0.0));
    }
}
