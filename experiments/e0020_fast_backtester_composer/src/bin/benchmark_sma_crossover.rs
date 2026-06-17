use std::time::Instant;

use anyhow::{Context, Result};
use fast_backtester::{available_years, backtest, load_bars_continuous, DualSmaCrossover};

const RUNS: usize = 10;

fn main() -> Result<()> {
    let fast_period = 50_usize;
    let slow_period = 200_usize;
    let hold_bars = 60_usize;
    let cost_per_turnover = 0.0;

    let years = available_years("EURUSD").context("list EURUSD years")?;
    eprintln!(
        "EURUSD continuous stream: {} -> {} ({} files)",
        years.first().unwrap(),
        years.last().unwrap(),
        years.len()
    );

    let t0 = Instant::now();
    let bars = load_bars_continuous("EURUSD", None, None)
        .context("load EURUSD continuous bars")?;
    let load_ms = t0.elapsed().as_secs_f64() * 1000.0;

    let strategy = DualSmaCrossover::new(fast_period, slow_period, hold_bars);

    let mut signal_ms_runs = Vec::with_capacity(RUNS);
    let mut backtest_ms_runs = Vec::with_capacity(RUNS);
    let mut result = None;

    for _ in 0..RUNS {
        let t_signal = Instant::now();
        let signal = strategy.generate_signal(&bars);
        signal_ms_runs.push(t_signal.elapsed().as_secs_f64() * 1000.0);

        let t_backtest = Instant::now();
        result = Some(backtest(&bars, &signal, cost_per_turnover));
        backtest_ms_runs.push(t_backtest.elapsed().as_secs_f64() * 1000.0);
    }

    let signal_ms = mean(&signal_ms_runs);
    let backtest_ms = mean(&backtest_ms_runs);
    let backtest_run_ms = signal_ms + backtest_ms;
    let m = &result.expect("at least one backtest run").metrics;

    println!("strategy=DualSmaCrossover fast={fast_period} slow={slow_period} hold_bars={hold_bars}");
    println!("bars={}", bars.len());
    println!("runs={RUNS}");
    println!("load_ms={load_ms:.1}");
    println!("signal_ms_avg={signal_ms:.1}");
    println!("backtest_ms_avg={backtest_ms:.1}");
    println!("backtest_run_ms_avg={backtest_run_ms:.1}");
    println!("total_return={:.6}", m.total_return);
    println!("ann_return={:.6}", m.ann_return);
    println!("ann_vol={:.6}", m.ann_vol);
    println!("sharpe={:.4}", m.sharpe);
    println!("max_drawdown={:.6}", m.max_drawdown);
    println!("hit_rate={:.4}", m.hit_rate);
    println!("ann_turnover={:.4}", m.ann_turnover);
    println!("n_bars={}", m.n_bars);

    Ok(())
}

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}
