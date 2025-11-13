from flask import Flask, request, send_file, jsonify
from yt_dlp import YoutubeDL
import os
import threading
import time
import uuid

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Auto cleanup every 5 minutes ---
def cleanup_old_files():
    while True:
        now = time.time()
        for filename in os.listdir(DOWNLOAD_DIR):
            path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(path):
                if now - os.path.getmtime(path) > 300:  # 5 minutes
                    try:
                        os.remove(path)
                    except Exception:
                        pass
        time.sleep(60)

threading.Thread(target=cleanup_old_files, daemon=True).start()


@app.route("/")
def home():
    return "YouTube Downloader API is running."


@app.route("/download", methods=["POST"])
def download_audio():
    data = request.get_json()
    url = data.get("url")
    format_type = data.get("format", "mp3")

    if not url:
        return jsonify({"error": "Missing YouTube URL"}), 400

    output_id = str(uuid.uuid4())
    if format_type == "mp4":
        output_path = os.path.join(DOWNLOAD_DIR, f"{output_id}.mp4")
        ydl_opts = {
            "outtmpl": output_path,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
        }
    else:
        output_path = os.path.join(DOWNLOAD_DIR, f"{output_id}.mp3")
        ydl_opts = {
            "outtmpl": output_path,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
        }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
