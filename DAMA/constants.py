from typing import Final

class HeuristicWeights:
    """
    Weights used by the HeuristicAnalyzer to bias the AI's decision-making
    during playouts and move selection. These are not 'hard rules' but
    priorities that help the AI play more like a human expert.
    """
    # --- Mulligan (Preparation Phase) ---
    # Bonus added to the evaluation of the 'Mulligan' action if the hand is bad (brick).
    MULLIGAN_BONUS: Final[float] = 800.0
    # Penalty added if the hand is already playable, to discourage unnecessary reshuffling.
    MULLIGAN_PENALTY: Final[float] = -800.0

    # --- Combo & Chains ---
    # High bonus for completing a Chain (e.g., following Skill A with Skill B).
    CHAIN_COMPLETION_BONUS: Final[float] = 600.0
    # Moderate bonus if the card being played has a 'ChainsWith' target currently in hand/slot.
    CHAIN_POTENTIAL_BONUS: Final[float] = 120.0
    # Synergy bonus for completing 'Set' pieces (like having multiple 'Valor' items).
    SET_PIECE_BONUS: Final[float] = 100.0

    # --- Ramping & Snowballing ---
    # Threshold (turns) to consider a game as 'Early Game'.
    EARLY_GAME_TURN_LIMIT: Final[int] = 5
    # Incentive to play resource generators (Rage/Kai generators) early on.
    EARLY_RAMP_BONUS: Final[float] = 80.0
    # Higher bonus for 'Light' (Control) classes to play scaling cards early.
    EARLY_SCALING_BONUS_LIGHT: Final[float] = 120.0
    # Generic incentive for early scaling/permanent buffs.
    EARLY_SCALING_BONUS_GENERIC: Final[float] = 60.0
    # Penalty to discourage over-generating resources when the game is already in late stages.
    LATE_GAME_GENERATOR_PENALTY: Final[float] = -20.0

    # --- Tempo (Immediate Board Impact) ---
    # HP ratio below which the opponent is considered in 'Lethal Range'.
    LETHAL_HP_RATIO: Final[float] = 0.4
    # HP ratio below which the observer is considered in 'Survival Range'.
    SURVIVAL_HP_RATIO: Final[float] = 0.3
    # Massive incentive to use 'Finisher' tagged cards when the enemy is low.
    FINISHER_LETHAL_BONUS: Final[float] = 150.0
    # Penalty for 'wasting' high-level finishers too early in the game.
    FINISHER_EARLY_PENALTY: Final[float] = -40.0
    # Bonus to prioritize defensive actions (Heal, Shield) when HP is critical.
    SURVIVAL_TEMPO_BONUS: Final[float] = 120.0
    # Multiplier for tempo-related bonuses for 'Heavy' (Aggro) classes.
    AGGRO_TEMPO_MULTIPLIER: Final[float] = 1.5

    # --- Meta Countering ---
    # Winrate Bias threshold in the MetaRegistry to consider a card a 'Universal Threat'.
    META_COUNTER_THRESHOLD: Final[float] = 20.0
    # Bonus for playing 'Counter' cards (Unequip, Discard) when the enemy has a threat equipped.
    META_COUNTER_BONUS: Final[float] = 150.0

    # --- Resource Efficiency ---
    # Incentive to generate resources when below the safe threshold (e.g., <2 Rage).
    LOW_RAGE_GENERATOR_BONUS: Final[float] = 40.0
    # Incentive to use cards that 'consume' resources when they are plentiful.
    HIGH_RAGE_CONSUMER_BONUS: Final[float] = 30.0

    # --- Prerequisites (Rule Enforcement) ---
    # Hard penalty for attempting to play a card without its 'Requires' field met.
    PREREQ_FAIL_PENALTY: Final[float] = -500.0
    # Multiplier for the value of a card if its Chain prerequisite isn't in play yet.
    PREREQ_CHAIN_MISSING_MULT: Final[float] = 0.4
    # Minimum prerequisite satisfaction for a card to be considered playable.
    PREREQ_MIN_THRESHOLD: Final[float] = 0.1

    # --- Thresholds & Limits ---
    # Max level for a card to be considered 'Early Game' playable.
    LOW_LEVEL_THRESHOLD: Final[int] = 2
    # Hand brick threshold (Too few low level cards).
    HAND_BRICK_THRESHOLD: Final[int] = 1
    # Hand healthy threshold (Enough low level cards).
    HAND_HEALTHY_THRESHOLD: Final[int] = 3
    # Late game turn threshold.
    LATE_GAME_HAND_SIZE: Final[int] = 4
    # Level at which 'Light' classes switch to Late Game mode.
    LIGHT_LATE_GAME_LEVEL: Final[int] = 7
    # Threshold for 'Low Rage' state.
    LOW_RAGE_THRESHOLD: Final[int] = 2

    # --- Archetype Scalars ---
    HEAVY_RAGE_BONUS: Final[float] = 0.1
    MEDIUM_RESOURCE_SCALAR: Final[float] = 0.05
    MEDIUM_HP_DIFF_SCALAR: Final[float] = 0.5
    LIGHT_CARD_ADV_SCALAR: Final[float] = 0.1
    # Floating point epsilon for divisions and comparisons
    EPSILON: Final[float] = 0.1

