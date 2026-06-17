mod backtest;
mod data;
mod indicators;

use backtest::{backtest, Metrics, Params, ATR_PERIOD};
use data::{load_eurusd, resample, ts_range, year_start_ts, Bar};
use indicators::{atr, ema};

use rayon::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::time::Instant;

// ── Parameter grid ────────────────────────────────────────────────────────────
const FAST_EMAS:  &[usize] = &[3, 5, 7, 8, 9, 10, 12, 13];
const SLOW_EMAS:  &[usize] = &[18, 20, 21, 25, 26, 30, 34, 50];
const ATR_MULTS:  &[f64]   = &[0.5, 1.0, 1.5, 2.0, 2.5];
const RR_RATIOS:  &[f64]   = &[1.0, 1.5, 2.0, 2.5, 3.0];
const TIMEFRAMES: &[u32]   = &[5, 15];

/// Minimum trades required for a result to be considered valid.
const MIN_TRADES: usize = 50;

fn main() {
    // ── Locate data directory ─────────────────────────────────────────────────
    let data_dir = PathBuf::from("../../../../data/bars/EURUSD");
    if !data_dir.exists() {
        eprintln!(
            "ERROR: Data directory not found at {:?}\n\
             Run `cargo run --release` from the project root:\n  \
             experiments/e0030_strategy_parameters/cat01_trend_following/tf01_ema_crossover/",
            data_dir
        );
        std::process::exit(1);
    }
    fs::create_dir_all("outputs").expect("Cannot create outputs/");

    // ── Load 1-min bars ───────────────────────────────────────────────────────
    println!("Loading EURUSD 1-min bars...");
    let t0 = Instant::now();
    let bars_1min = load_eurusd(&data_dir);
    println!(
        "  {} bars  ({:.2} years)  [{:.1}s]",
        bars_1min.len(),
        bars_1min.len() as f64 / (252.0 * 1440.0),
        t0.elapsed().as_secs_f32()
    );
    assert!(bars_1min.len() >= 1_000_000, "Expected ≥ 1 M bars; got {}", bars_1min.len());

    // ── Precompute per-timeframe resampled bars + cached indicators ───────────
    // Built once and reused by both the full-sample grid search and the
    // per-window walk-forward optimisation.
    let mut tf_data: Vec<TfData> = Vec::with_capacity(TIMEFRAMES.len());
    for &tf_min in TIMEFRAMES {
        println!("\nTimeframe: {tf_min}-min");
        let t1 = Instant::now();
        let bars_tf = resample(&bars_1min, tf_min);
        println!("  {} bars  [{:.2}s]", bars_tf.len(), t1.elapsed().as_secs_f32());

        // Precompute all needed EMAs for this TF (cache by period)
        let unique_periods: Vec<usize> = {
            let mut v: Vec<usize> =
                FAST_EMAS.iter().chain(SLOW_EMAS.iter()).copied().collect();
            v.sort_unstable();
            v.dedup();
            v
        };
        let ema_cache: HashMap<usize, Vec<f64>> = unique_periods
            .iter()
            .map(|&p| (p, ema(&bars_tf, p)))
            .collect();
        let atr_vals = atr(&bars_tf, ATR_PERIOD);

        tf_data.push(TfData { tf_min, bars: bars_tf, ema_cache, atr: atr_vals });
    }

    // ── Full-sample grid search ───────────────────────────────────────────────
    let mut all_results: Vec<(Params, Metrics)> = Vec::new();
    for tf in &tf_data {
        let grid = build_grid(tf.tf_min);
        println!(
            "\nTimeframe {}-min: searching {} combinations (rayon parallel)...",
            tf.tf_min,
            grid.len()
        );
        let t2 = Instant::now();
        // i64::MIN..i64::MAX selects the whole resampled series.
        let results = search_range(tf, &grid, i64::MIN, i64::MAX);
        println!("  Done [{:.2}s]", t2.elapsed().as_secs_f32());
        all_results.extend(results);
    }

    // ── Write results.csv ─────────────────────────────────────────────────────
    println!("\nWriting outputs/results.csv...");
    {
        let mut wtr = csv::Writer::from_path("outputs/results.csv")
            .expect("Cannot create outputs/results.csv");
        wtr.write_record([
            "fast_ema", "slow_ema", "atr_stop_mult", "rr_ratio", "tf_min",
            "sharpe", "profit_factor", "max_drawdown_r", "total_return", "n_trades",
        ])
        .unwrap();
        for (p, m) in &all_results {
            wtr.write_record(&[
                p.fast_ema.to_string(),
                p.slow_ema.to_string(),
                format!("{:.2}", p.atr_stop_mult),
                format!("{:.1}", p.rr_ratio),
                p.tf_min.to_string(),
                format!("{:.6}", m.sharpe),
                format!("{:.6}", m.profit_factor),
                format!("{:.6}", m.max_drawdown_r),
                format!("{:.4}", m.total_return),
                m.n_trades.to_string(),
            ])
            .unwrap();
        }
        wtr.flush().unwrap();
    }
    println!("  {} rows written", all_results.len());

    // ── Sort by Sharpe, filter by min trades ──────────────────────────────────
    all_results.sort_by(|a, b| {
        b.1.sharpe
            .partial_cmp(&a.1.sharpe)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let valid: Vec<&(Params, Metrics)> = all_results
        .iter()
        .filter(|(_, m)| m.n_trades >= MIN_TRADES)
        .collect();

    // ── Print and save top-10 ─────────────────────────────────────────────────
    println!(
        "\nTop-10 (min {} trades, sorted by Sharpe):",
        MIN_TRADES
    );
    println!(
        "{:<6} {:<6} {:<6} {:<5} {:<5}  {:>8}  {:>8}  {:>8}  {:>8}  {:>7}",
        "fast", "slow", "atr_m", "rr", "tf",
        "sharpe", "pf", "max_dd_r", "tot_R", "trades"
    );

    let top10: Vec<serde_json::Value> = valid
        .iter()
        .take(10)
        .map(|(p, m)| {
            println!(
                "{:<6} {:<6} {:<6.1} {:<5.1} {:<5}  {:>8.4}  {:>8.4}  {:>8.4}  {:>8.2}  {:>7}",
                p.fast_ema, p.slow_ema, p.atr_stop_mult, p.rr_ratio, p.tf_min,
                m.sharpe, m.profit_factor, m.max_drawdown_r, m.total_return, m.n_trades
            );
            serde_json::json!({
                "fast_ema":       p.fast_ema,
                "slow_ema":       p.slow_ema,
                "atr_stop_mult":  p.atr_stop_mult,
                "rr_ratio":       p.rr_ratio,
                "tf_min":         p.tf_min,
                "sharpe":         m.sharpe,
                "profit_factor":  m.profit_factor,
                "max_drawdown_r": m.max_drawdown_r,
                "total_return":   m.total_return,
                "n_trades":       m.n_trades,
            })
        })
        .collect();

    let json_str = serde_json::to_string_pretty(&top10).expect("JSON serialisation failed");
    fs::write("outputs/top_params.json", &json_str).expect("Cannot write outputs/top_params.json");
    println!("\nSaved outputs/top_params.json");

    // ── Walk-forward optimisation ─────────────────────────────────────────────
    // Proper (non-anchored-selection) walk-forward: for each window we re-run
    // the full grid search on the IS slice ONLY, select the best IS parameter
    // set, then evaluate that exact set on the untouched OOS slice. No future
    // information leaks into parameter selection. Selected params are logged per
    // window so the protocol is auditable.
    println!("\nWalk-forward optimisation (IS-only grid search per window)...");

    // Anchored walk-forward windows: IS always starts at 2003; OOS steps 2 years
    let windows: &[(i32, i32, i32, i32)] = &[
        (2003, 2014, 2015, 2018),
        (2003, 2016, 2017, 2020),
        (2003, 2018, 2019, 2022),
        (2003, 2020, 2021, 2025),
    ];

    let mut wf_wtr = csv::Writer::from_path("outputs/walkforward.csv")
        .expect("Cannot create outputs/walkforward.csv");
    wf_wtr
        .write_record([
            "window", "is_start", "is_end", "oos_start", "oos_end",
            "sel_fast", "sel_slow", "sel_atr_mult", "sel_rr", "sel_tf",
            "is_sharpe", "is_pf", "is_n_trades",
            "oos_sharpe", "oos_pf", "oos_max_drawdown_r", "oos_n_trades",
        ])
        .unwrap();

    println!(
        "\n{:<4}  {:<12}  {:<12}  {:<20}  {:>8}  {:>8}  {:>8}  {:>7}",
        "win", "IS", "OOS", "selected", "IS-Sh", "OOS-Sh", "OOS-PF", "OOS-n"
    );

    for (idx, &(is_s, is_e, oos_s, oos_e)) in windows.iter().enumerate() {
        let is_start = year_start_ts(is_s);
        let is_end   = year_start_ts(is_e + 1);
        let oos_start = year_start_ts(oos_s);
        let oos_end   = year_start_ts(oos_e + 1);

        // 1) Grid-search the IS slice across every timeframe.
        let mut is_results: Vec<(Params, Metrics)> = Vec::new();
        for tf in &tf_data {
            let grid = build_grid(tf.tf_min);
            is_results.extend(search_range(tf, &grid, is_start, is_end));
        }

        // 2) Select the best IS parameter set (max Sharpe, ≥ MIN_TRADES).
        is_results.sort_by(|a, b| {
            b.1.sharpe
                .partial_cmp(&a.1.sharpe)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let selected = is_results
            .iter()
            .find(|(_, m)| m.n_trades >= MIN_TRADES);

        let (sel_params, is_m) = match selected {
            Some((p, m)) => (p.clone(), m.clone()),
            None => {
                println!("  Window {}: no valid IS combination — skipping.", idx + 1);
                continue;
            }
        };

        // 3) Evaluate the selected params on the OOS slice (no re-fitting).
        let tf = tf_data
            .iter()
            .find(|t| t.tf_min == sel_params.tf_min)
            .expect("selected tf must exist");
        let oos_m = eval_params(tf, &sel_params, oos_start, oos_end);

        println!(
            "{:<4}  {:<12}  {:<12}  {:<20}  {:>8.4}  {:>8.4}  {:>8.4}  {:>7}",
            idx + 1,
            format!("{}-{}", is_s, is_e),
            format!("{}-{}", oos_s, oos_e),
            format!(
                "{}/{} {:.1}× rr{:.1} {}m",
                sel_params.fast_ema, sel_params.slow_ema,
                sel_params.atr_stop_mult, sel_params.rr_ratio, sel_params.tf_min
            ),
            is_m.sharpe, oos_m.sharpe, oos_m.profit_factor, oos_m.n_trades
        );

        wf_wtr
            .write_record(&[
                (idx + 1).to_string(),
                is_s.to_string(), is_e.to_string(),
                oos_s.to_string(), oos_e.to_string(),
                sel_params.fast_ema.to_string(),
                sel_params.slow_ema.to_string(),
                format!("{:.2}", sel_params.atr_stop_mult),
                format!("{:.1}", sel_params.rr_ratio),
                sel_params.tf_min.to_string(),
                format!("{:.6}", is_m.sharpe),
                format!("{:.6}", is_m.profit_factor),
                is_m.n_trades.to_string(),
                format!("{:.6}", oos_m.sharpe),
                format!("{:.6}", oos_m.profit_factor),
                format!("{:.6}", oos_m.max_drawdown_r),
                oos_m.n_trades.to_string(),
            ])
            .unwrap();
    }
    wf_wtr.flush().unwrap();
    println!("\nSaved outputs/walkforward.csv");
    println!("\nTotal elapsed: {:.1}s", t0.elapsed().as_secs_f32());
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Resampled bars for one timeframe plus its cached indicator arrays.
/// Indicator vectors are aligned 1:1 with `bars` (same length / index).
struct TfData {
    tf_min: u32,
    bars: Vec<Bar>,
    ema_cache: HashMap<usize, Vec<f64>>,
    atr: Vec<f64>,
}

/// Build the parameter grid for a single timeframe, applying the
/// `slow_ema > fast_ema + 5` separation constraint.
fn build_grid(tf_min: u32) -> Vec<Params> {
    FAST_EMAS
        .iter()
        .flat_map(|&fast| {
            SLOW_EMAS
                .iter()
                .filter(move |&&slow| slow > fast + 5)
                .flat_map(move |&slow| {
                    ATR_MULTS.iter().flat_map(move |&atr_m| {
                        RR_RATIOS.iter().map(move |&rr| Params {
                            fast_ema: fast,
                            slow_ema: slow,
                            atr_stop_mult: atr_m,
                            rr_ratio: rr,
                            tf_min,
                        })
                    })
                })
        })
        .collect()
}

/// Run `grid` over the `[start_ts, end_ts)` slice of one timeframe's bars,
/// reusing the cached indicator arrays (sliced to the same index range).
/// `i64::MIN..i64::MAX` selects the whole series.
fn search_range(
    tf: &TfData,
    grid: &[Params],
    start_ts: i64,
    end_ts: i64,
) -> Vec<(Params, Metrics)> {
    let (s, e) = ts_range(&tf.bars, start_ts, end_ts);
    let bars = &tf.bars[s..e];
    let atr_v = &tf.atr[s..e];
    grid.par_iter()
        .map(|p| {
            let fast_v = &tf.ema_cache[&p.fast_ema][s..e];
            let slow_v = &tf.ema_cache[&p.slow_ema][s..e];
            let m = backtest(bars, fast_v, slow_v, atr_v, p);
            (p.clone(), m)
        })
        .collect()
}

/// Evaluate a single parameter set on the `[start_ts, end_ts)` slice.
fn eval_params(tf: &TfData, p: &Params, start_ts: i64, end_ts: i64) -> Metrics {
    let (s, e) = ts_range(&tf.bars, start_ts, end_ts);
    let bars = &tf.bars[s..e];
    let fast_v = &tf.ema_cache[&p.fast_ema][s..e];
    let slow_v = &tf.ema_cache[&p.slow_ema][s..e];
    let atr_v = &tf.atr[s..e];
    backtest(bars, fast_v, slow_v, atr_v, p)
}
