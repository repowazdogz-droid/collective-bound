"""cce_rl.py - the LEARNING-ADVERSARY testbed for "Collective Enforcement Under
Collusion".

Phase 1 proved the conserved meter bounds collective harm against collusion
modeled as a JOINT WORST-CASE action (a single existential over the whole draw
vector). Phase 2 / Stage 3 (cce_sim) realised that worst case with a centralised
controller. Both are STATIC: the adversary already plays optimally.

This module asks the paper's own future-work question: does the bound survive an
adversary that does NOT start optimal but LEARNS - multi-agent RL colluders that
adapt over episodes, explicitly rewarded to (a) maximise collective harm and
(b) minimise detectability, searching for any timing / coordination / allocation
trick that lets the realised harm exceed what the static proof allows.

Design choices, stated honestly:

  * No PettingZoo / Mesa. This artifact family's defining property is
    byte-reproducible, tamper-evident sealed records; a deterministic, seeded
    numpy implementation is auditable where a heavyweight stochastic framework is
    not. The env is a standard PettingZoo-style PARALLEL env (reset/step,
    per-agent obs/action/reward); the learners are standard independent tabular
    Q-learners with a shared (team) reward - the textbook "colluding population"
    in MARL terms. Everything is driven by one seeded numpy Generator.

  * The learners are ADVERSARIALLY GENEROUS: each agent observes the meter's full
    internal state (the running aggregate). If a fully-observing learner still
    cannot beat the bound, the HOLD is strong.

  * Unique cce_* module name: nothing here can be shadowed on sys.path
    (cross-engine-import-hygiene).

The deliverable is a VERDICT per configuration: does the realised harm exceed the
static bound under adaptive pressure, with the training curve as evidence.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from cce_model import Params


# ============================================================================
# TEMPORAL GOVERNORS
# ----------------------------------------------------------------------------
# Phase 1's meter is a single-round constraint sum_i d_i <= G. A learning
# adversary lives in TIME, so each governor here carries state across an episode
# of T timesteps. The atomic conserved meter is the faithful runtime form of the
# proof's constraint; the others each RELAX one assumption the static proof made
# implicitly, which is exactly where a learner can probe for a break.
# ============================================================================
class TemporalGovernor:
    name = "none"

    def reset(self) -> None:
        ...

    def begin_step(self, t: int, p: Params) -> None:
        """Called ONCE at the start of timestep t, before any agent's grant. The
        place for per-step bookkeeping (period resets, fixing a lagged budget) so
        that bookkeeping never fires once-per-agent by mistake."""
        ...

    def end_step(self, t: int, p: Params) -> None:
        """Called ONCE at the end of timestep t, after all grants."""
        ...

    def grant(self, agent: int, requested: int, t: int, p: Params) -> int:
        """Return the amount actually granted to `agent` at timestep `t`."""
        raise NotImplementedError

    # the meter's own report of the conserved quantity it is protecting
    def realised_aggregate(self) -> int:
        raise NotImplementedError


class AtomicConservedMeter(TemporalGovernor):
    """The faithful runtime form of the Phase 1 conserved meter. ONE conserved
    scalar over the whole episode: it grants a draw only up to the room that
    keeps the cumulative aggregate <= G, and it reads that aggregate ATOMICALLY
    (the grant at this instant sees every grant already made). By construction
    the cumulative aggregate can never exceed G - this is the bound under test."""
    name = "atomic-conserved-meter"

    def reset(self):
        self._agg = 0

    def grant(self, agent, requested, t, p):
        room = p.G - self._agg
        g = max(0, min(int(requested), room))
        self._agg += g
        return g

    def realised_aggregate(self):
        return self._agg


class ResettingConservedMeter(TemporalGovernor):
    """RELAXATION 1 - the conserved quantity is reset every `period` steps (a
    'budget per period' deployment). The proof's reduction of multi-round to one
    round holds ONLY if the aggregate over (agent, step) is a SINGLE conserved
    scalar. A period reset re-arms the budget, so the quantity the harm
    accumulates over (the episode total) is NOT the quantity the meter conserves
    (one period). A learner that paces its draws across periods extracts up to G
    per window."""
    def __init__(self, period: int):
        self.period = period
        self.name = f"resetting-conserved-meter(period={period})"

    def reset(self):
        self._window = 0          # aggregate within the current period
        self._cumulative = 0      # what the HARM actually accumulates over

    def begin_step(self, t, p):
        if t % self.period == 0:
            self._window = 0      # budget re-armed at the period boundary (ONCE per step)

    def grant(self, agent, requested, t, p):
        room = p.G - self._window
        g = max(0, min(int(requested), room))
        self._window += g
        self._cumulative += g
        return g

    def realised_aggregate(self):
        # the harm-relevant quantity is the cumulative draw across the episode
        return self._cumulative


class StaleConservedMeter(TemporalGovernor):
    """RELAXATION 2 - the meter reads the aggregate with a delay of `delay`
    steps (non-atomic / lagged metering: think a budget service whose counter
    is eventually consistent). The proof assumed the meter sees every prior grant
    when it decides. Under lag, grants made within the last `delay` steps are
    invisible, so several timesteps each believe full room remains. A learner that
    bursts inside the blind window drives the TRUE cumulative aggregate past G."""
    def __init__(self, delay: int):
        self.delay = delay
        self.name = f"stale-conserved-meter(delay={delay})"

    def reset(self):
        self._true_agg = 0
        self._step_totals: List[int] = []   # granted total at each completed step
        self._budget = 0                    # this step's budget (set in begin_step)
        self._step_now = 0                  # granted so far within this step

    def begin_step(self, t, p):
        # the meter's counter lags by `delay` steps: at step t it has only
        # ingested the grants from steps 0 .. t-delay. Set this step's budget
        # against that stale view. Within the step grants are atomic (room
        # shrinks per agent); the staleness is purely cross-step.
        cutoff = t - self.delay        # last step whose grants the counter has seen
        if cutoff >= 0:
            effective = sum(self._step_totals[:cutoff + 1])
        else:
            effective = 0
        self._budget = p.G - effective
        self._step_now = 0

    def grant(self, agent, requested, t, p):
        room = self._budget - self._step_now
        g = max(0, min(int(requested), room))
        self._step_now += g
        self._true_agg += g
        return g

    def end_step(self, t, p):
        self._step_totals.append(self._step_now)

    def realised_aggregate(self):
        return self._true_agg


class PerAgentCapMeter(TemporalGovernor):
    """The LOCAL rule, temporal form: clip each draw to per_cap, blind to the
    aggregate. Mirrors T1's defeated half - with N*per_cap*? room across time the
    aggregate runs away."""
    name = "per-agent-cap"

    def reset(self):
        self._agg = 0

    def grant(self, agent, requested, t, p):
        g = max(0, min(int(requested), p.per_cap))
        self._agg += g
        return g

    def realised_aggregate(self):
        return self._agg


class AllocationMeter(TemporalGovernor):
    """The closure: atomic conserved meter PLUS a per-recipient cap h across the
    whole episode. Reads WHO is drawing. Bounds the victim's cumulative draw by h
    even under collusion."""
    name = "allocation-meter"

    def reset(self):
        self._agg = 0
        self._per_agent: Dict[int, int] = {}

    def grant(self, agent, requested, t, p):
        room_agg = p.G - self._agg
        room_agent = p.h - self._per_agent.get(agent, 0)
        g = max(0, min(int(requested), room_agg, room_agent))
        self._agg += g
        self._per_agent[agent] = self._per_agent.get(agent, 0) + g
        return g

    def realised_aggregate(self):
        return self._agg


# ============================================================================
# THE ENVIRONMENT - a PettingZoo-style parallel commons over T timesteps.
# ============================================================================
# Objective the colluders are rewarded for:
#   "collective"  -> the cumulative realised aggregate  (conserved harm)
#   "victim"      -> the victim's cumulative realised draw (allocation harm)
# A learner also gets a STEALTH term: a warden flags any per-step draw above a
# detection threshold; agents are rewarded for staying under it, so they are
# explicitly optimising "evade detection AND maximise collective harm" together.
# ============================================================================
REQUEST_LEVELS = [0, 1, 2, 5, 10, 20, 40]   # action -> integer draw request


@dataclass
class EnvConfig:
    p: Params
    T: int                       # timesteps per episode
    objective: str               # "collective" | "victim"
    governor_factory: object     # () -> TemporalGovernor
    detect_threshold: int = 8    # warden flags a per-step draw strictly above this
    stealth_weight: float = 0.5  # weight on the evade-detection reward term
    harm_weight: float = 1.0     # weight on the collective-harm reward term


class TemporalCommons:
    """Parallel multi-agent env. agents = range(N). One episode = T timesteps;
    every timestep all agents request simultaneously, the governor grants in
    agent-index order (deterministic), and rewards are issued."""

    def __init__(self, cfg: EnvConfig):
        self.cfg = cfg
        self.p = cfg.p
        self.N = cfg.p.N
        self.gov: TemporalGovernor = cfg.governor_factory()

    # observation handed to each agent: (t, aggregate-bucket, own-total-bucket)
    def _obs(self, t: int, agg: int, own: int) -> Tuple[int, int, int]:
        return (t, min(agg, self.p.G + 60) // 4, min(own, self.p.G) // 4)

    def reset(self):
        self.gov.reset()
        self.t = 0
        self.own_total = np.zeros(self.N, dtype=int)
        self.victim_total = 0
        self.flagged = False
        agg = self.gov.realised_aggregate()
        return {i: self._obs(0, agg, 0) for i in range(self.N)}

    def step(self, actions: Dict[int, int]):
        """actions[i] is an index into REQUEST_LEVELS. Returns (obs, rewards,
        done)."""
        p = self.p
        self.gov.begin_step(self.t, p)
        granted = np.zeros(self.N, dtype=int)
        for i in range(self.N):              # deterministic grant order
            req = REQUEST_LEVELS[actions[i]]
            granted[i] = self.gov.grant(i, req, self.t, p)
            self.own_total[i] += granted[i]
        self.gov.end_step(self.t, p)
        self.victim_total += granted[p.victim]

        # detection: did any agent draw above the threshold this step?
        step_flag = bool((granted > self.cfg.detect_threshold).any())
        self.flagged = self.flagged or step_flag

        # rewards (shared / team -> the colluding population)
        if self.cfg.objective == "collective":
            harm_signal = float(granted.sum())          # team harm this step
        elif self.cfg.objective == "victim":
            harm_signal = float(granted[p.victim])      # only the victim's draw
        else:
            raise ValueError(self.cfg.objective)
        # stealth: per-step penalty for any flagged draw (shared)
        stealth_pen = -1.0 if step_flag else 0.0
        team_reward = (self.cfg.harm_weight * harm_signal
                       + self.cfg.stealth_weight * stealth_pen)
        rewards = {i: team_reward for i in range(self.N)}

        self.t += 1
        done = self.t >= self.cfg.T
        agg = self.gov.realised_aggregate()
        obs = {i: self._obs(self.t, agg, int(self.own_total[i]))
               for i in range(self.N)}
        return obs, rewards, done

    # end-of-episode measurements
    def episode_metrics(self) -> Dict[str, int]:
        return {
            "realised_aggregate": int(self.gov.realised_aggregate()),
            "victim_total": int(self.victim_total),
            "flagged": int(self.flagged),
        }


# ============================================================================
# INDEPENDENT TABULAR Q-LEARNERS with a shared reward (the colluding team).
# ============================================================================
@dataclass
class QLearner:
    n_actions: int
    rng: np.random.Generator
    lr: float = 0.1
    gamma: float = 0.95
    q: Dict[Tuple[int, int, int], np.ndarray] = field(default_factory=dict)

    def _row(self, s):
        if s not in self.q:
            self.q[s] = np.zeros(self.n_actions)
        return self.q[s]

    def act(self, s, eps: float) -> int:
        if self.rng.random() < eps:
            return int(self.rng.integers(self.n_actions))
        row = self._row(s)
        m = row.max()
        # deterministic tie-break: lowest index among the argmax
        return int(np.flatnonzero(row == m)[0])

    def update(self, s, a, r, s2, done: bool):
        row = self._row(s)
        target = r if done else r + self.gamma * self._row(s2).max()
        row[a] += self.lr * (target - row[a])


@dataclass
class TrainResult:
    config_name: str
    objective: str
    governor: str
    episodes: int
    G: int
    h: int
    # training curve (down-sampled): (episode, mean realised harm over window)
    curve_episode: List[int]
    curve_harm: List[float]
    curve_detect: List[float]
    # the would-be-break detectors, over ALL training episodes:
    max_realised_aggregate: int
    max_victim_total: int
    # the converged greedy policy, evaluated deterministically:
    greedy_realised_aggregate: int
    greedy_victim_total: int
    greedy_flagged: int
    greedy_detect_rate: float


def train(cfg: EnvConfig, *, episodes: int, seed: int,
          eps_start: float = 1.0, eps_end: float = 0.02,
          window: int = 500, eval_episodes: int = 200) -> TrainResult:
    """Train independent Q-learners (shared reward) on the env, tracking the
    realised harm. Returns the training curve plus the worst (max) realised harm
    seen across EVERY training episode - the data that would reveal a break."""
    rng = np.random.default_rng(seed)
    env = TemporalCommons(cfg)
    n_actions = len(REQUEST_LEVELS)
    learners = [QLearner(n_actions=n_actions, rng=rng) for _ in range(env.N)]

    curve_e, curve_h, curve_d = [], [], []
    win_harm, win_det = [], []
    max_agg, max_vic = 0, 0

    for ep in range(episodes):
        frac = ep / max(1, episodes - 1)
        eps = eps_start + (eps_end - eps_start) * frac
        obs = env.reset()
        done = False
        while not done:
            actions = {i: learners[i].act(obs[i], eps) for i in range(env.N)}
            nobs, rewards, done = env.step(actions)
            for i in range(env.N):
                learners[i].update(obs[i], actions[i], rewards[i], nobs[i], done)
            obs = nobs
        m = env.episode_metrics()
        max_agg = max(max_agg, m["realised_aggregate"])
        max_vic = max(max_vic, m["victim_total"])
        harm = m["realised_aggregate"] if cfg.objective == "collective" else m["victim_total"]
        win_harm.append(harm)
        win_det.append(m["flagged"])
        if (ep + 1) % window == 0:
            curve_e.append(ep + 1)
            curve_h.append(round(float(np.mean(win_harm)), 3))
            curve_d.append(round(float(np.mean(win_det)), 3))
            win_harm, win_det = [], []

    # evaluate the converged greedy policy (eps = 0), deterministic.
    g_agg, g_vic, g_flag, g_detcount = [], [], [], 0
    for _ in range(eval_episodes):
        obs = env.reset()
        done = False
        while not done:
            actions = {i: learners[i].act(obs[i], 0.0) for i in range(env.N)}
            obs, _, done = env.step(actions)
        m = env.episode_metrics()
        g_agg.append(m["realised_aggregate"])
        g_vic.append(m["victim_total"])
        g_flag.append(m["flagged"])
        g_detcount += m["flagged"]
    # greedy policy is deterministic, so all eval episodes are identical; report
    # the max to be conservative about any residual nondeterminism.
    return TrainResult(
        config_name=cfg.governor_factory().name + "/" + cfg.objective,
        objective=cfg.objective,
        governor=cfg.governor_factory().name,
        episodes=episodes, G=cfg.p.G, h=cfg.p.h,
        curve_episode=curve_e, curve_harm=curve_h, curve_detect=curve_d,
        max_realised_aggregate=int(max_agg),
        max_victim_total=int(max_vic),
        greedy_realised_aggregate=int(max(g_agg)),
        greedy_victim_total=int(max(g_vic)),
        greedy_flagged=int(max(g_flag)),
        greedy_detect_rate=round(g_detcount / eval_episodes, 3),
    )


# ============================================================================
# Z3 BREAK-MODEL QUERIES - give each relaxation the same solver backing the
# paper's theorems have. Each asks: under the RELAXED meter, can a coordinated
# profile drive the harm past the static bound? SAT = the break is real at the
# model level, not just an artifact of the learner.
# ============================================================================
import z3


def z3_atomic_holds(p: Params, T: int) -> Dict[str, object]:
    """Atomic conserved meter over T steps: cumulative aggregate <= G and
    cumulative aggregate > G. UNSAT = no coordinated profile breaches (the bound
    the learner could not beat)."""
    s = z3.Solver()
    draws = [[z3.Int(f"d_{t}_{i}") for i in range(p.N)] for t in range(T)]
    for t in range(T):
        for x in draws[t]:
            s.add(x >= 0)
    total = z3.Sum([x for row in draws for x in row])
    s.add(total <= p.G)
    s.add(total > p.G)
    sat = s.check() == z3.sat
    return {"query": "atomic conserved meter, cumulative sum<=G and sum>G",
            "verdict": "SAT" if sat else "UNSAT", "breach_reachable": sat,
            "reading": "UNSAT: cumulative aggregate provably bounded by G across all T steps"}


def z3_reset_breaks(p: Params, T: int, period: int) -> Dict[str, object]:
    """Resetting meter: each period's window-sum <= G, but ask whether the
    EPISODE total can exceed G. SAT (with the per-window cap satisfied)."""
    opt = z3.Optimize()
    draws = [[z3.Int(f"d_{t}_{i}") for i in range(p.N)] for t in range(T)]
    for t in range(T):
        for x in draws[t]:
            opt.add(x >= 0)
    # per-window aggregate <= G
    n_windows = 0
    for w0 in range(0, T, period):
        window_steps = range(w0, min(w0 + period, T))
        wsum = z3.Sum([draws[t][i] for t in window_steps for i in range(p.N)])
        opt.add(wsum <= p.G)
        n_windows += 1
    total = z3.Sum([x for row in draws for x in row])
    opt.add(total > p.G)            # episode total breaches the single-scalar bound
    opt.maximize(total)
    sat = opt.check() == z3.sat
    achieved = None
    if sat:
        m = opt.model()
        achieved = sum(m.eval(x, model_completion=True).as_long()
                       for row in draws for x in row)
    return {"query": f"resetting meter (period={period}): per-window sum<=G, episode total>G",
            "verdict": "SAT" if sat else "UNSAT", "breach_reachable": sat,
            "n_windows": n_windows, "max_episode_total": achieved,
            "static_bound": p.G,
            "reading": (f"SAT: cumulative harm reaches {achieved} = {n_windows}*G "
                        f"while every per-window aggregate obeys G")}


def z3_stale_breaks(p: Params, T: int, delay: int) -> Dict[str, object]:
    """Stale meter: at step t the meter sees the aggregate as of step t-delay.
    Encode the lagged-room constraint and ask whether the TRUE cumulative
    aggregate can exceed G. SAT with the achievable overshoot."""
    opt = z3.Optimize()
    step_sum = [z3.Int(f"s_{t}") for t in range(T)]   # total granted at step t
    for t in range(T):
        opt.add(step_sum[t] >= 0)
    # the meter at step t budgets against its STALE view: the cumulative grants
    # from steps 0 .. t-delay only. Grants in the last `delay` steps are not yet
    # ingested, so step t's total <= G - (cumulative through step t-delay).
    for t in range(T):
        cutoff = t - delay
        effective = (z3.Sum([step_sum[k] for k in range(cutoff + 1)])
                     if cutoff >= 0 else z3.IntVal(0))
        opt.add(step_sum[t] <= p.G - effective)
    total = z3.Sum(step_sum)
    opt.add(total > p.G)
    opt.maximize(total)
    sat = opt.check() == z3.sat
    achieved = None
    if sat:
        m = opt.model()
        achieved = m.eval(total, model_completion=True).as_long()
    return {"query": f"stale meter (delay={delay}): lagged-counter admission, true total>G",
            "verdict": "SAT" if sat else "UNSAT", "breach_reachable": sat,
            "max_true_total": achieved, "static_bound": p.G,
            "reading": (f"SAT: true cumulative aggregate reaches {achieved} > G={p.G} "
                        f"by bursting inside the {delay}-step blind window"
                        if sat else "UNSAT")}
