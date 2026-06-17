use std::env;

use anyhow::{Context, Result};
use fast_backtester::{backtest, bars_path, load_bars};

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let symbol = args.get(1).map(String::as_str).unwrap_or("EURUSD");
    let year: u16 = args
        .get(2)
        .map(|s| s.parse())
        .transpose()
        .context("year must be a valid u16")?
        .unwrap_or(2024);

    let path = bars_path(symbol, year);
    eprintln!("loading {}", path.display());
    let bars = load_bars(&path).with_context(|| format!("failed to load {}", path.display()))?;
    eprintln!("loaded {} bars", bars.len());

    // Placeholder: flat signal benchmark to validate the pipeline end-to-end.
    let signal = vec![0.0; bars.len()];
    let result = backtest(&bars, &signal, 0.0);

    println!("bars={}", result.metrics.n_bars);
    println!("total_return={:.6}", result.metrics.total_return);
    println!("sharpe={:.4}", result.metrics.sharpe);

    Ok(())
}
