import React, { useState, useRef } from "react";
import "./App.css";

interface Slide {
  title: string;
  bullets: string[];
}

interface UploadResponse {
  success: boolean;
  filename: string;
  total_chunks: number;
  total_slides: number;
  slides: Slide[];
}

const App = () => {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || file.type !== "application/pdf") {
      setUploadStatus("Please select a valid PDF file.");
      return;
    }

    setLoading(true);
    setError(null);
    setUploadStatus("Processing PDF...");
    setSlides([]);
    setCurrentSlideIndex(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload-pdf", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed: ${res.status}`);
      }

      const result: UploadResponse = await res.json();

      if (result.success && result.slides) {
        setSlides(result.slides);
        console.log(result.slides);
        setUploadStatus(
          `Successfully generated ${result.total_slides} slides from ${result.filename}`
        );
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Upload failed";
      setError(errorMessage);
      setUploadStatus("Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const nextSlide = () => {
    if (currentSlideIndex < slides.length - 1) {
      setCurrentSlideIndex(currentSlideIndex + 1);
    }
  };

  const prevSlide = () => {
    if (currentSlideIndex > 0) {
      setCurrentSlideIndex(currentSlideIndex - 1);
    }
  };

  const resetUpload = () => {
    setSlides([]);
    setError(null);
    setUploadStatus(null);
    setCurrentSlideIndex(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="slidesynth-home">
      <h1 className="app-title">SlideSynth</h1>
      <p className="app-subtitle">
        Transform PDFs into presentation slides with AI
      </p>

      {slides.length === 0 && (
        <div className="upload-container">
          <button
            className="upload-btn"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            {loading ? "Processing..." : "Upload PDF"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
            onChange={handleUpload}
          />
          <p className="upload-hint">Select a PDF file to generate slides</p>
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>{uploadStatus}</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button className="retry-btn" onClick={resetUpload}>
            Try Again
          </button>
        </div>
      )}

      {uploadStatus && !loading && !error && slides.length > 0 && (
        <div className="success-container">
          <p className="success-message">{uploadStatus}</p>
        </div>
      )}

      {slides.length > 0 && (
        <div className="slides-container">
          <div className="slide-navigation">
            <button
              className="nav-btn"
              onClick={prevSlide}
              disabled={currentSlideIndex === 0}
            >
              ← Previous
            </button>
            <span className="slide-counter">
              Slide {currentSlideIndex + 1} of {slides.length}
            </span>
            <button
              className="nav-btn"
              onClick={nextSlide}
              disabled={currentSlideIndex === slides.length - 1}
            >
              Next →
            </button>
          </div>

          <div className="slide-display">
            <h2 className="slide-title">{slides[currentSlideIndex]?.title}</h2>
            <ul className="slide-bullets">
              {slides[currentSlideIndex]?.bullets.map((bullet, index) => (
                <li key={index} className="slide-bullet">
                  {bullet}
                </li>
              ))}
            </ul>
          </div>

          <button className="new-upload-btn" onClick={resetUpload}>
            Upload New PDF
          </button>
        </div>
      )}
    </div>
  );
};

export default App;
