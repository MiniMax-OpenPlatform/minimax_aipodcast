import React from 'react';
import './App.css';
import PodcastGenerator from './components/PodcastGenerator';

function App() {
  return (
    <div className="App">
      <header className="app-header">
        <h1>🎙️ MiniMax AI 播客生成器</h1>
        <p>智能生成专业播客</p>
      </header>
      <main className="app-main">
        <PodcastGenerator />
      </main>
      <footer className="app-footer">
        <p>Powered by MiniMax AI | 🤖 Generated with Claude Code</p>
      </footer>
    </div>
  );
}

export default App;
