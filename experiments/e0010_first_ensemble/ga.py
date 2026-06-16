"""Lightweight genetic algorithm for parameter search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


FitnessFn = Callable[[list[float]], float]


@dataclass
class GAConfig:
    population_size: int = 24
    generations: int = 12
    elite_count: int = 2
    tournament_size: int = 3
    mutation_rate: float = 0.15
    mutation_scale: float = 0.2
    seed: int = 42


@dataclass
class GAResult:
    best_genome: list[float]
    best_fitness: float
    history_best: list[float]


def _tournament_select(
    population: list[list[float]],
    fitnesses: list[float],
    rng: np.random.Generator,
    tournament_size: int,
) -> list[float]:
    indices = rng.integers(0, len(population), size=tournament_size)
    best_idx = max(indices, key=lambda i: fitnesses[i])
    return population[best_idx].copy()


def _crossover(
    parent_a: list[float],
    parent_b: list[float],
    rng: np.random.Generator,
) -> tuple[list[float], list[float]]:
    if len(parent_a) == 1:
        return parent_a.copy(), parent_b.copy()
    point = int(rng.integers(1, len(parent_a)))
    child_a = parent_a[:point] + parent_b[point:]
    child_b = parent_b[:point] + parent_a[point:]
    return child_a, child_b


def _mutate(genome: list[float], rng: np.random.Generator, rate: float, scale: float) -> list[float]:
    out = genome.copy()
    for i in range(len(out)):
        if rng.random() < rate:
            out[i] = float(np.clip(out[i] + rng.normal(0.0, scale), 0.0, 1.0))
    return out


def run_ga(
    fitness_fn: FitnessFn,
    genome_length: int,
    config: GAConfig,
    cache: dict[tuple[float, ...], float] | None = None,
) -> GAResult:
    """Evolve a population and return the best genome by train-set fitness."""
    rng = np.random.default_rng(config.seed)
    fitness_cache = cache if cache is not None else {}

    def score(genome: list[float]) -> float:
        key = tuple(round(g, 8) for g in genome)
        if key not in fitness_cache:
            fitness_cache[key] = float(fitness_fn(genome))
        return fitness_cache[key]

    population = [
        [float(rng.random()) for _ in range(genome_length)] for _ in range(config.population_size)
    ]
    fitnesses = [score(g) for g in population]
    history_best: list[float] = []

    for _ in range(config.generations):
        ranked = sorted(zip(population, fitnesses, strict=True), key=lambda x: x[1], reverse=True)
        population = [g.copy() for g, _ in ranked]
        fitnesses = [f for _, f in ranked]
        history_best.append(fitnesses[0])

        next_population = [g.copy() for g in population[: config.elite_count]]

        while len(next_population) < config.population_size:
            parent_a = _tournament_select(population, fitnesses, rng, config.tournament_size)
            parent_b = _tournament_select(population, fitnesses, rng, config.tournament_size)
            child_a, child_b = _crossover(parent_a, parent_b, rng)
            next_population.append(_mutate(child_a, rng, config.mutation_rate, config.mutation_scale))
            if len(next_population) < config.population_size:
                next_population.append(_mutate(child_b, rng, config.mutation_rate, config.mutation_scale))

        population = next_population
        fitnesses = [score(g) for g in population]

    best_idx = int(np.argmax(fitnesses))
    return GAResult(
        best_genome=population[best_idx],
        best_fitness=fitnesses[best_idx],
        history_best=history_best,
    )
