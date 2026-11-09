'use client';
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="account"><h1>Something interrupted the connection.</h1><p>Your changes may not have been saved. Please retry. If this continues, check the backend configuration.</p><button onClick={reset}>Try again</button></main>; }
