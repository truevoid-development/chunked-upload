import type { NextApiRequest, NextApiResponse } from "next";
import axios from "axios";
import formidable from "formidable";
import fs from "fs";

// Disable the default body parser
export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method === "POST") {
    // Parse the multipart form data
    const form = new formidable.IncomingForm();
    form.parse(req, async (err, fields, files) => {
      if (err) {
        return res.status(500).json({ error: "Error parsing form data" });
      }

      const file = files.file as formidable.File;
      const chunkIndex = fields.chunkIndex as string;
      const totalChunks = fields.totalChunks as string;

      // Read the file
      const fileData = fs.readFileSync(file.filepath);

      try {
        // Forward the request to your Python backend
        const response = await axios.post(
          "http://your-python-backend-url/upload",
          fileData,
          {
            headers: {
              "Content-Type": req.headers["content-type"] ||
                "application/octet-stream",
              "Content-Range": req.headers["content-range"],
              "X-Chunk-Index": chunkIndex,
              "X-Total-Chunks": totalChunks,
            },
          },
        );

        // Return the response from the Python backend
        res.status(response.status).json(response.data);
      } catch (error) {
        console.error("Error forwarding request to Python backend:", error);
        res.status(500).json({ error: "Error forwarding request to backend" });
      } finally {
        // Clean up the temp file
        fs.unlinkSync(file.filepath);
      }
    });
  } else {
    // Handle any non-POST requests
    res.setHeader("Allow", ["POST"]);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
