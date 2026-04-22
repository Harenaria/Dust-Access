# Dust Access Simulator

<div align="center">

**A comprehensive game simulator and balance analysis toolkit for the Expandable Card Game (ECG) Dust Access**

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blue)](https://python-poetry.org/)

</div>

---

## Overview

**Dust Access Simulator** is a full-featured game engine and analysis suite for *Dust Access*, an Expandable Card Game (ECG). Unlike TCGs, ECGs distribute cards in fixed sets rather than randomized boosters—making rigorous balance validation essential.

This project provides:

- **Complete Game Engine** — A faithful implementation of *Dust Access* rules, managing decks, players, effects, combat, and turn phases.
- **DAMA: AI-Powered Balance Testing** — An advanced SO-ISMCTS (Single-Observer Information Set Monte Carlo Tree Search) agent for automated meta-game analysis.
- **Multiplayer Support** — WebSocket-based client-server architecture for online play.
- **Modern GUI Client** — A rich, interactive interface built with [Flet](https://flet.dev/).

---

## Project Structure

```
dust-access-simulator/
├── core/               # Game engine (client-agnostic)
├── DAMA/               # AI balance analysis tool (SO-ISMCTS)
├── networking/         # Multiplayer infrastructure (WebSocket)
├── client_views/       # GUI client (Flet)
├── data/               # Game data (CSV card database)
├── docs/               # Documentation
└── bin/                # Entry point scripts
```

---

## Installation

### Prerequisites

- **Python 3.13+**
- **Poetry** (dependency management)

### Setup

```bash
# Clone the repository
git clone https://github.com/MariaGratiaPlena/Dust-Access-Simulator.git
cd Dust-Access-Simulator

# Install dependencies
poetry lock
poetry install
```

---

## Quick Start

### Run the AI Simulator (DAMA)

Perform automated balance analysis using the SO-ISMCTS agent:

```bash
poetry run simulator
```

### Start the Multiplayer Server

Launch the WebSocket server for online play:

```bash
poetry run server
```

### Launch the Game Client

Start the Flet GUI client:

```bash
poetry run client
```

### Run All Components

Start server and client together:

```bash
poetry run run-all
```

---

## DAMA

DAMA (**D**ust **A**ccess **M**eta-game **A**nalysis) uses **Single-Observer Information Set Monte Carlo Tree Search (SO-ISMCTS)** to simulate high-level strategic play. This allows detection of:

- **Dominant strategies** before human playtesting
- **Card efficiency imbalances** within structure decks
- **Skill-dependent cards** (Skill Spikes vs Noob Stompers)

### Stratified Testing Tiers

| Tier            | Iterations | Purpose                                                  |
|:----------------|:-----------|:---------------------------------------------------------|
| **Casual**      | 100        | Detect greedy-dominant strategies and punisher mechanics |
| **Tactical**    | 500        | Evaluate multi-turn planning and resource management     |
| **Competitive** | 1000       | Identify structural flaws and equilibrium states         |

For full technical details, see [DAMA/README.md](DAMA/README.md).

---

## Game Mechanics Overview

*Dust Access* features several unique mechanics modeled by this simulator. For a complete rulebook, see [docs/rules.md](docs/rules.md).

### Core Concepts

- **Direct Combat** — Players ("Accessors") fight directly rather than through creatures.
- **Dual Action Economy** — Each turn provides one *Combat Action* (attacks) and one *Tactical Action* (skills, equipment, abilities).
- **Equipment Slots** — Rigid slot system: Weapon, Off-Hand, Head, Chest, Arms, Legs.
- **Level Scaling** — Player level increases each turn (max 10), gating cards by level requirement instead than resources.

### Key Statistics

| Stat            | Description                                            |
|:----------------|:-------------------------------------------------------|
| **Power**       | Offensive strength; influences weapon and skill damage |
| **Tenacity**    | Armor value subtracted from incoming damage            |
| **Durability**  | Maximum HP; increases by 10 each turn until level 5    |
| **Efficiency**  | Amplifies skill effectiveness                          |
| **Sensitivity** | Amplifies healing capabilities                         |

---

## Technology Stack

| Component       | Technology                       |
|:----------------|:---------------------------------|
| Core Engine     | Pure Python, dataclasses         |
| Data Management | Pandas (CSV parsing)             |
| AI / MCTS       | Custom SO-ISMCTS with UCT + RAVE |
| Networking      | `websockets`                     |
| GUI             | [Flet](https://flet.dev/)        |
| Visualization   | Matplotlib, Seaborn, Plotly      |

---

## Development

### Guidelines and Rules

- Game logic resides in `core/` and must remain client-agnostic.
- Network protocol uses JSON serialization via `core/serialization.py`.
- Card effects are declarative and parsed from CSV data.
- **GenAI usage in code generation is permitted** for both fast prototyping and code revision, but it must be **revised by a human** before being committed to the repository if it is not self-explanatory. 
- The repository owner reserves the right to grant the permit of delaying the revision of the code generated by AI to a future date if the code works as expected or if it's required to get the prototype out as soon as possible for any reason. However, it still is required to be revised by a human before being pushed to the main branch.
- If GenAI is used for vibe-coding, it is suggested to completely rewrite from scratch the drafted code if possible, especially for complex classes and components like the GUI. Usually this helps the revision process.
- **GenAI MUST NOT be used in asset generation or in any task regarding the card game's artistic content as a whole (e.g., card art, flavor text, simulator GUI assets etc.). This rule is absolute and non-negotiable, and it is not subject to ANY exception.**

---

## License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

```
Copyright 2025 Dust Access ECG Team
```

---

## Acknowledgments

- MCTS implementation based on [Cowling et al., 2012](https://ieeexplore.ieee.org/document/6203567/) (Information Set MCTS)
- [Browne et al., 2012](https://ieeexplore.ieee.org/document/6145622/) — A Survey of Monte Carlo Tree Search Methods