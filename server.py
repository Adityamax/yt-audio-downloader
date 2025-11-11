from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

@app.route("/download", methods=["GET"])
def download():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    # Choose format
    option = request.args.get("format", "mp3")

    # Download options
    if option == "mp3":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }
    else:
        ydl_opts = {'format': 'best', 'outtmpl': 'downloads/%(title)s.%(ext)s'}

    os.makedirs("downloads", exist_ok=True)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return jsonify({
            "title": info.get("title"),
            "url": info.get("url"),
            "format": option
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

