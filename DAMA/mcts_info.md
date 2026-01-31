# Architettura SO-ISMCTS per il Bilanciamento di Dust Access

Questo documento descrive l'architettura, le scelte progettuali e i fondamenti teorici dell'agente di intelligenza artificiale sviluppato per l'analisi del bilanciamento di *Dust Access*.

L'agente agisce come uno strumento di **Stress-Testing Analitico**. Il suo obiettivo primario non è "vincere", ma esplorare lo spazio delle possibilità per validare la solidità matematica degli **Structure Decks**, garantendo che il prodotto "out-of-the-box" sia giocabile ed equilibrato prima che i giocatori inizino il processo di deckbuilding personalizzato.

---

## 1. Il Dominio: Expandable Card Games (ECG)

È fondamentale distinguere *Dust Access* dai classici TCG per comprendere l'approccio alla simulazione.

### 1.1 ECG vs TCG: Il Cambio di Paradigma
*Dust Access* è un **Expandable Card Game (ECG)**. A differenza dei TCG (Trading Card Games), non esiste la "caccia alla carta rara" tramite bustine casuali. Le carte sono distribuite in set fissi (Structure Decks).
*   **Implicazione per il Bilanciamento:** Non è accettabile che una carta sia "più forte perché è rara". Ogni Structure Deck deve essere competitivo contro gli altri nel suo stato base.
*   **Obiettivo della Simulazione:** Il *Winrate del Mazzo* è una metrica importante ma secondaria (poiché i giocatori modificheranno i mazzi). La metrica primaria è l'**Efficienza della Carta**: individuare se specifiche carte all'interno di uno Structure Deck offrono un vantaggio matematico ingiustificabile, rompendo l'economia del gioco.

