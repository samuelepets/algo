/// Simple moving average with `min_periods = period` semantics: warmup bars are NaN.
pub fn sma(values: &[f64], period: usize) -> Vec<f64> {
    let n = values.len();
    let mut out = vec![f64::NAN; n];
    if period == 0 || n < period {
        return out;
    }

    let mut sum: f64 = values[..period].iter().sum();
    out[period - 1] = sum / period as f64;
    for i in period..n {
        sum += values[i] - values[i - period];
        out[i] = sum / period as f64;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sma_matches_manual_average() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let avg = sma(&values, 3);
        assert!(avg[0].is_nan());
        assert!(avg[1].is_nan());
        assert!((avg[2] - 2.0).abs() < f64::EPSILON);
        assert!((avg[3] - 3.0).abs() < f64::EPSILON);
        assert!((avg[4] - 4.0).abs() < f64::EPSILON);
    }
}
