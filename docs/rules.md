# Descrizione breve del progetto
Dust Access è un ECG (Gioco di Carte Espandibile) ispirato ai Giochi di Ruolo. I principi alla base del suo design sono:
- **attenzione rivolta al deckbuilding e alla maestria nell'uso delle carte**: ogni giocatore ha a disposizione tutte le carte di tutti i set ed il gameplay delle classi sarà meccanico ma molto consistente nonostante l'onnipresente fattore della fortuna. Il gioco favorisce l'anti-meta e la personalizzazione delle strategie (non si avrà la pressione di dover investire su delle carte nuove solo per provare un mazzo che potrebbe non funzionare)
- **immersività**: il giocatore è il protagonista della sua avventura. Niente "creature" da comandare o risorse esplicite da gestire. Il proprio Accessor, l'avatar dl giocatore, è il focus del gameplay.
- **bassi costi d'accesso**: divisione tra Starter Deck e Set Espansione, dove i starter deck saranno progettati per essere un esperienza di gioco dal più basso costo possibile).
- **maggior equilibrio tra le carte di un set**: nessuna distinzione di rarità e specializzazioni pensate per coesistere piuttosto che per sostituire le precedenti se non strettamente necessario.
- **alta versatilità e adattabilità a nuove modalità di gioco**: anche se non ufficialmente supportato, non dovrebbe risultare difficile a giocatori o designer intraprendenti di utilizzare il gioco come framework per nuove modalità come le 2v2 o il gioco in solitaria o, ad esempio, per costruire interi dungeon esplorabili o avventure come in un gioco di ruolo da tavolo.

# Ambientazione di gioco
- Dopo un apocalisse dalle circostanze poco chiare avvenuta chissà quanto prima, i "nuovi umani" si ritrovano a dover percorrere da zero il percorso della civilizzazione che l'umanità che noi conosciamo ha vissuto.
- Viene ritrovato di un antico server contenente un'IA che conosce tutto lo scibile umano; purtroppo, questa è abbastanza avanzata da avere una coscienza e scegliere il sonno eterno alla solitudine.
Insieme al server è ritrovato uno strano calcolatore antropomorfo che, se connesso tramite dei sensori ad un umano, è capace di permettergli di proiettare la sua coscienza in una simulazione fisica simile ad un deserto ("S&&S", Simulation and Statistics, anche detta "Sands") in cui i sogni dell'IA emergono dalle sabbie di dati.
- I "nuovi umani" sono affascinati dalla scoperta: ognuno tenta di copiare il calcolatore originale per accedere alla conoscenza nascosta nel server e recuperare quanti più dati possibili dalle S&&S. Nascono così gli Accessor, personal computer antropomorfi che replicano le funzioni del dispositivo originale in tutto e per tutto.
- La conquista dei dati contenuti nell'IA, ora conosciuta anche come "Sandman", sarà fonte di molte battaglie ed anche movimenti religiosi (che proteggono le S&&S dai razziatori di dati siccome rispettano Sandman come un messia ed attendono il suo risveglio), rivoluzionando per sempre la nuova civiltà che avanzerà a velocità incredibili.

# Ruleset
## La regola d'oro
Se il testo di una carta contraddice una regola e la carta è considerata "giocabile" dal regolamento adottato in quella partita, allora il testo della carta avrà la priorità sulle regole.

## Win Condition
Il giocatore il cui Accessor ha HP maggiori di 0 nell'istante in cui tutti gli altri Accessor hanno HP pari a 0 è il vincitore dello scontro.

