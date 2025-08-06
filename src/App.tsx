import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const App = () => {
  const [data, setData] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Health check
  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setData(data.status); // use "status", not "rest"
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching data:", err);
        setError(err.message);
        setLoading(false);
      });
  }, []);

  // Handle file upload
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || file.type !== "application/pdf") {
      setUploadStatus("Please select a valid PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload-pdf", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }
      const result = await res.json();
      console.log(result);
      setUploadStatus("Upload successful!");
    } catch (err) {
      console.error(err);
      setUploadStatus("Upload failed.");
    }
  };

  if (loading) return <div className="slidesynth-home">Loading...</div>;
  if (error) return <div className="slidesynth-home">Error: {error}</div>;

  return (
    <div className="slidesynth-home">
      <p>Backend status: {data}</p>

      <div className="upload-container">
        <button
          className="upload-btn"
          type="button"
          onClick={() => fileInputRef.current?.click()}
        >
          Upload PDF
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: "none" }}
          onChange={handleUpload}
        />
      </div>

      {uploadStatus && <p>{uploadStatus}</p>}
    </div>
  );
};

export default App;
