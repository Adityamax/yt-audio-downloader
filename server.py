from flask import Flask, request, jsonify, send_file, render_template_string
import yt_dlp
import os

app = Flask(__name__)

# === Simple HTML UI ===
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Audio Downloader</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #0d1117;
            color: #f0f6fc;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }
        input, button {
            padding: 10px;
            border-radius: 6px;
            border: none;
            font-size: 15px;
        }
        input {
            width: 320px;
            margin-bottom: 10px;
        }
        button {
            background: #238636;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #2ea043;
        }
        #downloadBtn {
            display: none;
            background: #1f6feb;
        }
        #downloadBtn:hover {
            background: #388bfd;
        }
    </style>
</head>
<body>
    <h2>🎵 YouTube MP3 Downloader</h2>
    <input id="url" type="text" placeholder="Paste YouTube link here" />
    <button onclick="downloadAudio()">Convert to MP3</button>
    <button id="downloadBtn" onclick="getFile()">Download MP3</button>
    <p id="status"></p>

    <script>
        async function downloadAudio() {
            const url = document.getElementById('url').value.trim();
            const status = document.getElementById('status');
            const dlBtn = document.getElementById('downloadBtn');
            dlBtn.style.display = 'none';
            if (!url) return status.innerText = 'Please enter a YouTube link.';

            status.innerText = 'Converting... please wait ⏳';
            const res = await fetch('/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url })
            });

            const data = await res.json();
            if (data.error) {
                status.innerText = '❌ Error: ' + data.error;
            } else {
                status.innerText = '✅ Conversion complete!';
                dlBtn.style.display = 'inline-block';
            }
        }

        function getFile() {
            window.location.href = '/get_audio';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)


@app.route('/download', methods=['POST'])
def download_audio():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # Load cookies from environment variable
        cookie_data = os.getenv("YT_COOKIES", "")
        if not cookie_data.strip():
            return jsonify({"error": "No YouTube cookies found in environment"}), 500

        with open('/tmp/cookies.txt', 'w') as f:
            f.write(cookie_data)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '/tmp/audio.%(ext)s',
            'cookiefile': '/tmp/cookies.txt',
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_audio')
def get_audio():
    try:
        for ext in ['mp3', 'm4a', 'webm']:
            file_path = f'/tmp/audio.{ext}'
            if os.path.exists(file_path):
                return send_file(file_path, as_attachment=True)
        return jsonify({"error": "Audio file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
