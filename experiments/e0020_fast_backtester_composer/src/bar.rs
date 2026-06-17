use chrono::{DateTime, FixedOffset, NaiveDateTime};

/// Single 1-minute OHLCV bar. Timestamps are stored in EET as provided by the corpus.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Bar {
    pub timestamp: DateTime<FixedOffset>,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

impl Bar {
    pub fn parse_timestamp(raw: &str) -> Option<DateTime<FixedOffset>> {
        let naive = NaiveDateTime::parse_from_str(raw.trim(), "%Y.%m.%d %H:%M:%S").ok()?;
        // Corpus timestamps are labeled EET; treat them as UTC+2 without DST handling for now.
        naive.and_local_timezone(FixedOffset::east_opt(2 * 3600)?).single()
    }
}
