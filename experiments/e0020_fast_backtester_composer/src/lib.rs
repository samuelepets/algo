//! High-performance vectorized backtester for 1-minute OHLCV bars.
//!
//! Loads gzipped semicolon-delimited CSVs from the repository `data/` corpus and
//! runs look-ahead-free open-to-open backtests over contiguous bar streams.

pub mod backtest;
pub mod bar;
pub mod data;
pub mod indicators;
pub mod metrics;
pub mod strategy;

pub use backtest::{backtest, BacktestResult};
pub use bar::Bar;
pub use data::{available_years, bars_path, load_bars, load_bars_continuous, repo_root, DataError};
pub use metrics::Metrics;
pub use strategy::DualSmaCrossover;
