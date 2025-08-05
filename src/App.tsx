import React, { useState, useEffect } from "react";
import "./App.css";

const App = () => {
  const [data, setData] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setData(data.rest);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching data:", err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="slidesynth-home">Loading...</div>;
  if (error) return <div className="slidesynth-home">Error: {error}</div>;

  return <div className="slidesynth-home">{data}</div>;
};

export default App;
