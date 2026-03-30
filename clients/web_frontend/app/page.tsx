'use client'

import React, { useState } from 'react'

export default function MataMataDashboard() {
  const [url, setUrl] = useState('')
  const [threshold, setThreshold] = useState('5')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      // Pointing to the dockerized fastAPI instance
      const res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, vt_threshold: parseInt(threshold) || 5 })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Scan failed')
      setResult(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="w-full max-w-7xl mx-auto p-8 relative flex flex-col items-center">
      {/* Logo */}
      <div className="mb-8">
        <img 
          src="/project_matamata.jpeg" 
          alt="Project Mata-Mata Logo" 
          className="h-48 w-auto border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]"
        />
      </div>

      <header className="text-center mb-12">
        <h1 className="text-6xl font-black uppercase tracking-tighter mb-4 text-black">
          Project Mata-Mata
        </h1>
        <p className="text-xl text-gray-700 font-medium max-w-2xl mx-auto">
          Consolidates multi-source intelligence (Google Threat Intel, VirusTotal, Web Risk) with Gemini AI for comprehensive URL risk analysis.
        </p>
        
        {/* Scoring Logic Ribbon */}
        <div className="mt-8 flex flex-wrap justify-center gap-4 text-sm font-bold">
          <span className="flex items-center gap-2 bg-[#ff007f] text-white px-4 py-2 rounded-none border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            🔴 DANGER: Core + Verification Hit
          </span>
          <span className="flex items-center gap-2 bg-[#00ffff] text-black px-4 py-2 rounded-none border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            🟢 SAFE: Clean indicator & 0 Detections
          </span>
          <span className="flex items-center gap-2 bg-[#ffff00] text-black px-4 py-2 rounded-none border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            🟡 WARNING: Fallback state
          </span>
        </div>
      </header>

      {/* Input Box */}
      <form onSubmit={handleScan} className="mb-12 relative z-10 bg-white p-6 rounded-none border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex flex-col gap-4 w-full max-w-4xl">
        <div className="flex gap-4">
          <input 
            type="text" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste external URL to scan..." 
            className="flex-grow bg-white text-black px-4 py-3 outline-none placeholder:text-gray-500 text-lg border-2 border-black"
            required
          />
          <button 
            type="submit" 
            disabled={loading}
            className="bg-[#00ffff] hover:bg-[#00dada] text-black font-black py-3 px-8 border-2 border-black transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
          >
            {loading ? 'Scanning...' : 'Analyze Threat'}
          </button>
        </div>
        
        <div className="flex items-center gap-3 text-sm text-black px-4 pt-3">
          <label htmlFor="threshold" className="font-bold">VirusTotal Detection Threshold:</label>
          <input 
            id="threshold"
            type="number" 
            min="1"
            max="100"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="w-14 bg-white text-black px-2 py-1 outline-none text-center border-2 border-black font-bold"
            title="VirusTotal Malicious Threshold"
          />
          <span className="font-medium">(URLs with detections above this number are flagged as Malicious. Default: 5)</span>
        </div>
      </form>

      {/* Loader */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 bg-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] w-full max-max-w-4xl">
           <div className="w-16 h-16 border-4 border-black border-t-[#00ffff] rounded-none animate-spin mb-6"></div>
           <p className="text-black font-black tracking-widest text-sm text-center">
            [1] VALIDATING AGAINST THREAT INTEL...<br />
            [2] DISPATCHING BROWSER INSTANCES...<br />
            [3] RETRIEVING DOM & NETWORK TELEMETRY...<br />
            [4] INITIALIZING GEMINI VISION DETECTORS...<br />
              This will take ~30 seconds.
           </p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-6 bg-[#ff007f] text-white border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] mb-8 w-full max-w-4xl">
          <p className="font-black font-mono tracking-wide">❌ FATAL ERROR: {error}</p>
        </div>
      )}

      {/* Results State */}
      {result && (
        <div className="space-y-6 w-full max-w-4xl">
          
          {/* Global Final Verdict Banner */}
          <div className={`p-6 border-4 border-black flex items-center justify-between shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] ${
            result.final_verdict === "DANGER" ? "bg-[#ff007f] text-white" :
            result.final_verdict === "SAFE" ? "bg-[#00ffff] text-black" :
            "bg-[#ffff00] text-black"
          }`}>
            <div>
              <p className="text-xs mb-1 uppercase tracking-widest font-black">Final Verdict</p>
              <h2 className="text-3xl font-black tracking-wider">
                {result.final_verdict === "DANGER" ? "KNOWN BAD / DANGEROUS" : 
                 result.final_verdict === "SAFE" ? "KNOWN GOOD / SAFE" : 
                 "CAUTION / WARNING"}
              </h2>
              <p className="text-xs mt-1">Aggregated scoring from all intelligence sources.</p>
            </div>
            <div className="text-4xl font-black">
              {result.final_verdict === "DANGER" ? "💀" : result.final_verdict === "SAFE" ? "✅" : "⚠️"}
            </div>
          </div>

          <div className="flex justify-between items-center bg-white p-6 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
            <div>
              <p className="text-gray-500 text-sm mb-1 uppercase tracking-widest font-bold">Target Evaluated</p>
              <h2 className="text-2xl font-mono text-black break-all font-bold">{result.url}</h2>
            </div>
            <div className="text-right">
              <p className="text-gray-500 text-sm mb-1 uppercase tracking-widest font-bold">Type</p>
              <h2 className="text-xl font-mono text-black font-bold">{result.type}</h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
            {Object.entries(result.results || {}).map(([checker, data]: [string, any]) => (
              <div key={checker} className={`bg-white p-6 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] ${
                data.error ? 'border-[#ffff00]' : 
                data.risk_factors?.verdict === 'Malicious' ? 'bg-[#ff007f]/10' : 
                data.risk_factors?.verdict === 'Suspicious' ? 'bg-[#ffff00]/10' :
                'bg-[#00ffff]/10'
              }`}>
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold text-black">{checker === "Google Web Risk" ? "Google Web Risk Eval" : checker}</h3>
                  {data.error ? (
                    <span className="px-3 py-1 text-xs font-bold bg-[#ffff00] text-black border-2 border-black">
                      Error
                    </span>
                  ) : (
                    <>
                      {/* Normal cards show verdict if available */}
                      {checker !== "VirusTotal" ? (
                        <span className={`px-3 py-1 text-xs font-bold border-2 border-black
                          ${data.risk_factors?.verdict === 'Malicious' ? 'bg-[#ff007f] text-white' :
                            data.risk_factors?.verdict === 'Suspicious' ? 'bg-[#ffff00] text-black' :
                            'bg-[#00ffff] text-black'}
                        `}>
                          {data.risk_factors?.verdict || (data.is_malicious ? 'Malicious' : 'Clean')}
                        </span>
                      ) : (
                        /* VirusTotal ONLY shows chip if it is Malicious */
                        data.risk_factors?.verdict === 'Malicious' && (
                          <span className="px-3 py-1 text-xs font-bold bg-[#ff007f] text-white border-2 border-black">
                            Malicious
                          </span>
                        )
                      )}
                    </>
                  )}
                </div>
                
                <p className="text-black font-medium mb-4">{data.summary}</p>
                
                {data.details?.full_analysis && (
                  <div className="mt-4 p-4 bg-black text-white overflow-x-auto border-2 border-black">
                    <p className="text-xs text-gray-400 uppercase tracking-widest mb-2 font-bold">AI Detailed Diagnosis</p>
                    <pre className="text-sm font-mono whitespace-pre-wrap">{data.details.full_analysis}</pre>
                  </div>
                )}
              </div>
            ))}

            {/* Dedicated card for GTI Verdict moved from mockup flow */}
            {result.results?.["VirusTotal"]?.risk_factors?.gti_verdict && (
              <div className="bg-white p-6 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold text-black">GTI Assessment</h3>
                  <span className="px-3 py-1 text-xs font-bold border-2 border-black bg-[#00ffff] text-black">
                    {result.results["VirusTotal"].risk_factors.gti_verdict}
                  </span>
                </div>
                <p className="text-black text-sm">
                  {result.results["VirusTotal"].details?.description || "Google Threat Intelligence verdict extracted from VirusTotal response."}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  )
}
