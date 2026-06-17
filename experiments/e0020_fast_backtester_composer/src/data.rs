use std::fs::{self, File};
use std::io::BufReader;
use std::path::{Path, PathBuf};

use csv::ReaderBuilder;
use flate2::read::GzDecoder;
use thiserror::Error;

use crate::bar::Bar;

#[derive(Debug, Error)]
pub enum DataError {
    #[error("failed to open {path}: {source}")]
    Open {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("failed to read CSV from {path}: {source}")]
    Read {
        path: PathBuf,
        source: csv::Error,
    },
    #[error("invalid timestamp in {path}: {value}")]
    Timestamp { path: PathBuf, value: String },
    #[error("invalid numeric field in {path}: {field}={value}")]
    Numeric {
        path: PathBuf,
        field: &'static str,
        value: String,
    },
    #[error("no data directory for symbol {symbol}: {path}")]
    MissingSymbol { symbol: String, path: PathBuf },
    #[error("no years selected for symbol {symbol}")]
    NoYears { symbol: String },
}

/// Resolve the repository root from this experiment directory.
pub fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repo root should exist")
}

/// Path to a yearly bar file, e.g. `data/bars/EURUSD/EURUSD_2024.csv.gz`.
pub fn bars_path(symbol: &str, year: u16) -> PathBuf {
    repo_root().join(format!("data/bars/{symbol}/{symbol}_{year}.csv.gz"))
}

/// Sorted list of years available for a symbol in the corpus.
pub fn available_years(symbol: &str) -> Result<Vec<u16>, DataError> {
    let symbol_dir = repo_root().join(format!("data/bars/{symbol}"));
    if !symbol_dir.is_dir() {
        return Err(DataError::MissingSymbol {
            symbol: symbol.to_string(),
            path: symbol_dir,
        });
    }

    let prefix = format!("{symbol}_");
    let mut years = Vec::new();
    for entry in fs::read_dir(&symbol_dir).map_err(|source| DataError::Open {
        path: symbol_dir.clone(),
        source,
    })? {
        let entry = entry.map_err(|source| DataError::Open {
            path: symbol_dir.clone(),
            source,
        })?;
        let name = entry.file_name();
        let name = name.to_string_lossy();
        if !name.starts_with(&prefix) || !name.ends_with(".csv.gz") {
            continue;
        }
        let year_str = &name[prefix.len()..name.len() - 7];
        if let Ok(year) = year_str.parse::<u16>() {
            years.push(year);
        }
    }
    years.sort_unstable();
    Ok(years)
}

/// Load all selected years for a symbol as one continuous, time-sorted stream.
///
/// Duplicate timestamps are dropped (first kept). Gaps from inactive periods are
/// not filled; consecutive rows form the continuous series used by the backtester.
pub fn load_bars_continuous(
    symbol: &str,
    start_year: Option<u16>,
    end_year: Option<u16>,
) -> Result<Vec<Bar>, DataError> {
    let all_years = available_years(symbol)?;
    let lo = start_year.unwrap_or_else(|| all_years.first().copied().unwrap_or(0));
    let hi = end_year.unwrap_or_else(|| all_years.last().copied().unwrap_or(0));
    let years: Vec<u16> = all_years
        .into_iter()
        .filter(|year| *year >= lo && *year <= hi)
        .collect();

    if years.is_empty() {
        return Err(DataError::NoYears {
            symbol: symbol.to_string(),
        });
    }

    let mut bars = Vec::new();
    for year in years {
        bars.extend(load_bars(bars_path(symbol, year))?);
    }

    bars.sort_by_key(|bar| bar.timestamp);
    bars.dedup_by_key(|bar| bar.timestamp);
    Ok(bars)
}

/// Load all bars from a gzipped semicolon-delimited CSV in the repo corpus.
pub fn load_bars(path: impl AsRef<Path>) -> Result<Vec<Bar>, DataError> {
    let path = path.as_ref().to_path_buf();
    let file = File::open(&path).map_err(|source| DataError::Open {
        path: path.clone(),
        source,
    })?;
    let decoder = GzDecoder::new(BufReader::new(file));
    let mut reader = ReaderBuilder::new()
        .delimiter(b';')
        .has_headers(true)
        .from_reader(decoder);

    let mut bars = Vec::new();
    for result in reader.records() {
        let record = result.map_err(|source| DataError::Read {
            path: path.clone(),
            source,
        })?;
        let timestamp = Bar::parse_timestamp(&record[0]).ok_or_else(|| DataError::Timestamp {
            path: path.clone(),
            value: record[0].to_string(),
        })?;
        bars.push(Bar {
            timestamp,
            open: parse_f64(&path, "Open", &record[1])?,
            high: parse_f64(&path, "High", &record[2])?,
            low: parse_f64(&path, "Low", &record[3])?,
            close: parse_f64(&path, "Close", &record[4])?,
            volume: parse_f64(&path, "Volume", &record[5])?,
        });
    }

    Ok(bars)
}

fn parse_f64(path: &Path, field: &'static str, raw: &str) -> Result<f64, DataError> {
    raw.trim()
        .parse()
        .map_err(|_| DataError::Numeric {
            path: path.to_path_buf(),
            field,
            value: raw.to_string(),
        })
}
