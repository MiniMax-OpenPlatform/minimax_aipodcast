import React, { useState, useRef } from 'react';
import './PodcastGenerator.css';

const PodcastGenerator = () => {
  // 状态管理
  const [apiKey, setApiKey] = useState('');
  const [textInput, setTextInput] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [pdfFile, setPdfFile] = useState(null);

  const [speaker1Type, setSpeaker1Type] = useState('default');
  const [speaker1Voice, setSpeaker1Voice] = useState('mini');
  const [speaker1Audio, setSpeaker1Audio] = useState(null);

  const [speaker2Type, setSpeaker2Type] = useState('default');
  const [speaker2Voice, setSpeaker2Voice] = useState('max');
  const [speaker2Audio, setSpeaker2Audio] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const [logs, setLogs] = useState([]);
  const [script, setScript] = useState([]);
  const [coverImage, setCoverImage] = useState('');
  const [traceIds, setTraceIds] = useState([]);

  const [audioUrl, setAudioUrl] = useState('');
  const [scriptUrl, setScriptUrl] = useState('');

  const [showLogs, setShowLogs] = useState(false);

  // 渐进式播放相关状态 - 双缓冲方案
  const [activePlayer, setActivePlayer] = useState(0);  // 当前激活的播放器 (0 或 1)
  const [player0Url, setPlayer0Url] = useState('');
  const [player1Url, setPlayer1Url] = useState('');

  // URL 解析警告
  const [urlWarning, setUrlWarning] = useState(null);  // {message: string, error_code: string}

  const audioRef0 = useRef(null);
  const audioRef1 = useRef(null);

  // API 基础 URL（从环境变量读取，默认为空字符串表示同源）
  // 开发环境通过 package.json 的 proxy 配置代理到 http://localhost:5001
  // 生产环境通过 Nginx 反向代理到后端服务
  const API_URL = process.env.REACT_APP_API_URL || '';

  // 处理文件上传
  const handlePdfChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setPdfFile(file);
    } else {
      alert('请上传 PDF 文件');
    }
  };

  const handleSpeaker1AudioChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSpeaker1Audio(file);
    }
  };

  const handleSpeaker2AudioChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSpeaker2Audio(file);
    }
  };

  // 添加日志
  const addLog = (message) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), message }]);
  };

  // 添加 Trace ID
  const addTraceId = (api, traceId) => {
    setTraceIds(prev => [...prev, { api, traceId }]);
  };

  // 双缓冲播放器 - 后端已控制更新频率，前端直接更新即可
  const updateProgressiveAudio = (newUrl) => {
    console.log(`[前端播放器] 收到后端更新事件，URL: ${newUrl.substring(newUrl.length - 30)}`);
    performUpdate(newUrl);
  };

  // 执行实际的播放器更新
  const performUpdate = (newUrl) => {
    console.log(`[播放器更新] 开始更新，URL: ${newUrl.substring(newUrl.length - 30)}`);
    const currentAudio = activePlayer === 0 ? audioRef0.current : audioRef1.current;
    const nextAudio = activePlayer === 0 ? audioRef1.current : audioRef0.current;

    // 如果当前播放器正在播放
    if (currentAudio && !currentAudio.paused) {
      const currentTime = currentAudio.currentTime;
      console.log(`[播放器更新] 当前播放中，位置: ${currentTime.toFixed(2)}s，将切换到播放器 ${activePlayer === 0 ? 1 : 0}`);

      // 预加载下一个播放器
      if (activePlayer === 0) {
        setPlayer1Url(newUrl);
      } else {
        setPlayer0Url(newUrl);
      }

      // 等待下一个播放器加载完成后切换
      setTimeout(() => {
        if (nextAudio) {
          nextAudio.currentTime = currentTime;
          nextAudio.play().then(() => {
            // 切换激活的播放器
            setActivePlayer(prev => prev === 0 ? 1 : 0);
            // 暂停之前的播放器
            if (currentAudio) {
              currentAudio.pause();
            }
          }).catch(err => {
            console.error('切换播放失败:', err);
          });
        }
      }, 500);
    } else {
      // 如果没有播放，直接更新当前播放器
      if (activePlayer === 0) {
        setPlayer0Url(newUrl);
      } else {
        setPlayer1Url(newUrl);
      }
    }
  };

  // 通用下载函数 - 解决跨域下载问题
  const handleDownload = async (url, filename) => {
    try {
      const response = await fetch(`${API_URL}${url}`);
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status}`);
      }
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('下载失败:', error);
      alert(`下载失败: ${error.message}`);
    }
  };

  // 生成播客
  const handleGenerate = async () => {
    // 验证输入
    if (!apiKey.trim()) {
      alert('请输入 MiniMax API Key');
      return;
    }

    if (!textInput && !urlInput && !pdfFile) {
      alert('请至少提供一种输入内容（文本/网址/PDF）');
      return;
    }

    // 清空之前的状态
    setLogs([]);
    setScript([]);
    setTraceIds([]);
    setCoverImage('');
    setAudioUrl('');
    setScriptUrl('');
    setPlayer0Url('');
    setPlayer1Url('');
    setActivePlayer(0);
    setUrlWarning(null);
    setIsGenerating(true);

    // 构建 FormData
    const formData = new FormData();
    formData.append('api_key', apiKey);
    if (textInput) formData.append('text_input', textInput);
    if (urlInput) formData.append('url', urlInput);
    if (pdfFile) formData.append('pdf_file', pdfFile);

    formData.append('speaker1_type', speaker1Type);
    if (speaker1Type === 'default') {
      formData.append('speaker1_voice_name', speaker1Voice);
    } else if (speaker1Audio) {
      formData.append('speaker1_audio', speaker1Audio);
    }

    formData.append('speaker2_type', speaker2Type);
    if (speaker2Type === 'default') {
      formData.append('speaker2_voice_name', speaker2Voice);
    } else if (speaker2Audio) {
      formData.append('speaker2_audio', speaker2Audio);
    }

    // 建立 SSE 连接
    try {
      const response = await fetch(`${API_URL}/api/generate_podcast`, {
        method: 'POST',
        body: formData
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = ''; // 用于累积不完整的行

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // 将新数据追加到缓冲区
        buffer += decoder.decode(value, { stream: true });

        // 按行分割，但保留最后一个可能不完整的行
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保存最后一个不完整的行

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            const jsonStr = trimmedLine.substring(6);
            // 跳过空的 data 行
            if (!jsonStr.trim()) continue;

            try {
              const data = JSON.parse(jsonStr);
              handleSSEEvent(data);
            } catch (e) {
              console.error('解析 SSE 数据失败:', e);
              console.error('问题行长度:', jsonStr.length);
              console.error('问题行开头:', jsonStr.substring(0, 100));
              console.error('问题行结尾:', jsonStr.substring(Math.max(0, jsonStr.length - 100)));
              // 不中断流程，继续处理其他事件
            }
          }
        }
      }

      // 处理缓冲区中剩余的数据
      if (buffer.trim() && buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.substring(6));
          handleSSEEvent(data);
        } catch (e) {
          console.error('解析最后一行 SSE 数据失败:', e);
        }
      }
    } catch (error) {
      console.error('生成播客失败:', error);
      addLog(`错误: ${error.message}`);
      setIsGenerating(false);
    }
  };

  // 处理 SSE 事件
  const handleSSEEvent = (data) => {
    switch (data.type) {
      case 'progress':
        setProgress(data.message);
        addLog(data.message);
        break;

      case 'log':
        addLog(data.message);
        break;

      case 'script_chunk':
        setScript(prev => [...prev, data.full_line]);
        break;

      case 'trace_id':
        addTraceId(data.api, data.trace_id);
        break;

      case 'cover_image':
        setCoverImage(data.image_url);
        addLog('封面生成完成');
        break;

      case 'audio_chunk':
        // 这里可以实现流式音频播放
        // 暂时跳过，等待complete事件获取完整音频
        break;

      case 'bgm':
      case 'welcome_audio_chunk':
        // BGM 和欢迎语音频事件，前端不需要处理
        break;

      case 'progressive_audio':
        // 收到渐进式音频更新 - 使用双缓冲策略
        const progressiveUrl = `${API_URL}${data.audio_url}`;

        // 调用双缓冲更新函数（会自动累积并平滑切换）
        updateProgressiveAudio(progressiveUrl);

        // 使用后端发送的 message，或生成默认消息
        let logMessage;
        if (data.message) {
          logMessage = `✅ ${data.message}`;
        } else if (data.sentence_number) {
          logMessage = `✅ 第 ${data.sentence_number} 句已添加，播客时长: ${Math.round(data.duration_ms / 1000)}秒`;
        } else {
          logMessage = `✅ 开场音频已生成，播客时长: ${Math.round(data.duration_ms / 1000)}秒`;
        }
        addLog(logMessage);
        break;

      case 'complete':
        // 设置最终音频和脚本的下载 URL
        console.log('[complete] 收到完成事件:', data);
        console.log('[complete] audio_url:', data.audio_url);
        console.log('[complete] script_url:', data.script_url);
        
        if (data.audio_url) {
          setAudioUrl(data.audio_url);
        }
        if (data.script_url) {
          setScriptUrl(data.script_url);
        }
        setIsGenerating(false);
        setProgress('播客生成完成！');
        addLog('🎉 播客生成完成！可以下载了');
        break;

      case 'url_parse_warning':
        // URL 解析失败的警告，但不中断流程
        addLog(`⚠️ ${data.message}`);
        setUrlWarning({
          message: data.message,
          error_code: data.error_code
        });
        if (data.error_code === '403') {
          setProgress('网址解析遇到问题，但您可以继续使用其他输入方式');
        }
        break;

      case 'error':
        addLog(`❌ 错误: ${data.message}`);
        setIsGenerating(false);
        setProgress('');
        break;

      default:
        console.log('未知事件类型:', data);
    }
  };

  return (
    <div className="podcast-generator">
      {/* API Key 配置区 */}
      <div className="section">
        <h2>🔑 API Key 配置</h2>
        <div className="input-content">
          <div className="input-group">
            <label className="input-label">MiniMax API Key</label>
            <input
              type="password"
              placeholder="请输入你的 MiniMax API Key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="api-key-input"
            />
            <p className="input-description">
              在 <a href="https://www.minimaxi.com/" target="_blank" rel="noopener noreferrer">MiniMax 官网</a> 获取你的 API Key
            </p>
          </div>
        </div>
      </div>

      {/* 输入内容区 */}
      <div className="section">
        <h2>📝 输入内容</h2>
        <p className="input-hint">以下三种输入方式可以单独使用或组合使用：</p>
        <div className="input-content">
          <div className="input-group">
            <label className="input-label">💬 话题文本</label>
            <textarea
              placeholder="输入你想讨论的话题..."
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              rows={5}
            />
          </div>

          <div className="input-group">
            <label className="input-label">🔗 网址链接</label>
            <input
              type="text"
              placeholder="输入网址 URL..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
            />
          </div>

          <div className="input-group">
            <label className="input-label">📄 上传 PDF</label>
            <div className="file-upload">
              <label htmlFor="pdf-upload" className="upload-label">
                {pdfFile ? `已选择: ${pdfFile.name}` : '点击选择 PDF 文件'}
              </label>
              <input
                id="pdf-upload"
                type="file"
                accept=".pdf"
                onChange={handlePdfChange}
                style={{ display: 'none' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 音色选择区 */}
      <div className="section">
        <h2>🎤 选择音色</h2>
        <div className="voice-config">
          <div className="speaker-config">
            <h3>Speaker 1</h3>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  checked={speaker1Type === 'default'}
                  onChange={() => setSpeaker1Type('default')}
                />
                默认音色
              </label>
              {speaker1Type === 'default' && (
                <select value={speaker1Voice} onChange={(e) => setSpeaker1Voice(e.target.value)}>
                  <option value="mini">Mini（女声）</option>
                  <option value="max">Max（男声）</option>
                </select>
              )}
            </div>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  checked={speaker1Type === 'custom'}
                  onChange={() => setSpeaker1Type('custom')}
                />
                自定义音色
              </label>
              {speaker1Type === 'custom' && (
                <div className="file-upload">
                  <label htmlFor="speaker1-audio" className="upload-label">
                    {speaker1Audio ? speaker1Audio.name : '上传音频文件'}
                  </label>
                  <input
                    id="speaker1-audio"
                    type="file"
                    accept=".wav,.mp3,.flac,.m4a"
                    onChange={handleSpeaker1AudioChange}
                    style={{ display: 'none' }}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="speaker-config">
            <h3>Speaker 2</h3>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  checked={speaker2Type === 'default'}
                  onChange={() => setSpeaker2Type('default')}
                />
                默认音色
              </label>
              {speaker2Type === 'default' && (
                <select value={speaker2Voice} onChange={(e) => setSpeaker2Voice(e.target.value)}>
                  <option value="mini">Mini（女声）</option>
                  <option value="max">Max（男声）</option>
                </select>
              )}
            </div>
            <div className="radio-group">
              <label>
                <input
                  type="radio"
                  checked={speaker2Type === 'custom'}
                  onChange={() => setSpeaker2Type('custom')}
                />
                自定义音色
              </label>
              {speaker2Type === 'custom' && (
                <div className="file-upload">
                  <label htmlFor="speaker2-audio" className="upload-label">
                    {speaker2Audio ? speaker2Audio.name : '上传音频文件'}
                  </label>
                  <input
                    id="speaker2-audio"
                    type="file"
                    accept=".wav,.mp3,.flac,.m4a"
                    onChange={handleSpeaker2AudioChange}
                    style={{ display: 'none' }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 生成按钮 */}
      <button
        className="generate-btn"
        onClick={handleGenerate}
        disabled={isGenerating}
      >
        {isGenerating ? '🎙️ 生成中...' : '🚀 开始生成播客'}
      </button>

      {/* URL 解析警告 */}
      {urlWarning && (
        <div className="warning-box">
          <div className="warning-icon">⚠️</div>
          <div className="warning-content">
            <div className="warning-title">网址解析遇到问题</div>
            <div className="warning-message">{urlWarning.message}</div>
            {urlWarning.error_code === '403' && (
              <div className="warning-suggestion">
                💡 <strong>建议操作：</strong>
                <br />
                1. 打开该网址，复制页面中的文本内容
                <br />
                2. 粘贴到上方的"话题文本"输入框中
                <br />
                3. 点击"开始生成播客"继续
              </div>
            )}
          </div>
          <div className="close-warning" onClick={() => setUrlWarning(null)}>×</div>
        </div>
      )}

      {/* 进度显示 */}
      {progress && (
        <div className="progress-bar">
          <div className="progress-text">{progress}</div>
        </div>
      )}

      {/* 播客播放器和封面 - 并排显示 */}
      {((player0Url || player1Url || audioUrl) || coverImage) && (
        <div className="player-cover-container">
          {/* 播客封面 - 左侧 */}
          {coverImage && (
            <div className="cover-section">
              <h2>🖼️ 播客封面</h2>
              <img src={coverImage} alt="播客封面" className="cover-image" />
            </div>
          )}

          {/* 播客播放器 - 右侧 - 双缓冲 */}
          {(player0Url || player1Url || audioUrl) && (
            <div className="player-section">
              <h2>🎧 播客播放器</h2>
              {/* 播放器 0 */}
              <audio
                ref={audioRef0}
                controls={activePlayer === 0}
                className="audio-player"
                src={player0Url || (audioUrl && activePlayer === 0 ? `${API_URL}${audioUrl}` : '')}
                preload="metadata"
                style={{ display: activePlayer === 0 ? 'block' : 'none' }}
              />
              {/* 播放器 1 */}
              <audio
                ref={audioRef1}
                controls={activePlayer === 1}
                className="audio-player"
                src={player1Url || (audioUrl && activePlayer === 1 ? `${API_URL}${audioUrl}` : '')}
                preload="metadata"
                style={{ display: activePlayer === 1 ? 'block' : 'none' }}
              />
            </div>
          )}
        </div>
      )}

      {/* 对话脚本 */}
      {script.length > 0 && (
        <div className="section">
          <h2>📄 对话脚本</h2>
          <div className="script-box">
            {script.map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>
        </div>
      )}

      {/* 下载按钮 */}
      {audioUrl && (
        <div className="download-section">
          <button 
            onClick={() => handleDownload(audioUrl, 'podcast.mp3')} 
            className="download-btn"
          >
            ⬇️ 下载音频
          </button>
          {scriptUrl && (
            <button 
              onClick={() => handleDownload(scriptUrl, 'script.txt')} 
              className="download-btn"
            >
              ⬇️ 下载脚本
            </button>
          )}
          {coverImage && (
            <button 
              onClick={() => handleDownload(`/download/cover?url=${encodeURIComponent(coverImage)}`, 'cover.png')} 
              className="download-btn"
            >
              ⬇️ 下载封面
            </button>
          )}
        </div>
      )}

      {/* 详细日志 */}
      <div className="section logs-section">
        <h2 onClick={() => setShowLogs(!showLogs)} style={{ cursor: 'pointer' }}>
          🔍 详细日志 {showLogs ? '▼' : '▶'}
        </h2>
        {showLogs && (
          <div className="logs-box">
            {logs.map((log, index) => (
              <p key={index}>
                <span className="log-time">[{log.time}]</span> {log.message}
              </p>
            ))}
          </div>
        )}
      </div>

      {/* Trace IDs */}
      {traceIds.length > 0 && (
        <div className="trace-ids">
          <h3>Trace IDs</h3>
          {traceIds.map((trace, index) => (
            <p key={index}>
              <strong>{trace.api}:</strong> <code>{trace.traceId}</code>
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

export default PodcastGenerator;
