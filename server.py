from flask import Flask, request, render_template, send_file
import yt_dlp
import os
import tempfile
import shutil
from threading import Timer

app = Flask(__name__)

def cleanup_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        format = request.form.get("format")

        if not url:
            return render_template("index.html", error="Please enter a YouTube URL")

        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')

        # Write cookies from environment variable to a temp file if available
        cookies_env = os.getenv("YT_COOKIES")
        cookies_file_path = None
        if cookies_env:
            cookies_file = tempfile.NamedTemporaryFile(delete=False)
            cookies_file.write(cookies_env.encode())
            cookies_file.flush()
            cookies_file_path = cookies_file.name
            cookies_file.close()

        ydl_opts = {
            'outtmpl': output_path,
            'format': 'bestaudio/best' if format == 'mp3' else 'bestvideo+bestaudio/best',
            'postprocessors': [],
            'quiet': True,
            'no_warnings': True,
        }

        if cookies_file_path:
            ydl_opts['cookiefile'] = cookies_file_path

        if format == 'mp3':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if format == 'mp3':
                    filename = os.path.splitext(filename)[0] + '.mp3'

            # Schedule cleanup of temp_dir and cookies file after 60 seconds
            Timer(60, cleanup_dir, args=[temp_dir]).start()
            if cookies_file_path:
                Timer(60, os.remove, args=[cookies_file_path]).start()

            return send_file(filename, as_attachment=True)
        except Exception as e:
            cleanup_dir(temp_dir)
            if cookies_file_path and os.path.exists(cookies_file_path):
                os.remove(cookies_file_path)
            return render_template("index.html", error=str(e))

    return render_template("index.html")
