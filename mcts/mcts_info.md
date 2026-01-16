# Architettura dell'Agente: UCT con Scoring Dinamico basato su RAVE

  Per l'analisi del bilanciamento è stato sviluppato un agente autonomo basato su MCTS. La variante implementata è UCT (Upper
  Confidence bounds applied to Trees) con un meccanismo di scoring avanzato che utilizza RAVE (Rapid Action Value Estimation)
  e un beta dinamico.

  La configurazione dell'algoritmo è stata guidata dalla necessità di emulare una specifica "persona" di giocatore.

  ## 1. La "Personas" di Riferimento: il "Meta-Gamer"

  L'obiettivo del nostro algoritmo è simulare un giocatore di livello competitivo. Questo giocatore tipo, che chiameremo
  "meta-gamer", è aggressivo, cerca di ottenere il massimo vantaggio possibile e applica le strategie più promettenti
  scoperte dalla community globale.

  >Il "meta-gaming" è la pratica di prendere decisioni basandosi su conoscenze statistiche acquisite esternamente (es.
  risultati di tornei, tassi di vittoria delle carte), invece di affidarsi solo all'esperienza personale o a stime
  qualitative (le cosiddette "euristiche" o il "theory-crafting").

  Questa analogia è perfetta per il nostro MCTS: l'algoritmo agisce come un meta-gamer, dove le "conoscenze esterne" non sono
  i tornei, ma le migliaia di partite che esso stesso simula per quantificare matematicamente il valore di ogni mossa.

  ## 2. I Principi del Gioco Competitivo da Modellare

  L'equilibrio di un "meta" competitivo si basa su due principi che il nostro bot deve saper riconoscere:

   1. **Il Principio di Consistenza (la ricerca del "Best-in-Slot"):** Una strategia con un'alta consistenza (un win rate elevato
      e statisticamente affidabile) è quasi sempre preferibile a una strategia più "esplosiva" ma volatile, che magari
      produce vittorie schiaccianti in alcuni casi ma è inefficace in troppi altri. L'obiettivo è massimizzare il vantaggio
      evitando turni "morti" o mosse inutilizzabili.

   2. **Il Principio Contestuale (le "Anti-Meta Tech"):** Una strategia che è spesso inefficace in generale, ma che vince in modo
      affidabile contro una specifica strategia dominante, è uno strumento prezioso. Diventa una scelta forte se il contesto
      in cui funziona (cioè la presenza del mazzo da battere) appare spesso.

  3. Traduzione dei Principi nei Parametri dell'Algoritmo

  Per modellare questo comportamento, abbiamo configurato RAVE con un beta dinamico grazie all'uso di un parametro `b` = 0.01:

  La scelta di un b piccolo ma maggiore di zero nella formula del beta dinamico è cruciale per la nostra analisi. Questo
  parametro forza un decadimento dell'influenza delle statistiche generali di RAVE (AMAF), costringendo l'algoritmo a
  specializzarsi sulle linee di gioco più promettenti man mano che le esplora.

  Questo modella perfettamente il comportamento di un giocatore esperto per due motivi:

   1. Corregge il Difetto di RAVE: RAVE è potentissimo nello scoprire il valore "generale" di una carta, ma tende a ignorare
      l'importanza dell'ordine delle mosse. Il decadimento di beta spinge il bot a fidarsi dei dati specifici di una sequenza
      una volta che è stata testata a sufficienza, riconoscendo che in un gioco di carte il contesto e la sequenza sono
      tutto.

   2. Permette la Scoperta di Strategie di Nicchia: Forzando la specializzazione, il bot può identificare "ottimi locali
      strabilianti". In altre parole, può scoprire che una certa mossa, magari debole in generale, ha un win rate altissimo
      in una situazione molto specifica. Questo è il meccanismo con cui l'algoritmo identifica non solo le strategie
      dominanti e versatili (il "meta"), ma anche le potenti strategie di nicchia ("anti-meta").

  Questa capacità è fondamentale nel nostro contesto di analisi di structure deck, dove l'equilibrio non è dato dalla
  possibilità di cambiare carte, ma dalla ricchezza di opzioni strategiche e di contromosse presenti all'interno del mazzo
  stesso.

