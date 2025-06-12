# Risk-Analytics Toolkit – Monte Carlo, Probability and Optimization in Python

**Risk-Analytics Toolkit** is a Python package that bundles three self-contained modules that quantify and mitigate cyber-risk:

| Module                 | What it solves                                                                                                                   | Techniques used                                                                                    |   |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | - |
| `risk_metrics.py`      | Computes annualized loss expectancy (ALE) from distributional inputs and Monte Carlo samples                                     | Triangular, log-normal and Pareto distributions, vectorized NumPy sampling, Monte Carlo estimation |   |
| `prob_model.py`        | Answers “what-if” questions on a two-phase security process, including conditional positives                                     | Joint probability tables, marginalization, Bayes rule                                              |   |
| `control_optimizer.py` | Learns how security controls affect safeguard effect and maintenance load, then finds the cheapest way to strengthen the network | Ordinary least squares, SciPy `linprog`                                                            |   |

Everything is pure Python 3 with minimal, widely available dependencies.

---

## Why this repo

* **End-to-end workflow** – from raw probability data to actionable control counts.
* **No black boxes** – every formula is implemented explicitly and heavily commented so you can trace the math line by line.
* **Reproducible outputs** – each module exposes a single top-level function (`Task1`, `Task2`, `Task3`) whose signature matches the public API shown below.

---

## Repository layout

```
risk-analytics/
├─ risk_metrics.py          # Task 1 – ALE via Monte Carlo
├─ prob_model.py            # Task 2 – conditional probabilities
├─ control_optimizer.py     # Task 3 – regression and LP
├─ examples/
│  ├─ demo_task1.py
│  ├─ demo_task2.py
│  └─ demo_task3.py
├─ requirements.txt
└─ README.md
```

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/<your-handle>/risk-analytics.git
cd risk-analytics
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # numpy, scipy, pandas, matplotlib

# 2. Run the canned examples
python examples/demo_task1.py
python examples/demo_task2.py
python examples/demo_task3.py
```

Each script prints intermediate steps and a final result so you can verify the logic quickly.

---

## Public API

```python
from risk_metrics import Task1
from prob_model import Task2
from control_optimizer import Task3
```

### Task 1 – ALE and Monte Carlo

```python
prob1, mean_t, median_t, mean_d, var_d, prob2, prob3, ale = Task1(
    a=1_000, b=20_000, c=8_000,           # triangular AV parameters
    point1=12_000,                        # Pr(AV ≤ point1)
    number_set=[0,1,2,3,4,5,6,7,8,9],     # discrete occurrence counts
    prob_set=[0.05,0.11,...,0.01],        # matching probabilities
    num=100_000,                          # Monte Carlo draws
    point2=25_000, point3=10_000, point4=20_000,
    mu=9.2, sigma=1.0,                    # log-normal for flaw A
    xm=5_000, alpha=2.5                  # Pareto for flaw B
)
```

### Task 2 – Two-phase screening

```python
prob1, prob2, prob3 = Task2(
    num=500,
    table=[[a,b,c,d], [e,f,g,h], [i,j,k,l]],  # 3×4 joint counts
    probs=[PX2,PX3,PX4,PX5,PY6,PY7]           # conditional T|X,Y
)
```

### Task 3 – Control optimization

```python
weights_b, weights_d, x_add = Task3(
    x=[[x11,x12,...,x15],  # 4×5 matrix of historical control counts
       ...],
    y=[y1,y2,y3,y4,y5],    # safeguard effects
    z=[z1,z2,z3,z4,z5],    # maintenance loads
    x_initial=[1,0,3,2],   # current deployment
    c=[c1,c2,c3,c4],       # unit costs
    x_bound=[nb1,nb2,nb3,nb4], # per-type upper limits
    se_bound=120, ml_bound=80
)
```

`x_add` is a float vector showing exactly how many extra controls to deploy per type.

---

## Implementation notes

* **Vectorization first** – NumPy and SciPy replace Python loops wherever possible for speed on large Monte Carlo runs.
* **Deterministic seeds** – examples fix `np.random.seed(42)` so your first run matches the README.
* **Clear separation** – math helpers (`_triangular_cdf`, `_long_name`) live in private functions to keep the top-level API clean.
* **Graceful fallbacks** – if SciPy’s `linprog` is missing, `control_optimizer.py` raises a descriptive error instead of crashing.

---

## Extending the toolkit

| Idea                         | Hint                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------ |
| **Risk correlations**        | Couple flaw A and flaw B with a copula instead of assuming independence.             |
| **Discrete-time simulation** | Replace analytical ALE with a time-stepped cash-flow model.                          |
| **Dashboard**                | Wrap the three tasks in a small Flask or Streamlit front end for interactive tuning. |

Pull requests are welcome – especially for unit tests, new distributions, or additional optimization constraints.

---
