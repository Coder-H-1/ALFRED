'use client';
import { useEffect, useState, useRef } from 'react';

// ZoneWindow component handles the styling for a window inside a zone
function ZoneWindow({ title, children, visible }) {
  if (!visible) return null;
  return (
    <div className="box box-elevated zone-window visible">
      {title && <h3>{title}</h3>}
      {children}
    </div>
  );
}

function VisualizerCanvas({ analyserRef, isAudioSpeaking }) {
  const canvasRef = useRef(null);
  
  useEffect(() => {
    let animationId;
    const draw = () => {
      animationId = requestAnimationFrame(draw);
      if (!canvasRef.current || !analyserRef.current) return;
      
      const analyser = analyserRef.current;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      analyser.getByteTimeDomainData(dataArray);
      
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);
      if (!isAudioSpeaking) return;

      ctx.lineWidth = 3;
      ctx.strokeStyle = '#0088FF';
      ctx.beginPath();
      const sliceWidth = width * 1.0 / bufferLength;
      let x = 0;
      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * height / 2;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        x += sliceWidth;
      }
      ctx.lineTo(width, height / 2);
      ctx.stroke();
    };
    draw();
    return () => cancelAnimationFrame(animationId);
  }, [analyserRef, isAudioSpeaking]);

  return (
    <canvas ref={canvasRef} width="350" height="60" style={{width: '100%', height: '60px', display: 'block'}}></canvas>
  );
}

