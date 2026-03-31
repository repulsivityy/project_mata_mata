import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const apiKey = process.env.MATA_API_KEY;
    const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/scan';

    if (!apiKey) {
      console.error("❌ MATA_API_KEY is not set on the Next.js server!");
      return NextResponse.json({ detail: "Server misconfiguration: MATA_API_KEY is not set on the server." }, { status: 500 });
    }

    console.log(`📡 Proxying request to: ${apiUrl}`);

    const res = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': apiKey,
      },
      body: JSON.stringify(body),
    });

    // Check if the response is JSON
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    } else {
      const text = await res.text();
      console.error(`❌ Backend returned non-JSON response: ${text}`);
      return NextResponse.json({ detail: "Backend returned an invalid response format." }, { status: 500 });
    }
  } catch (error: any) {
    console.error(`❌ Proxy error: ${error.message}`);
    return NextResponse.json({ detail: error.message || "Failed to proxy request" }, { status: 500 });
  }
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const jobId = searchParams.get('job_id');
    const apiKey = process.env.MATA_API_KEY;
    const apiUrlBase = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1/scan';
    const statusUrl = `${apiUrlBase.replace('/scan', '/scan/status')}/${jobId}`;

    if (!jobId) {
      return NextResponse.json({ detail: "Missing job_id parameter" }, { status: 400 });
    }

    if (!apiKey) {
      return NextResponse.json({ detail: "Server misconfiguration: MATA_API_KEY is not set on the server." }, { status: 500 });
    }

    console.log(`📡 GET Proxying status request to: ${statusUrl}`);

    const res = await fetch(statusUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'X-API-KEY': apiKey,
      },
    });

    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    } else {
      const text = await res.text();
      console.error(`❌ Backend returned non-JSON response for GET status: ${text}`);
      return NextResponse.json({ detail: "Backend returned an invalid response format." }, { status: 500 });
    }
  } catch (error: any) {
    console.error(`❌ GET Proxy error: ${error.message}`);
    return NextResponse.json({ detail: error.message || "Failed to proxy request" }, { status: 500 });
  }
}
