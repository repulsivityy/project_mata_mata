'use client'

import React, { useState } from 'react'

export default function MataMataDashboard() {
  const [url, setUrl] = useState('')
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
      const res = await fetch(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
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
    <main className="max-w-4xl mx-auto p-8 relative">

      {/* Header section with glowing threat radar vibe */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[300px] bg-blue-600/20 blur-[120px] rounded-full -z-10 pointer-events-none" />
      
      <header className="text-center mb-12 mt-12">
        <h1 className="text-5xl font-extrabold tracking-tight mb-4 tracking-tighter bg-gradient-to-br from-white to-gray-400 bg-clip-text text-transparent">
          Project Mata-Mata
        </h1>
        <p className="text-gray-400 text-lg">Threat Intelligence & Phishing Analysis</p>
      </header>

      {/* Input Box */}
      <form onSubmit={handleScan} className="flex gap-4 mb-12 relative z-10 glassmorphism p-2 rounded-2xl">
        <input 
          type="text" 
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste external URL to scan..." 
          className="w-full bg-transparent text-white px-6 py-4 outline-none placeholder:text-gray-500 text-lg"
          required
        />
        <button 
          type="submit" 
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-4 px-10 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap shadow-[0_0_20px_rgba(37,99,235,0.4)] hover:shadow-[0_0_30px_rgba(37,99,235,0.6)]"
        >
          {loading ? 'Scanning...' : 'Analyze Threat'}
        </button>
      </form>

      {/* Loader */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 animate-pulse">
           <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-6"></div>
           <p className="text-blue-400 animate-pulse font-mono tracking-widest text-sm text-center">
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
        <div className="glassmorphism p-6 rounded-2xl border-red-500/30 bg-red-500/10 mb-8">
          <p className="text-red-400 font-mono tracking-wide">❌ FATAL ERROR: {error}</p>
        </div>
      )}

      {/* Results State */}
      {result && (
        <div className="space-y-6 animate-in slide-in-from-bottom-8 fade-in duration-700">
          
          {/* Global Final Verdict Banner */}
          <div className={`p-6 rounded-2xl border flex items-center justify-between glassmorphism ${
            result.final_verdict === "DANGER" ? "border-red-500/50 bg-red-500/10" :
            result.final_verdict === "SAFE" ? "border-emerald-500/30 bg-emerald-500/10" :
            "border-yellow-500/30 bg-yellow-500/10"
          }`}>
            <div>
              <p className="text-gray-400 text-xs mb-1 uppercase tracking-widest font-bold">Final Verdict</p>
              <h2 className={`text-3xl font-bold tracking-wider ${
                result.final_verdict === "DANGER" ? "text-red-400" :
                result.final_verdict === "SAFE" ? "text-emerald-400" :
                "text-yellow-400"
              }`}>
                {result.final_verdict === "DANGER" ? "KNOWN BAD / DANGEROUS" : 
                 result.final_verdict === "SAFE" ? "KNOWN GOOD / SAFE" : 
                 "CAUTION / WARNING"}
              </h2>
              <p className="text-gray-400 text-xs mt-1">Aggregated scoring from all intelligence sources.</p>
            </div>
            <div className={`text-4xl ${
              result.final_verdict === "DANGER" ? "text-red-500" :
              result.final_verdict === "SAFE" ? "text-emerald-500" :
              "text-yellow-500"
            }`}>
              {result.final_verdict === "DANGER" ? "💀" : result.final_verdict === "SAFE" ? "✅" : "⚠️"}
            </div>
          </div>

          <div className="flex justify-between items-center glassmorphism p-6 rounded-2xl">
            <div>
              <p className="text-gray-400 text-sm mb-1 uppercase tracking-widest font-bold">Target Evaluated</p>
              <h2 className="text-2xl font-mono text-blue-300 break-all">{result.url}</h2>
            </div>
            <div className="text-right">
              <p className="text-gray-400 text-sm mb-1 uppercase tracking-widest font-bold">Type</p>
              <h2 className="text-xl font-mono text-white">{result.type}</h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
            {Object.entries(result.results || {}).map(([checker, data]: [string, any]) => (
              <div key={checker} className={`glassmorphism p-6 rounded-2xl border ${data.error ? 'border-yellow-500/30' : data.is_malicious ? 'border-red-500/50 bg-red-500/5' : 'border-emerald-500/30 bg-emerald-500/5'}`}>
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">{checker === "Google Web Risk" ? "Google Web Risk Eval" : checker}</h3>
                  {checker !== "VirusTotal" ? (
                    <span className={`px-3 py-1 text-xs font-bold rounded-full tracking-widest uppercase
                      ${data.error ? 'bg-yellow-500/20 text-yellow-300' :
                        data.is_malicious ? 'bg-red-500/20 text-red-400 border border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.3)]' :
                          'bg-emerald-500/20 text-emerald-400'}
                    `}>
                      {data.error ? 'Error' : data.is_malicious ? 'Malicious' : 'Clean'}
                    </span>
                  ) : data.error ? (
                    <span className="px-3 py-1 text-xs font-bold rounded-full tracking-widest uppercase bg-yellow-500/20 text-yellow-300">
                      Error
                    </span>
                  ) : null}
                </div>
                
                <p className="text-gray-300 font-medium mb-4">{data.summary}</p>
                
                {data.details?.full_analysis && (
                  <div className="mt-4 p-4 bg-black/40 rounded-xl overflow-x-auto border border-white/5">
                    <p className="text-xs text-gray-500 uppercase tracking-widest mb-2 font-bold">AI Detailed Diagnosis</p>
                    <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">{data.details.full_analysis}</pre>
                  </div>
                )}
              </div>
            ))}

            {/* Dedicated card for GTI Verdict moved from mockup flow */}
            {result.results?.["VirusTotal"]?.risk_factors?.gti_verdict && (
              <div className="glassmorphism p-6 rounded-2xl border border-blue-500/30 bg-blue-500/5">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-bold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">GTI Assessment</h3>
                  <span className="px-3 py-1 text-xs font-bold rounded-full tracking-widest uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                    {result.results["VirusTotal"].risk_factors.gti_verdict}
                  </span>
                </div>
                <p className="text-gray-400 text-sm">
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
