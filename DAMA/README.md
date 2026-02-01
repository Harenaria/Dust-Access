# DAMA: Dust Access Meta-Game Analysis tool
## Static and Dynamic Balance Validation via Information Set Monte Carlo Tree Search

DAMA (Dust Access Meta-Game Analysis) is a tool designed for the formal verification and stress-testing of game balance within the **Dust Access** Expandable Card Game (ECG) ecosystem. By employing advanced stochastic search algorithms (SO-ISMCTS), DAMA simulates high-level strategic interactions to identify emergent imbalances and non-trivial dominant strategies of the structure decks before the intervention of human playtesters, in order to avoid resource waste.

## Run the tool
~~~
poetry lock
poetry install
poetry run simulator
~~~

## Theoretical Framework
### Monte Carlo Tree Search (MCTS)
The core decision-making engine of DAMA is based on the **Monte Carlo Tree Search (MCTS)** paradigm, a best-first search algorithm specifically suited for domains with vast state spaces where a reliable static evaluation function is unavailable. As established in contemporary literature, the search process progresses through the iterative execution of four fundamental phases:

1.  **Selection**: Navigating from the root node to a leaf node by recursively applying a selection policy that balances exploitation of high-reward branches and exploration of uncertain frontiers.
2.  **Expansion**: Appending one or more child nodes to the search frontier, representing previously unexplored legal transitions within the game's state space.
3.  **Simulation (Monotonic Rollout)**: Executing a rapid playout from the newly expanded state to a terminal condition (win/loss/draw), providing a noisy estimate of the node's theoretical value.
4.  **Backpropagation**: Propagating the final outcome upstream through the traversed path, updating the statistical distribution (visit count $n$ and cumulative reward $w$) for all ancestor nodes.

#### Selection Policy: UCT with RAVE Blending
DAMA utilizes the **Upper Confidence Bound applied to Trees (UCT)** combined with **Rapid Action Value Estimation (RAVE)** as its selection mechanism:

$$UCT_{RAVE} = (1-\beta)\bar{X}_j + \beta \cdot AMAF_j + C_p \sqrt{\frac{2 \ln n}{n_j}}$$

where:
*   $\bar{X}_j$ is the empirical mean reward of node $j$
*   $AMAF_j$ is the All-Moves-As-First heuristic value (see RAVE section)
*   $\beta$ is the dynamic blending factor that decays as visit counts increase
*   $n$ is the parent's visit count, $n_j$ is the node's visit count
*   $C_p = 0.7$ is the exploration coefficient

The exploration coefficient is tuned below the theoretical $\sqrt{2}$ following established practice for heuristic-augmented MCTS (Browne et al., 2012). Studies on card games with imperfect information suggest lower $C_p$ values when strong priors are available (Gelly & Silver, 2011). We use $C_p = 0.7$ as a balance: lower than $\sqrt{2}$ due to RAVE and `HeuristicAnalyzer` priors, but higher than values used in simpler card games (e.g., Hearts) to account for ECG strategic depth.

---

### Advanced Algorithmic Extensions for Incomplete Information

Traditional MCTS assumes perfect information. To address the latent variables inherent in card games (e.g., hidden hands and deck ordering), DAMA implements the **Single-Observer Information Set MCTS (SO-ISMCTS)** variant.

#### Information Set Topology (ISMCTS)
Rather than operating on individual game states, the algorithm operates over **Information Sets**, collections of states that are indistinguishable to the acting agent. This prevents the "cheating" bias prevalent in standard MCTS and ensures the agent's decisions are based strictly on observable data and statistical inference.

#### Determinization and Information Consistency
Search iterations utilize **Determinization**, wherein hidden state variables are instantiated by sampling from the distribution of unknown cards. DAMA incorporates an **Information Consistency Lock**: known entities (such as the observer's hand and activated choice candidates) are excluded from the permutation process, ensuring that all explored trajectories are topologically consistent with the actual game state.

#### RAVE and Rapid Strategic Convergence
To mitigate the "cold start" problem in deep search trees, DAMA integrates **Rapid Action Value Estimation (RAVE)**. RAVE leverages the "All-Moves-As-First" (AMAF) heuristic, allowing the agent to generalize the value of a move across different branches of the tree.
*   **Dynamic Beta Weighting**: A non-linear blending factor $\beta$ is employed to transition from RAVE-dominant estimates (high bias/low variance) to UCT-pure estimates (low bias/high variance) as the sample size increases.

#### Heuristic-Augmented Rollouts
To improve the fidelity of the simulation phase, DAMA replaces uniform random playouts with a **Heuristic-Driven Policy** (`HeuristicAnalyzer`). This localized optimization avoids degenerate game states (e.g., missed lethal opportunities) and adapts with the strategy suggested by the deck, resulting in a more accurate value estimation and faster convergence to optimal play.

---

### Analytical Methodology and Stratification

Evaluation is conducted across three discrete search tiers to isolate specific classes of game-theoretic phenomena:

| Tier                       | Iterations | Research Objective                                                                              |
|:---------------------------|:-----------|:------------------------------------------------------------------------------------------------|
| **Heuristic/Casual**       | 100        | **Early Convergence.** Detection of "Greedy-Dominant" strategies and punisher mechanics.        |
| **Intermediate/Tactical**  | 500        | **Multi-Turn Planning.** Evaluation of standard efficiency and resource management.             |
| **Asymptotic/Competitive** | 1000       | **Equilibrium Analysis.** Identification of structural flaws and high-ceiling strategic spikes. |

---

## References and Formal Literature

*   **Original ISMCTS Framework**: Cowling, P. I., Powley, E. J., & Whitehouse, D. (2012). *Information Set Monte Carlo Tree Search*. IEEE Transactions on Computational Intelligence and AI in Games. [Link to Paper](https://ieeexplore.ieee.org/document/6203567/)
*   **Search Principles**: Browne, C. B., et al. (2012). *A Survey of Monte Carlo Tree Search Methods*. IEEE Transactions on Computational Intelligence and AI in Games.
*   **Implementation Manifest**: Technical details regarding RAVE and UCT calibration can be found in [DAMA/tree.py](tree.py).