class MCTSConfig:
    """
    Core algorithmic parameters for the Information Set MCTS implementation.
    Adjusting these changes how the AI explores the game tree.
    """
    # Decay factor for RAVE (Rapid Action Value Estimation).
    # Controls how quickly the AI shifts from 'global intuition' to 'local tactical' calculation.
    RAVE_B_PARAM: Final[float] = 0.05
    # Default winrate assumed for nodes with 0 visits in AMAF statistics.
    AMAF_DEFAULT_WR: Final[float] = 0.5
    # UCT Exploration Coefficient (Cp).
    # Theoretical value is √2 ≈ 1.41 for rewards in [0,1], but domain-specific tuning is standard
    # (Browne et al., 2012). Studies on card games with imperfect information (e.g., Hearts)
    # found optimal Cp values below 0.5 due to limited branching. However, ECGs like Dust Access
    # have higher complexity (combos, equipment, resources), requiring more exploration.
    # We use 0.7 as a middle ground: lower than √2 because RAVE and HeuristicAnalyzer provide
    # strong priors, but higher than trick-taking games due to strategic depth.
    UCT_EXPLORATION_CP: Final[float] = 0.7
    # Maximum simulation depth (turns) per playout.
    MAX_ROLLOUT_DEPTH: Final[int] = 60
    # Probability of making a random move during playouts (vs heuristic move).
    ROLLOUT_EPSILON: Final[float] = 0.1

class RolloutPolicyWeights:
    """
    Weights specifically for the MCTS Rollout Policy.
    Balances speed with tactical intelligence.
    """
    BASE_WEIGHT: Final[float] = 10.0
    
    # Bonuses
    LETHAL_BONUS: Final[float] = 1000.0
    WALL_THREAT_REACTIVE_BONUS: Final[float] = 200.0
    META_BIAS_MULTIPLIER: Final[float] = 1.0
    META_EXPLORE_MULTIPLIER: Final[float] = 0.2
    
    # Minimum weight to ensure probabilistic variety
    MIN_WEIGHT: Final[float] = 0.1

class SimulationConfig:
    """
    Statistical and Tier configuration for the batch simulation runner.
    """
    # Z-Score for a 95% Confidence Interval in statistical sampling.
    # 1.96 means we are 95% sure that the results are not due to random chance.
    # It’s the universal standard to ensure the "Winrate" we see is mathematically stable.
    Z_SCORE_95: Final[float] = 1.96

    # Maximum expected variance (p=0.5) for the binomial winrate distribution.
    P_VAL_WORST_CASE: Final[float] = 0.5

    # --- Match Limits ---
    # Maximum turns before a match is declared a draw.
    MAX_MATCH_TURNS: Final[int] = 50
    # Soft stuck threshold (starts random move fallback).
    STUCK_THRESHOLD_SOFT: Final[int] = 3
    # Hard stuck threshold (terminates match).
    STUCK_THRESHOLD_HARD: Final[int] = 5
    # HP ratio below which a win is considered a 'Comeback'.
    COMEBACK_HP_RATIO: Final[float] = 0.3
    # Generic batch size for simulation tasks.
    BATCH_SIZE: Final[int] = 1

    # --- Tier Config: (Iterations per move, Process Noise Multiplier) ---
    # Casual: Fast simulation, noisier results (needs 1.5x more games for signal).
    TIER_CASUAL = (100, 1.5)
    # Advanced: Balanced depth and sample size.
    TIER_ADVANCED = (500, 1.2)
    # Competitive: Deep search, follows Nash Equilibrium closely (Base N needed).
    TIER_COMPETITIVE = (1000, 1.0)

