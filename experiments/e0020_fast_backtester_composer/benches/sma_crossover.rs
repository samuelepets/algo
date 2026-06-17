use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion};
use fast_backtester::{backtest, load_bars_continuous, DualSmaCrossover};

fn bench_sma_crossover_eurusd(c: &mut Criterion) {
    let bars = load_bars_continuous("EURUSD", None, None).expect("load EURUSD");
    let strategy = DualSmaCrossover::new(50, 200, 60);

    let mut group = c.benchmark_group("sma_crossover_eurusd");
    group.sample_size(10);

    group.bench_function("load_bars", |b| {
        b.iter(|| {
            black_box(load_bars_continuous("EURUSD", None, None).expect("load EURUSD"));
        });
    });

    group.bench_function("generate_signal", |b| {
        b.iter(|| {
            black_box(strategy.generate_signal(black_box(&bars)));
        });
    });

    let signal = strategy.generate_signal(&bars);
    group.bench_function("backtest", |b| {
        b.iter(|| {
            black_box(backtest(black_box(&bars), black_box(&signal), 0.0));
        });
    });

    group.bench_function("end_to_end", |b| {
        b.iter(|| {
            let bars = load_bars_continuous("EURUSD", None, None).expect("load EURUSD");
            let signal = strategy.generate_signal(&bars);
            black_box(backtest(&bars, &signal, 0.0));
        });
    });

    group.finish();
}

criterion_group!(benches, bench_sma_crossover_eurusd);
criterion_main!(benches);