### 1.2 Concetti Strategici Chiave
L'AI deve modellare concetti avanzati per valutare correttamente le carte:
*   **Engine (Motore):** Carte che convertono risorse (es. azioni, scarti) in vantaggio incrementale (pescate, segnalini). RAVE è essenziale qui, poiché l'Engine non vince subito, ma aumenta la probabilità di vittoria futura.
*   **Anti-Meta (Tech):** Carte progettate per contrastare strategie specifiche (es. *Nullify* contro mazzi Combo, *Rust* contro mazzi Equipaggiamento).
*   **Hard Commit vs Soft Commit:** Capire quando impegnare risorse permanenti (equipaggiare un'arma a due mani che occupa due slot) rispetto a risorse temporanee.

---

## 2. Il Sistema di Gioco: Regole ed Euristiche di *Dust Access*

Il design dell'agente è strettamente accoppiato alle meccaniche uniche di *Dust Access*. L'MCTS non "impara le regole" da zero, ma le naviga attraverso vincoli rigidi.

### 2.1 L'Avatar: Accessor e Statistiche
A differenza di giochi basati su creature (es. *Magic*), in *Dust Access* i giocatori ("Accessors") combattono direttamente. Lo stato del gioco è definito da statistiche fluide:
*   **Power (Attacco) vs Tenacity (Difesa):** Il cuore del gioco è matematico. Il danno è spesso calcolato come `max(1, Power - Tenacity)`.
    *   *Euristica MCTS:* L'AI valuta i "Breakpoints". Se l'avversario ha Tenacity 5, avere Power 5 o 6 è inutile (1 danno), ma Power 7 è infinitamente meglio (2 danni, quindi abbiamo praticamente raddoppiato il payoff). Questo guida l'equipaggiamento.
*   **Durability (Max HP):** La salute massima, che funge anche da "cap" per le cure.
*   **Efficiency & Sensitivity:** Statistiche di scaling che potenziano specifiche abilità o magie.

### 2.2 Action Economy: Combat vs Tactical
Il turno non è libero, ma vincolato da due risorse d'azione distinte:
1.  **Combat Action:** Usata esclusivamente per attaccare con l'arma equipaggiata.
2.  **Tactical Action:** Usata per giocare carte dalla mano (Cast), equipaggiare oggetti (Equip) o attivare abilità (Activate).
*   *Conseguenza Algoritmica:* L'albero di ricerca ha un fattore di ramificazione controllato. L'AI deve decidere l'ordine ottimale (es. Usare l'azione Tattica per buffarsi *prima* di usare l'azione Combat per attaccare).

### 2.3 Gestione degli Slot e Scaling
*   **Slot Rigidi:** Un giocatore ha slot specifici (Weapon, Off-Hand, Head, Chest, ecc.).
*   **Armi a Due Mani (Dual):** Equipaggiare un'arma *Dual* blocca lo slot *Off-Hand*. L'AI deve capire che equipaggiare un'arma a due mani comporta il costo opportunità di perdere lo scudo.
*   **Level Scaling:** La partita progredisce a turni. Al turno $X$, i giocatori sono al livello $\lceil X/2 \rceil$.
    *   *Euristica:* Una carta di Livello 1 è ottima al Turno 1, ma è un "dead draw" al Turno 10. L'MCTS pesa l'efficienza rispetto al livello corrente.

---

## 3. Scelte Architetturali e Giustificazioni Teoriche

L'agente utilizza una variante di MCTS. Di seguito la giustificazione per ogni componente rispetto alle regole sopra descritte.

### 3.1 Perché MCTS (Monte Carlo Tree Search)?
In *Dust Access*, lo spazio degli stati è vasto a causa delle combinazioni di equipaggiamento e statistiche. Una funzione di valutazione statica (come in Minimax) sarebbe troppo complessa da scrivere a mano e fragile ai cambiamenti di bilanciamento.
MCTS valuta uno stato "giocando" (Playouts) e le euristiche sono solo di accompagnamento, massimizzando i suoi risultati nello stesso numero di iterazioni. Se una configurazione di equipaggiamento porta alla vittoria nel 60% dei casi, è "forte", indipendentemente dal perché.

### 3.2 Perché SO-ISMCTS (Single-Observer Information Set MCTS)?
Un TCG è un gioco a **Informazione Imperfetta**.
Se usassimo MCTS standard, l'AI "vedrebbe" la mano dell'avversario e non giocherebbe mai in una trappola, falsando i dati.
**SO-ISMCTS** utilizza la **Determinization**:
1.  L'AI osserva il tavolo visibile.
2.  L'AI *ipotizza* una mano avversaria (mescolando le carte ignote nel mazzo/mano).
3.  Esegue la simulazione su questo stato ipotetico.
Questo simula un giocatore che ragiona sulle *probabilità* ("Potrebbe avere la carta X"), non sulla certezza.

### 3.3 Perché UCT e RAVE?
*   **UCT (Upper Confidence Bound applied to Trees):** Gestisce il dilemma tra esplorare nuove strategie (Exploration) e approfondire quelle vincenti (Exploitation).
*   **RAVE (Rapid Action Value Estimation):** Cruciale per rilevare gli **Engine**. In *Dust Access*, giocare una carta che aumenta la *Efficiency* al turno 1 paga i dividendi al turno 5. L'UCT standard è lento a capirlo. RAVE generalizza: "Se gioco questa carta, indipendentemente da quando, vinco spesso?". Questo permette all'AI di riconoscere rapidamente il valore degli investimenti a lungo termine.

### 3.4 Il Beta Dinamico
RAVE è impreciso nel breve termine (ignora la tattica). Il **Beta Dinamico** permette all'AI di fidarsi di RAVE all'inizio della ricerca (intuizione strategica) e di passare a UCT puro man mano che accumula dati (calcolo tattico preciso), emulando il processo mentale di un esperto.

---

## 4. Euristiche e Logiche di Dominio

### 4.1 Consistency Enforcement ("God Mode")
Questa è l'innovazione tecnica critica per supportare la natura "Combo" di *Dust Access*.
A causa della *Determinization*, l'ordine del mazzo cambia a ogni simulazione.
*   *Il Problema:* L'AI pianifica una combo su 2 turni. Al secondo turno, la simulazione rimescola il mazzo e la carta necessaria sparisce. L'AI conclude erroneamente che la combo è inaffidabile.
*   *La Soluzione:* Se l'albero di ricerca decide di giocare una carta specifica, il simulatore **forza** quella carta nella mano dell'agente (recuperandola dal mazzo).
*   *Ratio:* Stiamo valutando se la strategia è forte *quando riesce*, non quanto è fortunato il pescare. Questo isola la potenza della carta dalla varianza dello shuffle.

### 4.2 Analisi delle Minacce (`HeuristicAnalyzer`)
Nei playout (la fase casuale), l'AI non gioca a caso ma usa logiche minime per evitare partite senza senso:
1.  **Lethal Check:** Se `Power > HP Avversario`, attacca e vinci.
2.  **Wall Threat:** Se `Power <= Tenacity Avversario`, non attaccare inutilmente; cerca buff o azioni tattiche.

---

## 5. Metodologia Scientifica: Simulazione Stratificata

Per il report finale, simuliamo diversi livelli di abilità per separare le carte "facili" da quelle "forti".

| Tier | Iterazioni | Games ($N$) | Razionale Tecnico |
| :--- | :--- | :--- | :--- |
| **Casual** | 100 | 1600 | **High Noise.** L'AI gioca "a vista" (Greedy). Alto campione per mediare gli errori. Identifica carte che puniscono i principianti (*Noob Stompers*). |
| **Advanced** | 500 | 1000 | **Balanced.** Pianificazione tattica (2-3 turni). Simula il giocatore medio di Structure Deck. |
| **Competitive** | 1000 | 800 | **Low Noise.** L'AI converge all'ottimo (Nash Equilibrium approssimato). Identifica problemi strutturali profondi (*Universal Threats*) e carte ad alto skill cap (*Skill Spikes*). |

Questa stratificazione garantisce che il bilanciamento non renda il gioco inaccessibile ai neofiti (nerfando i Noob Stompers) né banale per gli esperti (preservando gli Skill Spikes).
