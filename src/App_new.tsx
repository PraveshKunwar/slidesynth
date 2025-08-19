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
  pptx_path?: string;
}

type ProcessingState =
  | "idle"
  | "uploading"
  | "processing"
  | "generating"
  | "success"
  | "error";

const App = () => {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [processingState, setProcessingState] =
    useState<ProcessingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
  const [uploadProgress, setUploadProgress] = useState<string>("");
  const [filename, setFilename] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || file.type !== "application/pdf") {
      setError("Please select a valid PDF file.");
      return;
    }

    setProcessingState("uploading");
    setError(null);
    setUploadProgress("Uploading PDF...");
    setSlides([]);
    setCurrentSlideIndex(0);
    setFilename(file.name);

    const formData = new FormData();
    formData.append("file", file);

    try {
      setProcessingState("processing");
      setUploadProgress("Processing PDF and extracting text...");

      const res = await fetch("/api/upload-pdf", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error(`Upload failed: ${res.status}`);
      }

      setProcessingState("generating");
      setUploadProgress("Generating slides with AI...");

      const result: UploadResponse = await res.json();

      if (result.success && result.slides) {
        setSlides(result.slides);
        setProcessingState("success");
        setUploadProgress(
          `Successfully generated ${result.total_slides} slides from ${result.filename}`
        );
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Upload failed";
      setError(errorMessage);
      setProcessingState("error");
      setUploadProgress("Upload failed.");
    }
  };

  const handleDownloadPPTX = async () => {
    if (!filename) return;

    try {
      const cleanFilename = filename.replace(".pdf", "");
      const response = await fetch(`/api/download-pptx/${cleanFilename}`);

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${cleanFilename}_slides.pptx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        throw new Error("Download failed");
      }
    } catch (err) {
      setError("Failed to download PPTX file");
    }
  };

  const resetUpload = () => {
    setSlides([]);
    setError(null);
    setUploadProgress("");
    setCurrentSlideIndex(0);
    setFilename("");
    setProcessingState("idle");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const getStatusIcon = () => {
    switch (processingState) {
      case "uploading":
        return "⬆️";
      case "processing":
        return "📄";
      case "generating":
        return "🤖";
      case "success":
        return "✅";
      case "error":
        return "❌";
      default:
        return "📁";
    }
  };

  return (
    <div className="slidesynth-home">
      <header className="app-header">
        <h1 className="app-title">SlideSynth</h1>
        <p className="app-subtitle">
          Transform PDFs into professional presentation slides with AI
        </p>
      </header>

      {/* Upload Container - Always visible */}
      <div className="upload-container">
        <div className="upload-icon">{getStatusIcon()}</div>

        <div className="upload-content">
          <h3>Upload Your PDF</h3>
          <p>Transform your documents into beautiful presentations with AI</p>

          <button
            className="upload-btn"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={processingState !== "idle"}
          >
            {processingState === "idle" ? "Choose PDF File" : "Processing..."}
            {processingState !== "idle" &&
              processingState !== "success" &&
              processingState !== "error" && (
                <div className="loading-spinner"></div>
              )}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="upload-input"
            onChange={handleUpload}
          />
        </div>

        {uploadProgress && (
          <div
            className={`upload-status ${
              processingState === "success"
                ? "success"
                : processingState === "error"
                ? "error"
                : "processing"
            }`}
          >
            {processingState !== "idle" &&
              processingState !== "success" &&
              processingState !== "error" && (
                <div className="loading-spinner"></div>
              )}
            {uploadProgress}
          </div>
        )}

        {error && (
          <div className="upload-status error">
            {error}
            <button
              className="retry-btn"
              onClick={resetUpload}
              style={{
                marginLeft: "10px",
                padding: "5px 10px",
                fontSize: "12px",
              }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Success State with Slides */}
      {processingState === "success" && slides.length > 0 && (
        <div className="slides-preview">
          <div className="preview-header">
            <h2>Generated Slides ({slides.length})</h2>
            <div className="preview-actions">
              <button className="download-btn" onClick={handleDownloadPPTX}>
                📥 Download PPTX
              </button>
              <button className="new-upload-btn" onClick={resetUpload}>
                🔄 New Upload
              </button>
            </div>
          </div>

          <div className="slides-grid">
            {slides.map((slide, index) => (
              <div
                key={index}
                className={`slide-thumbnail ${
                  index === currentSlideIndex ? "active" : ""
                }`}
                onClick={() => setCurrentSlideIndex(index)}
              >
                <div className="slide-number">{index + 1}</div>
                <div className="slide-content">
                  <h3 className="slide-title">{slide.title}</h3>
                  <div className="slide-bullets">
                    {slide.bullets.slice(0, 3).map((bullet, i) => (
                      <div key={i} className="bullet-point">
                        •{" "}
                        {bullet.length > 50
                          ? bullet.substring(0, 50) + "..."
                          : bullet}
                      </div>
                    ))}
                    {slide.bullets.length > 3 && (
                      <div className="bullet-more">
                        +{slide.bullets.length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {slides[currentSlideIndex] && (
            <div className="slide-detail">
              <div className="slide-header">
                <h2 className="detail-title">
                  {slides[currentSlideIndex].title}
                </h2>
                <div className="slide-counter">
                  {currentSlideIndex + 1} of {slides.length}
                </div>
              </div>
              <div className="slide-body">
                {slides[currentSlideIndex].bullets.map((bullet, i) => (
                  <div key={i} className="detail-bullet">
                    <span className="bullet-marker">•</span>
                    <span className="bullet-text">{bullet}</span>
                  </div>
                ))}
              </div>
              <div className="slide-navigation">
                <button
                  className="nav-btn prev"
                  onClick={() =>
                    setCurrentSlideIndex(Math.max(0, currentSlideIndex - 1))
                  }
                  disabled={currentSlideIndex === 0}
                >
                  ← Previous
                </button>
                <button
                  className="nav-btn next"
                  onClick={() =>
                    setCurrentSlideIndex(
                      Math.min(slides.length - 1, currentSlideIndex + 1)
                    )
                  }
                  disabled={currentSlideIndex === slides.length - 1}
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default App;
