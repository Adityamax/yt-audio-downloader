from flask import Flask, render_template_string, request, send_file, jsonify
import subprocess
import os
import uuid

app = Flask(__name__)

# === HTML FRONT PAGE ===
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YouTube Downloader</title>
<style>
body { font-family: Arial; background: #111; color: #fff; text-align: center; margin-top: 50px; }
input, select, button { padding: 10px; margin: 8px; border-radius: 5px; border: none; }
button { background: #28a745; color: white; cursor: pointer; }
button:hover { background: #218838; }
.container { background: #222; padding: 30px; border-radius: 10px; display: inline-block; }
</style>
</head>
<body>
    <div class="container">
        <h2>YouTube Audio/Video Downloader</h2>
        <form id="downloadForm">
            <input type="text" name="url" id="url" placeholder="Enter YouTube link" required size="40"><br>
            <select id="format" name="format">
                <option value="mp3">MP3 (Audio)</option>
                <option value="mp4">MP4 (Video)</option>
            </select><br>
            <button type="submit">Download</button>
        </form>
        <p id="status"></p>
    </div>
    <script>
        const form = document.getElementById("downloadForm");
        const status = document.getElementById("status");
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            status.innerText = "Processing...";
            const url = document.getElementById("url").value;
            const format = document.getElementById("format").value;
            const response = await fetch("/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, format })
            });
            const result = await response.json();
            if (result.error) {
                status.innerText = "Error: " + result.error;
            } else {
                status.innerHTML = `<a href="/file/${result.file}" style="color: #0f0;">Click to download ${result.file}</a>`;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/download', methods=['POST'])
def download_audio():
    data = request.get_json()
    url = data.get("url")
    file_format = data.get("format", "mp3")

    if not url:
        return jsonify({"error": "No URL provided"})

    # unique filename
    uid = str(uuid.uuid4())
    filename = f"{uid}.%(ext)s"
    output_path = f"downloads/{uid}"

    os.makedirs("downloads", exist_ok=True)

    if file_format == "mp3":
        ydl_opts = [
            "yt-dlp",
            "--cookies", "cookies.txt",
            "--extractor-args", "youtube:player_client=default",
            "-x", "--audio-format", "mp3",
            "-o", f"{output_path}.%(ext)s",
            url
        ]
    else:  # mp4
        ydl_opts = [
            "yt-dlp",
            "--cookies", "cookies.txt",
            "--extractor-args", "youtube:player_client=default",
            "-f", "bestvideo+bestaudio/best",
            "-o", f"{output_path}.%(ext)s",
            url
        ]

    try:
        result = subprocess.run(ydl_opts, capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({"error": result.stderr.strip()})
    except Exception as e:
        return jsonify({"error": str(e)})

    # find downloaded file
    for file in os.listdir("downloads"):
        if file.startswith(uid):
            return jsonify({"file": file})

    return jsonify({"error": "File not found"})


@app.route('/file/<path:filename>')
def serve_file(filename):
    file_path = os.path.join("downloads", filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
