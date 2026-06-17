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

    // ── Grid search ───────────────────────────────────────────────────────────
    let mut all_results: Vec<(Params, Metrics)> = Vec::new();

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

        // Build grid (respecting slow > fast + 5 constraint)
        let grid: Vec<Params> = FAST_EMAS
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
            .collect();

        println!("  Searching {} combinations (rayon parallel)...", grid.len());
        let t2 = Instant::now();

        let results: Vec<(Params, Metrics)> = grid
            .into_par_iter()
            .map(|params| {
                let fast_v = &ema_cache[&params.fast_ema];
                let slow_v = &ema_cache[&params.slow_ema];
                let m = backtest(&bars_tf, fast_v, slow_v, &atr_vals, &params);
                (params, m)
            })
            .collect();

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
            "sharpe", "profit_factor", "max_drawdown", "total_return", "n_trades",
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
                format!("{:.6}", m.max_drawdown),
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
        "sharpe", "pf", "max_dd", "tot_R", "trades"
    );

    let top10: Vec<serde_json::Value> = valid
        .iter()
        .take(10)
        .map(|(p, m)| {
            println!(
                "{:<6} {:<6} {:<6.1} {:<5.1} {:<5}  {:>8.4}  {:>8.4}  {:>8.4}  {:>8.2}  {:>7}",
                p.fast_ema, p.slow_ema, p.atr_stop_mult, p.rr_ratio, p.tf_min,
                m.sharpe, m.profit_factor, m.max_drawdown, m.total_return, m.n_trades
            );
            serde_json::json!({
                "fast_ema":      p.fast_ema,
                "slow_ema":      p.slow_ema,
                "atr_stop_mult": p.atr_stop_mult,
                "rr_ratio":      p.rr_ratio,
                "tf_min":        p.tf_min,
                "sharpe":        m.sharpe,
                "profit_factor": m.profit_factor,
                "max_drawdown":  m.max_drawdown,
                "total_return":  m.total_return,
                "n_trades":      m.n_trades,
            })
        })
        .collect();

    let json_str = serde_json::to_string_pretty(&top10).expect("JSON serialisation failed");
    fs::write("outputs/top_params.json", &json_str).expect("Cannot write outputs/top_params.json");
    println!("\nSaved outputs/top_params.json");

    // ── Walk-forward validation ───────────────────────────────────────────────
    if valid.is_empty() {
        println!("\nNo valid combinations found — skipping walk-forward.");
        return;
    }

    let (best_params, _) = valid[0];
    println!(
        "\nWalk-forward: fast={} slow={} atr_m={:.1} rr={:.1} tf={}min",
        best_params.fast_ema, best_params.slow_ema,
        best_params.atr_stop_mult, best_params.rr_ratio, best_params.tf_min
    );

    // Resampled bars + indicators for the best TF
    let wf_bars = resample(&bars_1min, best_params.tf_min);
    let wf_fast = ema(&wf_bars, best_params.fast_ema);
    let wf_slow = ema(&wf_bars, best_params.slow_ema);
    let wf_atr  = atr(&wf_bars, ATR_PERIOD);

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
            "is_sharpe", "is_pf", "is_n_trades",
            "oos_sharpe", "oos_pf", "oos_max_dd", "oos_n_trades",
        ])
        .unwrap();

    println!(
        "\n{:<6}  {:<12}  {:<12}  {:>8}  {:>8}  {:>8}  {:>8}",
        "win", "IS", "OOS", "IS-Sh", "OOS-Sh", "OOS-PF", "OOS-n"
    );

    for (idx, &(is_s, is_e, oos_s, oos_e)) in windows.iter().enumerate() {
        let (is_bars, is_fast, is_slow, is_atr_v) = slice_window(
            &wf_bars, &wf_fast, &wf_slow, &wf_atr,
            year_start_ts(is_s), year_start_ts(is_e + 1),
        );
        let (oos_bars, oos_fast, oos_slow, oos_atr_v) = slice_window(
            &wf_bars, &wf_fast, &wf_slow, &wf_atr,
            year_start_ts(oos_s), year_start_ts(oos_e + 1),
        );

        let is_m  = backtest(&is_bars,  &is_fast,  &is_slow,  &is_atr_v,  best_params);
        let oos_m = backtest(&oos_bars, &oos_fast, &oos_slow, &oos_atr_v, best_params);

        println!(
            "{:<6}  {:<12}  {:<12}  {:>8.4}  {:>8.4}  {:>8.4}  {:>8}",
            idx + 1,
            format!("{}-{}", is_s, is_e),
            format!("{}-{}", oos_s, oos_e),
            is_m.sharpe, oos_m.sharpe, oos_m.profit_factor, oos_m.n_trades
        );

        wf_wtr
            .write_record(&[
                (idx + 1).to_string(),
                is_s.to_string(), is_e.to_string(),
                oos_s.to_string(), oos_e.to_string(),
                format!("{:.6}", is_m.sharpe),
                format!("{:.6}", is_m.profit_factor),
                is_m.n_trades.to_string(),
                format!("{:.6}", oos_m.sharpe),
                format!("{:.6}", oos_m.profit_factor),
                format!("{:.6}", oos_m.max_drawdown),
                oos_m.n_trades.to_string(),
            ])
            .unwrap();
    }
    wf_wtr.flush().unwrap();
    println!("\nSaved outputs/walkforward.csv");
    println!("\nTotal elapsed: {:.1}s", t0.elapsed().as_secs_f32());
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Extract a contiguous slice of bars (and their pre-computed indicator arrays)
/// within the time range `[start_ts, end_ts)`.
fn slice_window(
    bars:    &[Bar],
    fast:    &[f64],
    slow:    &[f64],
    atr_v:  &[f64],
    start_ts: i64,
    end_ts:   i64,
) -> (Vec<Bar>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let (s, e) = ts_range(bars, start_ts, end_ts);
    (
        bars[s..e].to_vec(),
        fast[s..e].to_vec(),
        slow[s..e].to_vec(),
        atr_v[s..e].to_vec(),
    )
}
