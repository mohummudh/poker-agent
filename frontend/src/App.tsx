import { ActionControls } from "./components/ActionControls";
import { ActionLog } from "./components/ActionLog";
import { BoardStage } from "./components/BoardStage";
import { PlayerPanel } from "./components/PlayerPanel";
import { ReplayPanel } from "./components/ReplayPanel";
import { useSession } from "./hooks/useSession";

export default function App() {
  const { mode, session, handSummaries, selectedReplay, loading, submitting, error, submitAction, nextHand, selectReplay } =
    useSession();

  if (loading) {
    return (
      <main className="pixel-app">
        <div className="retro-world" />
        <div className="scanline-layer" />
        <section className="pixel-panel loading-panel">
          <h1 className="pixel-title-lg">Pixel Poker Duel</h1>
          <p>Loading table...</p>
        </section>
      </main>
    );
  }

  if (!session) {
    return (
      <main className="pixel-app">
        <div className="retro-world" />
        <div className="scanline-layer" />
        <section className="pixel-panel loading-panel">
          <h1 className="pixel-title-lg">Pixel Poker Duel</h1>
          <p>No session available.</p>
        </section>
      </main>
    );
  }

  const showNextHand = session.status === "hand_complete" || session.status === "session_complete";
  const opponentVisible = session.players.opponent.cardsVisible || session.street === "showdown" || showNextHand;

  return (
    <main className="pixel-app">
      <div className="retro-world" />
      <div className="scanline-layer" />

      <header className="pixel-panel app-header">
        <div>
          <h1 className="pixel-title-lg">Pixel Poker Duel</h1>
          <p className="header-subtitle">Heads-up No-limit Holdem 1/2 blinds</p>
        </div>
        <div className="header-status">
          <span className="status-badge">{mode === "api" ? "Live API" : "Mock Mode"}</span>
          <span className="status-badge">Hand {session.handId}</span>
          <span className="status-badge">Pot {session.pot}</span>
        </div>
      </header>

      {error ? <div className="pixel-panel error-banner">{error}</div> : null}

      <div className="game-shell">
        <section className="table-column" key={session.handId}>
          <PlayerPanel player={session.players.opponent} roleLabel="Opponent" revealCards={opponentVisible} />
          <BoardStage pot={session.pot} street={session.street} board={session.board} />
          <PlayerPanel player={session.players.human} roleLabel="Player" revealCards />

          <ActionControls legalActions={session.legalActions} disabled={submitting || showNextHand} onSubmit={submitAction} />

          {showNextHand ? (
            <button className="pixel-btn next-hand-btn" type="button" onClick={() => void nextHand()} disabled={submitting}>
              {session.status === "session_complete" ? "Rebuy & Start Next Hand" : "Start Next Hand"}
            </button>
          ) : null}
        </section>

        <aside className="sidebar-column">
          <ActionLog events={session.actionFeed} />
          <ReplayPanel handSummaries={handSummaries} replay={selectedReplay} onSelectHand={selectReplay} />
        </aside>
      </div>
    </main>
  );
}
