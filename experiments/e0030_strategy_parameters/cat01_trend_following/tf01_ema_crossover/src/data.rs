use chrono::NaiveDateTime;
use csv::ReaderBuilder;
use flate2::read::GzDecoder;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

/// One OHLCV bar.
///
/// ## Timezone / timestamp policy
/// `ts` is the bar's wall-clock label interpreted as a single, consistent
/// **exchange clock**. The source CSVs are stamped in EET; we parse the naive
/// `YYYY.MM.DD HH:MM:SS` label and convert it to a Unix epoch *as if it were
/// UTC* (`NaiveDateTime::and_utc`). We deliberately do **not** apply the real
/// EET↔UTC offset (which also carries DST transitions).
///
/// This is intentional and not a bug: it is an internally consistent monotonic
/// clock. The crucial property is that walk-forward window boundaries are
/// produced by [`year_start_ts`] using the *same* naive→UTC convention, so a
/// bar labelled `2015.01.01 00:00:00` maps to exactly the same epoch as the
/// `2015` boundary. IS/OOS slices therefore split on the calendar boundary the
/// data labels imply, with **no off-by-offset drift** at the edges. The only
/// consequence of skipping the real EET offset is that absolute epoch values
/// are shifted by a constant (±2/3 h) versus true UTC — irrelevant for
/// resampling, sorting, and year-aligned slicing, all of which are relative.
#[derive(Clone, Debug)]
pub struct Bar {
    pub ts: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
}

/// Load all available EURUSD yearly files from `data_dir` and return a
/// sorted, contiguous `Vec<Bar>` of 1-minute bars.
pub fn load_eurusd(data_dir: &Path) -> Vec<Bar> {
    let mut all: Vec<Bar> = Vec::with_capacity(6_000_000);

    for year in 2003..=2025 {
        let path = data_dir.join(format!("EURUSD_{}.csv.gz", year));
        if !path.exists() {
            continue;
        }

        let file = File::open(&path)
            .unwrap_or_else(|e| panic!("Cannot open {:?}: {}", path, e));
        let gz = GzDecoder::new(BufReader::new(file));
        let mut rdr = ReaderBuilder::new().delimiter(b';').from_reader(gz);

        for result in rdr.records() {
            let rec = result.unwrap_or_else(|e| panic!("CSV error in {:?}: {}", path, e));
            if rec.len() < 6 {
                continue;
            }
            let dt =
                NaiveDateTime::parse_from_str(rec[0].trim(), "%Y.%m.%d %H:%M:%S")
                    .unwrap_or_else(|e| panic!("Bad timestamp '{}': {}", &rec[0], e));
            all.push(Bar {
                ts: dt.and_utc().timestamp(),
                open:   rec[1].parse().unwrap_or(0.0),
                high:   rec[2].parse().unwrap_or(0.0),
                low:    rec[3].parse().unwrap_or(0.0),
                close:  rec[4].parse().unwrap_or(0.0),
                volume: rec[5].parse().unwrap_or(0.0),
            });
        }
    }

    all.sort_by_key(|b| b.ts);
    all
}

/// Resample 1-min bars to `minutes`-minute bars using standard OHLCV
/// aggregation: O = first, H = max, L = min, C = last, V = sum.
/// Weekend/session gaps are preserved as missing buckets (not filled).
pub fn resample(bars: &[Bar], minutes: u32) -> Vec<Bar> {
    if bars.is_empty() {
        return Vec::new();
    }

    let bucket_secs = (minutes as i64) * 60;
    let mut result: Vec<Bar> = Vec::with_capacity(bars.len() / minutes as usize + 1);

    let bucket_of = |ts: i64| (ts / bucket_secs) * bucket_secs;

    let mut cur_bucket = bucket_of(bars[0].ts);
    let mut open   = bars[0].open;
    let mut high   = bars[0].high;
    let mut low    = bars[0].low;
    let mut close  = bars[0].close;
    let mut volume = bars[0].volume;

    for bar in &bars[1..] {
        let b = bucket_of(bar.ts);
        if b == cur_bucket {
            if bar.high > high  { high = bar.high; }
            if bar.low  < low   { low  = bar.low;  }
            close  = bar.close;
            volume += bar.volume;
        } else {
            result.push(Bar { ts: cur_bucket, open, high, low, close, volume });
            cur_bucket = b;
            open   = bar.open;
            high   = bar.high;
            low    = bar.low;
            close  = bar.close;
            volume = bar.volume;
        }
    }
    result.push(Bar { ts: cur_bucket, open, high, low, close, volume });

    result
}

/// Epoch (seconds) of `year`-01-01 00:00:00 in the exchange clock used by
/// [`Bar::ts`]. Uses the same naive→UTC convention as bar parsing, so window
/// boundaries align exactly with the bar labels (see `Bar` docs for the policy).
pub fn year_start_ts(year: i32) -> i64 {
    use chrono::NaiveDate;
    NaiveDate::from_ymd_opt(year, 1, 1)
        .unwrap()
        .and_hms_opt(0, 0, 0)
        .unwrap()
        .and_utc()
        .timestamp()
}

/// Return the index range `[start, end)` of bars whose `ts` falls in
/// `[start_ts, end_ts)`.
pub fn ts_range(bars: &[Bar], start_ts: i64, end_ts: i64) -> (usize, usize) {
    let s = bars.partition_point(|b| b.ts < start_ts);
    let e = bars.partition_point(|b| b.ts < end_ts);
    (s, e)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_bar(ts: i64, o: f64, h: f64, l: f64, c: f64) -> Bar {
        Bar { ts, open: o, high: h, low: l, close: c, volume: 1.0 }
    }

    #[test]
    fn resample_5min() {
        // 6 one-minute bars → 2 five-minute bars
        let bars: Vec<Bar> = (0..6)
            .map(|i| make_bar(i * 60, 1.0 + i as f64 * 0.01, 1.01 + i as f64 * 0.01,
                              0.99 + i as f64 * 0.01, 1.005 + i as f64 * 0.01))
            .collect();
        let resampled = resample(&bars, 5);
        assert_eq!(resampled.len(), 2, "Expected 2 five-min bars");
        assert_eq!(resampled[0].open, bars[0].open);
        assert_eq!(resampled[0].close, bars[4].close);
        assert_eq!(resampled[1].open, bars[5].open);
    }
}
