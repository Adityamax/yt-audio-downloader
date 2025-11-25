import os
import uuid
import tempfile
import shutil
import threading
from threading import Timer
from pathlib import Path
from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_file, abort, after_this_request
)
import yt_dlp
import base64

app = Flask(__name__)
app.secret_key = os.urandom(24)

DOWNLOAD_CLEANUP_SECONDS = 60  # Delay before cleaning temp files

PROXIES = [
    "",  # no proxy
    "socks5://5.135.191.18:9100",
    "socks5://139.170.229.78:7080",
    "socks5://179.43.182.73:1080",
    "socks5://192.241.232.61:56527",
    "socks5://87.238.192.63:39272",
]

HTML_INDEX = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>YouTube Audio Downloader</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #f4f7f8;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      margin: 0;
      padding: 40px 20px;
    }
    .container {
      background: #fff;
      padding: 30px 40px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      max-width: 480px;
      width: 100%;
    }
    h1 {
      margin-top: 0;
      color: #222;
      text-align: center;
      font-weight: 700;
    }
    label {
      display: block;
      margin-top: 20px;
      font-weight: 600;
      color: #555;
    }
    input[type="url"],
    select,
    input[type="file"] {
      width: 100%;
      padding: 10px 12px;
      margin-top: 8px;
      border: 1.8px solid #ccc;
      border-radius: 6px;
      font-size: 15px;
      transition: border-color 0.3s ease;
    }
    input[type="url"]:focus,
    select:focus,
    input[type="file"]:focus {
      border-color: #4a90e2;
      outline: none;
    }
    input[type="submit"] {
      margin-top: 30px;
      background-color: #4a90e2;
      border: none;
      color: white;
      font-size: 18px;
      font-weight: 600;
      padding: 12px 0;
      width: 100%;
      border-radius: 6px;
      cursor: pointer;
      transition: background-color 0.25s ease;
    }
    input[type="submit"]:hover {
      background-color: #357abd;
    }
    small {
      color: #888;
      font-size: 13px;
      margin-top: 6px;
      display: block;
    }
    .message {
      margin-top: 20px;
      color: #2d862d;
      font-weight: 600;
      text-align: center;
    }
    .error {
      margin-top: 20px;
      color: #d9534f;
      font-weight: 600;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>YouTube Audio Downloader</h1>
    <form method="post" enctype="multipart/form-data">
      <label for="url">YouTube URL:</label>
      <input type="url" id="url" name="url" placeholder="Enter YouTube video URL" required>

      <label for="proxy">Proxy (optional):</label>
      <select id="proxy" name="proxy">
        {% for p in proxies %}
          <option value="{{p}}" {% if p == '' %}selected{% endif %}>{{ 'No Proxy' if p=='' else p }}</option>
        {% endfor %}
      </select>

      <label for="cookies_file">Upload cookies.txt (optional):</label>
      <input type="file" id="cookies_file" name="cookies_file" accept=".txt">
      <small>Or set YT_COOKIES_B64 environment variable to base64(cookies.txt)</small>

      <input type="submit" value="Start Download">
    </form>

    {% if message %}
      <div class="message">{{ message }}</div>
    {% endif %}
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
  </div>
</body>
</html>
"""

HTML_STATUS = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Download Status</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #f4f7f8;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      margin: 0;
      padding: 40px 20px;
    }
    .container {
      background: #fff;
      padding: 30px 40px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      max-width: 480px;
      width: 100%;
      text-align: center;
    }
    h1 {
      margin-top: 0;
      color: #222;
      font-weight: 700;
    }
    p {
      font-size: 16px;
      color: #444;
      margin: 12px 0;
    }
    a.download-link {
      display: inline-block;
      margin-top: 20px;
      background: #28a745;
      color: white;
      text-decoration: none;
      padding: 12px 24px;
      font-weight: 600;
      border-radius: 6px;
      transition: background-color 0.25s ease;
    }
    a.download-link:hover {
      background: #1e7e34;
    }
    .error {
      color: #d9534f;
      font-weight: 700;
      margin-top: 20px;
    }
    a.back-link {
      display: inline-block;
      margin-top: 30px;
      color: #4a90e2;
      text-decoration: none;
      font-weight: 600;
    }
    a.back-link:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Job {{ job_id }}</h1>
    <p>Status: <strong>{{ job.status }}</strong></p>
    {% if job.progress is not none %}
      <p>Progress: {{ job.progress }}</p>
    {% endif %}
    {% if job.error %}
      <p class="error">Error: {{ job.error }}</p>
    {% endif %}
    {% if job.filename %}
      <a class="download-link" href="{{ url_for('download', job_id=job_id) }}">Download File</a>
    {% else %}
      <p>If the job is still running, please reload this page.</p>
    {% endif %}
    <br>
    <a class="back-link" href="{{ url_for('index') }}">← Back to Home</a>
  </div>
</body>
</html>
"""



JOBS = {}  # job_id -> dict(status, temp_dir, filename, error, progress, tmp_cookies)


def cleanup_dir(path):
    try:
        shutil.rmtree(path)
    except Exception:
        pass


def schedule_cleanup(temp_dir, delay=DOWNLOAD_CLEANUP_SECONDS):
    Timer(delay, cleanup_dir, args=[temp_dir]).start()


def make_progress_hook(job_id):
    def progress(d):
        job = JOBS.get(job_id)
        if not job:
            return
        status = d.get('status')
        if status == 'downloading':
            downloaded_bytes = d.get('downloaded_bytes')
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if downloaded_bytes and total_bytes:
                pct = downloaded_bytes * 100 / total_bytes if total_bytes else None
                job['progress'] = f"{pct:.1f}% ({downloaded_bytes}/{total_bytes} bytes)"
            else:
                job['progress'] = d.get('eta') and f"ETA {d.get('eta')}" or "downloading..."
        elif status == 'finished':
            job['progress'] = "finished downloading; postprocessing..."
        else:
            job['progress'] = str(d)
    return progress


def run_download(job_id, url, proxy, cookies_file_path):
    job = JOBS[job_id]
    temp_dir = job['temp_dir']
    out_template = os.path.join(temp_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        'outtmpl': out_template,
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 30,
        'progress_hooks': [make_progress_hook(job_id)],
    }

    if proxy:
        ydl_opts['proxy'] = proxy

    if cookies_file_path:
        ydl_opts['cookiefile'] = cookies_file_path

    try:
        job['status'] = 'starting'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            job['status'] = 'downloading'
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            final_mp3 = os.path.splitext(filename)[0] + ".mp3"
            if not os.path.exists(final_mp3):
                files = list(Path(temp_dir).glob("*"))
                if files:
                    final_mp3 = str(files[0])
            job['filename'] = final_mp3
            job['status'] = 'finished'
            job['progress'] = '100%'
    except Exception as e:
        job['status'] = 'error'
        job['error'] = str(e)
    finally:
        if job.get('tmp_cookies') and os.path.exists(job['tmp_cookies']):
            try:
                os.remove(job['tmp_cookies'])
            except Exception:
                pass
        schedule_cleanup(temp_dir, delay=DOWNLOAD_CLEANUP_SECONDS)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        proxy = request.form.get("proxy", "").strip() or None

        if not url:
            return render_template_string(HTML_INDEX, error="Please enter a YouTube URL", proxies=PROXIES)

        job_id = str(uuid.uuid4())
        temp_dir = tempfile.mkdtemp(prefix="yt_dl_")
        JOBS[job_id] = {
            'status': 'queued',
            'temp_dir': temp_dir,
            'filename': None,
            'error': None,
            'progress': None,
            'tmp_cookies': None,
        }

        cookies_file_path = None
        uploaded = request.files.get("cookies_file")
        if uploaded and uploaded.filename:
            cookies_path = os.path.join(temp_dir, "cookies.txt")
            uploaded.save(cookies_path)
            cookies_file_path = cookies_path
            JOBS[job_id]['tmp_cookies'] = cookies_path

        if not cookies_file_path:
            cookies_b64 = os.getenv("YT_COOKIES_B64")
            if cookies_b64:
                try:
                    cookies_raw = base64.b64decode(cookies_b64)
                    cookies_path = os.path.join(temp_dir, "cookies.txt")
                    with open(cookies_path, "wb") as f:
                        f.write(cookies_raw)
                    cookies_file_path = cookies_path
                    JOBS[job_id]['tmp_cookies'] = cookies_path
                except Exception as e:
                    JOBS[job_id]['error'] = f"Bad YT_COOKIES_B64 env (ignored): {e}"

        JOBS[job_id]['status'] = 'starting'
        worker = threading.Thread(target=run_download, args=(job_id, url, proxy, cookies_file_path), daemon=True)
        worker.start()

        return redirect(url_for('status', job_id=job_id))

    return render_template_string(HTML_INDEX, proxies=PROXIES)


@app.route("/status/<job_id>", methods=["GET"])
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        abort(404)
    return render_template_string(HTML_STATUS, job=job, job_id=job_id)


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    job = JOBS.get(job_id)
    if not job:
        abort(404)
    if job.get('status') != 'finished' or not job.get('filename'):
        return redirect(url_for('status', job_id=job_id))

    filepath = job['filename']
    if not os.path.exists(filepath):
        return render_template_string(HTML_STATUS, job=job, job_id=job_id, error="File missing on disk")

    temp_dir = job['temp_dir']

    @after_this_request
    def cleanup(response):
        schedule_cleanup(temp_dir, delay=DOWNLOAD_CLEANUP_SECONDS)
        JOBS.pop(job_id, None)
        return response

    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