export default function Home() {
  const [config, setConfig] = useState(null);
  const [shapes, setShapes] = useState([]);
  
  const [displayedAnswer, setDisplayedAnswer] = useState('');
  const [inputText, setInputText] = useState('');
  const [realTimeLogs, setRealTimeLogs] = useState('');
  
  const logsEndRef = useRef(null);
  const inputRef = useRef(null);

  const canvasRef = useRef(null);
  const [isAudioSpeaking, setIsAudioSpeaking] = useState(false);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const silenceTimerRef = useRef(null);

  const videoRefs = useRef([]);
  const zonesRef = useRef({});
  const lastErrorRef = useRef(0);

  // Check for overflow in zones (Removed)
  // Web Audio API Setup
  useEffect(() => {
    let animationId;
    async function initAudio() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        audioContextRef.current = audioCtx;
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        analyserRef.current = analyser;
        
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        sourceRef.current = source;

        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkSpeaking = () => {
          animationId = requestAnimationFrame(checkSpeaking);
          if (!analyserRef.current) return;
          
          analyser.getByteTimeDomainData(dataArray);
          
          let sumSquares = 0;
          for (let i = 0; i < bufferLength; i++) {
            const val = (dataArray[i] - 128) / 128.0;
            sumSquares += val * val;
          }
          const rms = Math.sqrt(sumSquares / bufferLength);
          
          if (rms > 0.05) {
             setIsAudioSpeaking(true);
             if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
             silenceTimerRef.current = setTimeout(() => setIsAudioSpeaking(false), 2000);
          }
        };
        checkSpeaking();
      } catch (err) {
        console.error("Microphone access denied or error:", err);
      }
    }
    
    initAudio();
    
    return () => {
       if (animationId) cancelAnimationFrame(animationId);
       if (audioContextRef.current) audioContextRef.current.close();
    };
  }, []);

  const handleUserInteraction = () => {
    if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
  };

  const orbRef = useRef(null);

  // Poll config
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/config');
        if (res.ok) {
          const data = await res.json();
          setConfig(data);
        }
      } catch (err) {
        console.error(err);
      }
    }, 300);
    return () => clearInterval(interval);
  }, []);

  // Answer text word-by-word
  const targetTextRef = useRef('');
  const displayedLengthRef = useRef(0);
  const answerEndRef = useRef(null);

  useEffect(() => {
    if (config?.answerBox?.visible) {
      const currentFullText = config.answerBox.text || '';
      
      if (currentFullText.length === 0) {
        setDisplayedAnswer('');
        targetTextRef.current = '';
        displayedLengthRef.current = 0;
        return;
      }
      
      if (!currentFullText.startsWith(targetTextRef.current)) {
        setDisplayedAnswer('');
        displayedLengthRef.current = 0;
      }
      
      targetTextRef.current = currentFullText;
      
      const typeInterval = setInterval(() => {
        if (displayedLengthRef.current < targetTextRef.current.length) {
          const remaining = targetTextRef.current.substring(displayedLengthRef.current);
          const match = remaining.match(/^(\s*\S+\s*)/);
          const chunk = match ? match[0] : remaining;
          
          displayedLengthRef.current += chunk.length;
          setDisplayedAnswer(targetTextRef.current.substring(0, displayedLengthRef.current));
          
          if (chunk.trim().length > 0 && orbRef.current) {
             orbRef.current.style.transform = 'translate(-50%, -50%) scale(1.15)';
             setTimeout(() => {
                if (orbRef.current) orbRef.current.style.transform = 'translate(-50%, -50%) scale(1)';
             }, 150);
          }
        } else {
          clearInterval(typeInterval);
        }
      }, 50);
      
      return () => clearInterval(typeInterval);
    }
  }, [config?.answerBox?.visible, config?.answerBox?.text]);

  // Handle Video Controls (Mute, Seek)
  useEffect(() => {
    if (config?.videoControls && videoRefs.current.length > 0) {
      const { muted, seekOffset, seekDirection } = config.videoControls;
      
      videoRefs.current.forEach(video => {
        if (video) {
          if (video.muted !== muted) video.muted = muted;
          
          if (seekOffset > 0 && seekDirection) {
             if (seekDirection === 'forward') {
                video.currentTime += seekOffset;
             } else if (seekDirection === 'back') {
                video.currentTime -= seekOffset;
             }
          }
        }
      });
    }
  }, [config?.videoControls]);

  // Auto-scroll answer
  useEffect(() => {
    if (answerEndRef.current) {
      answerEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [displayedAnswer]);

  // Poll real-time logs
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('/api/logs');
        if (res.ok) {
          const data = await res.json();
          setRealTimeLogs(data.logs || '');
        }
      } catch (err) {
        console.error(err);
      }
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [realTimeLogs]);

  // Auto-focus command input when shown
  useEffect(() => {
    if (config?.commandInput && inputRef.current) {
      inputRef.current.focus();
    }
  }, [config?.commandInput]);

  // Query Active animation (Shapes)
  useEffect(() => {
    if (config?.queryActive) {
      const shapeInterval = setInterval(() => {
        const types = ['square', 'circle', 'pill', 'triangle', 'diamond', 'hexagon', 'star', 'cross', 'pentagon', 'octagon'];
        const type = types[Math.floor(Math.random() * types.length)];
        
        const angle = Math.random() * Math.PI * 2;
        const radius = Math.random() > 0.5 ? 300 + Math.random() * 200 : 2000 + Math.random() * 3000;
        const x = window.innerWidth / 2 + Math.cos(angle) * radius;
        const y = window.innerHeight / 2 + Math.sin(angle) * radius;

        const newShape = { id: Date.now() + Math.random(), type, startX: x, startY: y, angle, radius };
        setShapes(prev => [...prev, newShape]);

        setTimeout(() => {
          setShapes(prev => prev.map(s => s.id === newShape.id ? { ...s, pulled: true } : s));
          setTimeout(() => {
            setShapes(prev => prev.filter(s => s.id !== newShape.id));
          }, 600);
        }, 100);
      }, 75);

      return () => clearInterval(shapeInterval);
    } else {
       setShapes([]);
    }
  }, [config?.queryActive]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: inputText })
    });
    setInputText('');
  };

  if (!config) return <div className="container"><div className="alfred-core"><div className="alfred-core-inner"></div></div></div>;

  // Group windows by zone
  const getWindowsForZone = (zoneName) => {
    const windows = [];
    
    // 1. Visualizer (Bottom-most in its assigned zone)
    if (config.visualizer?.zone === zoneName) {
        windows.push(
          <div key="visualizer" className="box box-elevated visible" style={{ padding: '10px', position: 'fixed', bottom: '20px', right: '20px', width: '280px' }}>
             <VisualizerCanvas analyserRef={analyserRef} isAudioSpeaking={isAudioSpeaking} />
          </div>
        );
    }
    
    // 2. Status Text / Input (Only in Passive zone, above visualizer if present)
    if (zoneName === 'passive') {
        windows.push(
          <div key="statusText" className="input-area command-input-container" style={{ marginTop: 0, pointerEvents: 'auto', display: 'inline-block', width: 'auto', position: 'fixed', bottom: '20px', right: '350px' }}>
               {config.commandInput ? (
                 <form onSubmit={handleSubmit}>
                   <input 
                     ref={inputRef}
                     type="text" 
                     value={inputText}
                     onChange={e => setInputText(e.target.value)}
                     placeholder="Type your command..." 
                     autoFocus
                     className="command-input"
                   />
                 </form>
               ) : (
                 config.statusText ? (
                   <div className="status-text" style={{ whiteSpace: 'nowrap' }}>{config.statusText}</div>
                 ) : null
               )}
          </div>
        );
    }
    
    // Real-time logs are permanently pinned to bottom-left outside zone container.
    
    // 5. Preview (ShowBox)
    if (config.showBox?.zone === zoneName && config.showBox?.visible) {
      windows.push(
        <ZoneWindow key="showBox" title="Preview" visible={true}>
          <div className="show-content">
            <div className="image-stack" style={{ display: config.videoControls?.audioOnly ? 'none' : 'block', height: zoneName === 'focus' ? '60vh' : '300px' }}>
               {config.showBox.data && config.showBox.data.map((item, idx) => {
                   if (typeof item === 'string' && item.startsWith('youtube:')) {
                       const videoId = item.replace('youtube:', '');
                       return (
                           <iframe 
                               key={idx}
                               src={`https://www.youtube.com/embed/${videoId}?autoplay=1`} 
                               title="YouTube video player" 
                               frameBorder="0" 
                               allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                               allowFullScreen
                               className="stacked-image"
                               style={{ transform: `rotate(${(idx - (config.showBox.data.length/2)) * 3}deg) scale(${1 - idx * 0.03})`, zIndex: config.showBox.data.length - idx }}
                           ></iframe>
                       );
                   }
                   if (typeof item === 'string' && item.startsWith('video:')) {
                       const videoUrl = item.replace('video:', '');
                       return (
                           <video 
                               ref={el => videoRefs.current[idx] = el}
                               key={idx}
                               src={videoUrl} 
                               autoPlay 
                               controls
                               className="stacked-image"
                               style={{ transform: `rotate(${(idx - (config.showBox.data.length/2)) * 3}deg) scale(${1 - idx * 0.03})`, zIndex: config.showBox.data.length - idx }}
                           ></video>
                       );
                   }
                   return (
                       <img 
                         key={idx} 
                         src={item} 
                         className="stacked-image" 
                         style={{ transform: `rotate(${(idx - (config.showBox.data.length/2)) * 3}deg) scale(${1 - idx * 0.03})`, zIndex: config.showBox.data.length - idx }} 
                         alt="preview"
                       />
                   );
               })}
            </div>
            {config.videoControls?.audioOnly && (
               <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff'}}>
                 <i>Playing Audio Only</i>
               </div>
            )}
          </div>
        </ZoneWindow>
      );
    }
    
    // 6. Response (AnswerBox)
    if (config.answerBox?.zone === zoneName && config.answerBox?.visible) {
      windows.push(
        <ZoneWindow key="answerBox" title="Response" visible={true}>
          <div className="answer-content" style={{height: '100%'}}>
            <p>
              {displayedAnswer}
              <span ref={answerEndRef} />
            </p>
          </div>
        </ZoneWindow>
      );
    }
    
    return windows;
  };

  return (
    <div className="container" onClick={handleUserInteraction}>
      {/* Background Shapes */}
      {shapes.map(s => {
         const currentX = s.pulled ? window.innerWidth / 2 : s.startX;
         const currentY = s.pulled ? window.innerHeight / 2 : s.startY;
         const opacity = s.pulled ? 0 : 1;
         return (
           <div 
             key={s.id} 
             className={`shape ${s.type}`} 
             style={{
               left: currentX, 
               top: currentY, 
               opacity: opacity,
               transform: `translate(-50%, -50%) ${s.pulled ? 'scale(0.1)' : 'scale(1)'}`
             }} 
           />
         );
      })}

      {/* NEW: Zone Layout System */}
      <div className="zone-container">
        <div className="zone zone-active" ref={el => zonesRef.current['active'] = el}>
          {getWindowsForZone('active')}
        </div>
        
        <div className="zone zone-focus" ref={el => zonesRef.current['focus'] = el}>
          {getWindowsForZone('focus')}
        </div>
        
        <div className="zone zone-passive" ref={el => zonesRef.current['passive'] = el}>
          {getWindowsForZone('passive')}
        </div>
        
        <div className="zone zone-rapid" ref={el => zonesRef.current['rapid'] = el}>
          {getWindowsForZone('rapid')}
        </div>
      </div>

      {/* Error Update Zone Overlay (Removed) */}

      {/* Core Orb (Center Locked) */}
      <div 
        ref={orbRef} 
        style={{ 
          transition: 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)', 
          zIndex: 10, 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)'
        }}
        onClick={() => {
           if (orbRef.current) {
               orbRef.current.style.transform = 'translate(-50%, -50%) scale(1.4) rotate(90deg)';
               setTimeout(() => {
                   if (orbRef.current) {
                      orbRef.current.style.transform = 'translate(-50%, -50%) scale(1) rotate(0deg)';
                   }
               }, 300);
           }
        }}
      >
        <div className="alfred-core">
          <div className="alfred-core-inner"></div>
        </div>
      </div>

      {/* Pinned Real-time System Logs */}
      <div 
        className="box box-elevated visible" 
        style={{ 
          position: 'fixed', 
          bottom: '20px', 
          left: '20px', 
          width: '352px', 
          maxHeight: '220px', 
          pointerEvents: 'auto',
          zIndex: 9,
          margin: 0
        }}
      >
        <h3 style={{margin: '0 0 10px 0'}}>System Logs</h3>
        <div className="logs-content" style={{ maxHeight: '160px', overflowY: 'auto' }}>
          <pre style={{ color: '#b0b0b0', whiteSpace: 'pre-wrap', margin: 0, fontSize: '11px', fontFamily: 'monospace' }}>
            {realTimeLogs}
            <div ref={logsEndRef} />
          </pre>
        </div>
      </div>
    </div>
  );
}