## Requisiti per il gioco
Ogni giocatore deve avere:
- **Mazzo Loot:** il mazzo principale. È composto da carte Azione e da carte Equip per un totale di 60 carte.
- **Mazzo Specializzazioni (Mazzo SPE)**: il mazzo che contiene le carte SPE del giocatore.
- **Una carta Accessor**: Carta o Token che rappresenta il giocatore. Hanno due caratteristiche: 
	- Un contatore "livello" che coincide con il numero di turni che si è personalmente iniziato (Se il giocatore ha iniziato il proprio secondo turno, il livello dell'Accessor sarà 2). Il livello massimo è 10.
	- Un contatore "HP" che inizialmente coincide con la Durabilità riportata sulla propria SPE. Ad ogni turno, se il livello è inferiore o uguale a 5, gli **HP Massimi** aumentano di 10, ma gli HP attuali non vengono curati automaticamente.
	
	Può essere anche personalizzato o creato dal giocatore se si desidera giocare nei panni di un proprio personaggio. 
	>Un Accessor personalizzato deve essere sempre creato nel rispetto delle sensibilità degli altri membri del tavolo di gioco a cui si sta partecipando e, se presente, al regolamento definito dall'evento.
	
- Un modo per tener traccia dei contatori applicati su ogni carta (es. dadi)

## Costruzione del Mazzo Loot
Il mazzo Loot deve contenere esattamente 60 carte ed è possibile inserire un massimo di 3 copie per carta.

## Tipi di Carte
### Azioni
Carte con effetti attivabili nella Duel Phase che è possibile inserire nel mazzo Loot. 
Possono essere "Apprendibili" o "Trucchetti".
- Le **Azioni Apprendibili (Skill)** devono essere innanzitutto piazzate sul campo da gioco durante la Preparation Phase. 
- I **Trucchetti**, invece, possono essere attivati immediatamente dalla mano durante la Duel Phase e sono rimossi dal gioco una volta che il loro effetto termina. Non hanno un costo di attivazione specifico, ma alcuni trucchetti possono richiederne uno.

Come evidenziato nella sezione sulla **Struttura di un turno**, nella Duel Phase il giocatore ha a disposizione **un'Azione Tattica** e **un'Azione di Combattimento**.
L'attivazione di una Skill o di un Trucchetto consuma l'**Azione Tattica**.

Esistono alcune eccezioni alla regola:
- Due azioni (che chiameremo A e B) possono creare una "**Chain**" se la carta A indica all'interno del suo effetto la dicitura **Chain "B"**. Se si attiva A e la carta B è presente in campo e pronta, il giocatore può scegliere di attivare immediatamente anche l'azione B. Verranno eseguite entrambe le azioni nell'ordine A -> B consumando una sola Azione Tattica.
- Un azione può essere "**Instant**" se non è considerata nel limite di azioni per turno e il suo effetto è attivabile in qualsiasi momento del proprio turno. Ogni Instant ha un costo o una condizione di attivazione definita dalla carta stessa.

**Cooldown e Ricarica:**
Ogni qual volta un'azione è attivata è necessario posizionarla in orizzontale per indicare che è stata usata, e si posizionano su di essa tanti contatori CD quanto è descritto dal tempo di ricarica ("CD") riportato sulla carta. Un azione in questo stato è detta "**in ricarica**".
Un azione è attivabile solo se è posizionata in verticale e non ha contatori. Un azione in questo stato è detta "**pronta**".

Un azione che ha come effetto il fare danni che riesce a diminuire gli HP si dice che **colpisce**.
Un azione che ha come effetto il fare danni ma non riesce a diminuire gli HP nemici si dice **mancata**.

A inizio turno avviene la fase di **Ricarica globale**:
Si rimuove 1 contatore CD da **tutte** le proprie carte in ricarica. Se una carta in ricarica non possiede più contatori CD (o raggiunge lo 0 in questo momento), viene immediatamente posizionata in verticale (diventa pronta).

#### Limite di Skill sul Campo
È possibile avere al massimo 4 Skill Apprendibili sul campo contemporaneamente. Le Skill in ricarica (posizionate in orizzontale) occupano comunque uno degli slot disponibili. Se si vuole giocare una quinta Skill quando i 4 slot sono già occupati, è necessario scartare una delle Skill già presenti sul campo per liberare uno slot.

### Equip 
Carte che è possibile inserire nel mazzo Loot e che puoi equipaggiare nella Duel Phase (consumando la tua **Azione Tattica**) per aumentare le statistiche dell'Accessor se questo raggiunge le statistiche (es. Livello, Classe) richieste.
Possono avere anche degli effetti. 
Possono essere di 6 tipi:
1. Testa
2. Corpo
3. Braccia
4. Gambe
5. Arma principale
6. Mano Secondaria

È possibile avere in campo solo una carta Equip per tipo: se si vuole giocare una carta equip di un tipo che è già in campo è necessario rimuovere dal gioco la carta già presente.
Se un Arma è definita **Dual**, non puoi equipaggiare Equip nella Mano Secondaria.

L'Arma e la Mano Secondaria possono avere delle Skill associate: l'arma ha sempre un **Attacco** che consuma l'**Azione di Combattimento** durante la Duel Phase.

### Specializzazioni ("SPE")
Carte che influenzano il tuo stile di gioco e conferiscono al tuo Accessor tutto il testo contenuto al loro interno (Specializzazione ed effetti).
Possono essere Base o Avanzate: A inizio partita si deve giocare una Specializzazione Base, ma raggiunto il livello 5 del proprio Accessor è possibile evolverla in una Specializzazione Avanzata durante la Preparation Phase.

#### Statistiche delle Specializzazioni
- **Classe:** Può essere Leggera, Media o Pesante. Influenza gli Equipaggiamenti e le Abilità che è possibile utilizzare.
- **Durabilità:** Quanti "colpi" il tuo Accessor può prendere prima di essere costretto ad arretrare. Ad inizio partita coincide con il numero di HP.
- **Potenza:** La potenza di fuoco del tuo Accessor. Influenza i danni delle armi e delle skill.
- **Efficienza:** Un Accessor efficiente sarà capace di utilizzare al meglio le sue Abilità. Aumenta i danni o l'efficacia delle Skill.
- **Sensitività:** Un Accessor sensitivo è dotato di un IA migliore. Aumenta la capacità di cura.
- **Tenacia:** Il valore di armatura che viene sottratto direttamente dai danni in arrivo. 
  - Se Danno - Tenacia > 0: Il colpo (attacco o skill) va a segno (Hit) e infligge danni agli HP.
  - Altrimenti: Il colpo è parato/mancato (Blocked/Miss). Non vengono inflitti danni agli HP, ma si attivano eventuali effetti "On Miss" dell'attaccante.
#### La classe delle Specializzazioni
Un Accessor di **Classe Pesante** avrà le seguenti caratteristiche:
- Alta Potenza e/o Tenacia.
- Bassa Efficienza e/o Sensitività.
- Accesso a Equip e Azioni di classe Pesante (con Equip solitamente migliori e Azioni più semplici ma potenti in early game).

Un Accessor di **Classe Media** avrà le seguenti caratteristiche:
- Statistiche mediamente più alte ma senza picchi particolari.
- Accesso a Equip e Azioni di classe Media (con Trucchetti solitamente migliori e maggiore versatilità).

Un Accessor di **Classe Leggera** avrà le seguenti caratteristiche:
- Alta Efficienza e/o Sensitività.
- Bassa Potenza e/o Tenacia.
- Accesso a Equip e Azioni di classe Leggera (con Skill solitamente migliori e maggiore scalabilità nel late game).

## Struttura di una Partita
Una partita tra due giocatori avviene secondo questa sequenza:
1. I due giocatori lanciano un dado: il giocatore con il lancio più alto determina chi dei due inizia per primo (Per comodità chiameremo il giocatore che inizia per primo Giocatore 1 ed il giocatore che lo succede Giocatore 2). In caso di parità si ripete il lancio.

2. I due giocatori pescano 5 carte ciascuno dal mazzo Loot. Il Giocatore 2 pesca una carta aggiuntiva (per un totale di 6 carte). Entrambi i giocatori possono scegliere di effettuare un mulligan: se lo fanno, rimescolano le carte pescate nel mazzo e pescano nuovamente. È possibile effettuare mulligan solo una volta.

3. Dopo aver pescato, i due giocatori scelgono una Specializzazione Base dal mazzo apposito e la piazzano. Inizia quindi il turno del Giocatore 1, che, per il primo turno non pescherà e salterà direttamente alla Preparation Phase.

4. Al termine del suo turno toccherà al Giocatore 2.

5. Dopo il Giocatore 2 sarà nuovamente il turno del Giocatore 1 e viceversa, finché uno dei due non esaurisce gli HP.

### Struttura di un turno

Un turno si compone delle seguenti fasi:
1. **Fase di inizio turno:** 
   - Il Livello dell Accessor aumenta di 1 (fino a max 10).
   - Si rimuove 1 contatore CD da tutte le carte in ricarica e si rendono pronte quelle a 0 contatori.
   - Si attivano gli effetti "di inizio turno".

2. **Loot Phase:** Peschi una carta dal mazzo Loot.

3. **Preparation Phase:** In questa fase puoi solo **piazzare** carte sul campo per preparare le strategie future, ma non attivarle.
   - Puoi piazzare Skill Apprendibili dalla mano negli slot liberi.
   - Se hai raggiunto il Livello 5, puoi evolvere la tua Specializzazione.

4. **Duel Phase**: In questa fase hai a disposizione due azioni indipendenti, utilizzabili in qualsiasi ordine: **1 Azione Tattica** e **1 Azione di Combattimento**.

   **Azione Tattica (Scegline una):**
   - Attivare una Skill o un instant skill pronta sul campo (poi va in ricarica).
   - Equipaggiare un oggetto dalla mano (o sostituirne uno esistente).
   - *Se la Skill attivata ha una Chain valida, la seconda skill può essere attivata gratuitamente.*
   
   **Azione di Combattimento:**
   - Eseguire l'Attacco dell'arma equipaggiata: Se nessuna arma è equipaggiata, si può eseguire "un colpo base" che fa sempre 1 danno e conta come colpo mancato.
   > Inoltre, in questa fase è possibile attivare i trucchetti giocandoli direttamente dalla mano senza costi.
5. **Fase di fine turno:** 
   - Si attivano gli effetti "alla fine del turno".
   - Terminano gli effetti che durano "fino alla fine del turno".
   - **Check della mano:** Se hai più di 5 carte in mano, devi scartare carte finché non ne hai 5.