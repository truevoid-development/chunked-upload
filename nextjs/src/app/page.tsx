"use client";

import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";

import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { faCancel, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import prettyBytes from "pretty-bytes";

const queryClient = new QueryClient();

const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks

interface Object {
  path: string;
  completed: boolean;
  finalizing: boolean;
  nBytes: number;
  uploadedChunks: number;
  totalChunks: number;
}

interface ObjectList {
  items: Array<Object>;
}

function Objects(): React.ReactNode {
  const { data, refetch } = useQuery<ObjectList>({
    queryKey: ["objects"],
    queryFn: () => fetch("/api/objects").then((res) => res.json()),
    staleTime: 1000,
    refetchInterval: 1000,
  });

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
        const response = await axios.post("/api/objects", formData, {
          headers: {
            "Content-Type": "multipart/form-data",
            "Content-Range": `bytes ${start}-${end - 1}/${file.size}`,
          },
        });

        if (response.status === 200) {
          console.log("Upload completed");
          refetch();
          break;
        } else {
          refetch();
        }
      } catch (error) {
        console.error("Error uploading chunk:", error);
        break;
      }
    }
  }, []);

  const actions = (filename: string, completed: boolean): React.ReactNode => {
    return (
      <>
        {completed
          ? (
            <FontAwesomeIcon
              icon={faTrash}
              className="cursor-pointer text-red-500 hover:text-red-300"
              onClick={() => {
                axios.delete(`/api/objects/${filename}`).then(() => {
                  refetch();
                });
              }}
            />
          )
          : <FontAwesomeIcon icon={faCancel} className="cursor-pointer" />}
      </>
    );
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop });

  return (
    <div className="container mx-auto p-4 space-y-2">
      <h1 className="text-2xl font-bold mb-4">Chunked Upload</h1>

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
      <table className="table-auto w-full space-y-3 text-center py-8">
        <thead>
          <tr>
            <th>File</th>
            <th>Size</th>
            <th>Progress</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data === undefined ? <></> : data.items.map((item) => {
            return (
              <tr key={item.path}>
                <td>{item.path.slice(1)}</td>
                <td>{prettyBytes(item.nBytes)}</td>
                <td>
                  {item.completed
                    ? "Completed"
                    : (item.finalizing
                      ? `Finalizing: ${
                        Math.ceil(
                          100 * (1.0 - item.uploadedChunks / item.totalChunks),
                        )
                      }%`
                      : `Uploading: ${
                        Math.ceil(100 * item.uploadedChunks / item.totalChunks)
                      }%`)}
                </td>
                <td>{actions(item.path.slice(1), item.completed)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function UploadPage(): React.ReactNode {
  return (
    <QueryClientProvider client={queryClient}>
      <Objects />
    </QueryClientProvider>
  );
}

export default UploadPage;
