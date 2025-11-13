from flask import Flask, request, render_template, send_file, redirect, url_for
from pytube import YouTube
import os
import io

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        format = request.form.get("format")

        if not url:
            return render_template("index.html", error="Please enter a YouTube URL")

        try:
            yt = YouTube(url)
            if format == "mp3":
                # Get audio stream only
                stream = yt.streams.filter(only_audio=True).first()
                buffer = io.BytesIO()
                stream.stream_to_buffer(buffer)
                buffer.seek(0)
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f"{yt.title}.mp3",
                    mimetype="audio/mpeg"
                )
            else:
                # mp4 video
                stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                buffer = io.BytesIO()
                stream.stream_to_buffer(buffer)
                buffer.seek(0)
                return send_file(
                    buffer,
                    as_attachment=True,
                    download_name=f"{yt.title}.mp4",
                    mimetype="video/mp4"
                )
        except Exception as e:
            return render_template("index.html", error=str(e))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
