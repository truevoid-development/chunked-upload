"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks

const UploadPage: React.FC = () => {
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]; // Assume single file upload for simplicity
    if (!file) return;

    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min((chunkIndex + 1) * CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);

      const formData = new FormData();
      formData.append("file", chunk, file.name);
      formData.append("chunkIndex", chunkIndex.toString());
      formData.append("totalChunks", totalChunks.toString());

      try {
        const response = await axios.post("/api/upload", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
            "Content-Range": `bytes ${start}-${end - 1}/${file.size}`,
          },
        });

        if (response.status === 200) {
          setUploadProgress(100);
          console.log("Upload completed");
          break;
        } else {
          const progress = ((chunkIndex + 1) / totalChunks) * 100;
          setUploadProgress(Math.round(progress));
        }
      } catch (error) {
        console.error("Error uploading chunk:", error);
        break;
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Large File Uploader</h1>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed p-8 text-center cursor-pointer ${
          isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"
        }`}
      >
        <input {...getInputProps()} />
        {isDragActive
          ? <p>Drop the files here ...</p>
          : <p>Drag 'n' drop some files here, or click to select files</p>}
      </div>
      {uploadProgress > 0 && (
        <div className="mt-4">
          <p>Upload Progress: {uploadProgress}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${uploadProgress}%` }}
            >
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadPage;
