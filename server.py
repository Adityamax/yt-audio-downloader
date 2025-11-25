import os
import uuid
import tempfile
import shutil
import threading
from threading import Timer
from pathlib import Path
from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_file, abort, after_this_request, jsonify
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

HTML_SINGLE_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>YouTube Audio Downloader</title>
  <style>
    body {
      background-color: #000;
      color: #eee;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      margin: 0;
      padding: 40px 20px;
    }
    .container {
      background: #121212;
      padding: 30px 40px;
      border-radius: 12px;
      box-shadow: 0 0 20px #3a3a3a;
      max-width: 480px;
      width: 100%;
      color: #eee;
    }
    h1 {
      margin-top: 0;
      text-align: center;
      font-weight: 700;
      color: #4caf50;
      margin-bottom: 20px;
    }
    form > label {
      display: block;
      margin-top: 20px;
      font-weight: 600;
      color: #ccc;
    }
    input[type="url"],
    select,
    input[type="file"] {
      width: 100%;
      padding: 10px 12px;
      margin-top: 8px;
      border: 1.8px solid #444;
      border-radius: 6px;
      font-size: 15px;
      background: #222;
      color: #eee;
      transition: border-color 0.3s ease;
    }
    input[type="url"]:focus,
    select:focus,
    input[type="file"]:focus {
      border-color: #4caf50;
      outline: none;
    }
    input[type="submit"] {
      margin-top: 30px;
      background-color: #4caf50;
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
      background-color: #388e3c;
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
      color: #e53935;
      font-weight: 600;
      text-align: center;
    }
    .progress-container {
      margin-top: 30px;
      background: #222;
      border-radius: 8px;
      padding: 15px 20px;
    }
    .progress-label {
      font-weight: 600;
      color: #ccc;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
    }
    .progress-bar-bg {
      width: 100%;
      height: 14px;
      background: #333;
      border-radius: 7px;
      overflow: hidden;
    }
    .progress-bar-fill {
      height: 14px;
      background: linear-gradient(90deg, #4caf50, #81c784);
      width: 0%;
      transition: width 0.4s ease;
    }
    .download-button {
      margin-top: 25px;
      display: none;
      text-align: center;
    }
    .download-button a {
      background-color: #4caf50;
      color: white;
      text-decoration: none;
      padding: 12px 30px;
      border-radius: 30px;
      font-weight: 700;
      font-size: 18px;
      display: inline-block;
      transition: background-color 0.25s ease;
    }
    .download-button a:hover {
      background-color: #388e3c;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>YouTube Audio Downloader</h1>
    <form id="downloadForm" enctype="multipart/form-data">
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

    <div class="progress-container" id="progressContainer" style="display:none;">
      <div class="progress-label">
        <span id="fileName">Downloading your file...</span>
        <span id="progressPercent">0%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progressBar"></div>
      </div>
      <div class="progress-label" style="justify-content:flex-end; font-size: 12px; color: #aaa;">
        <span id="progressDetails"></span>
      </div>
    </div>

    <div class="download-button" id="downloadButton">
      <a id="downloadLink" href="#" download>Download File</a>
    </div>

    <div class="message" id="message"></div>
    <div class="error" id="error"></div>
  </div>

  <script>
    const form = document.getElementById('downloadForm');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressDetails = document.getElementById('progressDetails');
    const fileNameEl = document.getElementById('fileName');
    const downloadButton = document.getElementById('downloadButton');
    const downloadLink = document.getElementById('downloadLink');
    const message = document.getElementById('message');
    const error = document.getElementById('error');

    form.addEventListener('submit', async e => {
      e.preventDefault();
      message.textContent = '';
      error.textContent = '';
      downloadButton.style.display = 'none';
      progressBar.style.width = '0%';
      progressPercent.textContent = '0%';
      progressDetails.textContent = '';
      fileNameEl.textContent = 'Downloading your file...';
      progressContainer.style.display = 'block';

      const formData = new FormData(form);

      try {
        const response = await fetch('/start_download', {
          method: 'POST',
          body: formData
        });
        if (!response.ok) {
          throw new Error('Failed to start download');
        }
        const data = await response.json();
        const jobId = data.job_id;

        const pollInterval = 2000;
        let pollTimer;

        const pollStatus = async () => {
          try {
            const statusRes = await fetch('/job_status/' + jobId);
            if (!statusRes.ok) {
              throw new Error('Failed to get job status');
            }
            const statusData = await statusRes.json();

            if (statusData.status === 'error') {
              progressContainer.style.display = 'none';
              error.textContent = statusData.error || 'Error during download';
              clearInterval(pollTimer);
              return;
            }

            let pct = 0;
            if (statusData.progress) {
              let match = statusData.progress.match(/(\d+(\.\d+)?)/);
              if (match) {
                pct = parseFloat(match[1]);
              }
            }
            progressBar.style.width = pct + '%';
            progressPercent.textContent = pct.toFixed(1) + '%';

            if (statusData.filename) {
              fileNameEl.textContent = statusData.filename.split('/').pop();
              progressPercent.textContent = '100%';
              progressBar.style.width = '100%';
              progressDetails.textContent = 'Download ready';
              downloadLink.href = '/download/' + jobId;
              downloadButton.style.display = 'block';
              clearInterval(pollTimer);
            } else {
              progressDetails.textContent = statusData.progress || '';
              fileNameEl.textContent = 'Downloading your file...';
              downloadButton.style.display = 'none';
            }
          } catch (err) {
            error.textContent = 'Error fetching status';
            clearInterval(pollTimer);
          }
        };

        pollTimer = setInterval(pollStatus, pollInterval);
        pollStatus();

      } catch (err) {
        progressContainer.style.display = 'none';
        error.textContent = err.message || 'Unexpected error';
      }
    });
  </script>
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


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_SINGLE_PAGE, proxies=PROXIES)


@app.route("/start_download", methods=["POST"])
def start_download():
    url = request.form.get("url", "").strip()
    proxy = request.form.get("proxy", "").strip() or None

    if not url:
        return jsonify({"error": "Please enter a YouTube URL"}), 400

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

    return jsonify({"job_id": job_id})


@app.route("/job_status/<job_id>", methods=["GET"])
def job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job.get('status'),
        "progress": job.get('progress'),
        "filename": job.get('filename'),
        "error": job.get('error'),
    })


@app.route("/download/<job_id>", methods=["GET"])
def download(job_id):
    job = JOBS.get(job_id)
    if not job:
        abort(404)
    if job.get('status') != 'finished' or not job.get('filename'):
        return jsonify({"error": "File not ready"}), 404

    filepath = job['filename']
    if not os.path.exists(filepath):
        return jsonify({"error": "File missing on disk"}), 404

    temp_dir = job['temp_dir']

    @after_this_request
    def cleanup(response):
        schedule_cleanup(temp_dir, delay=DOWNLOAD_CLEANUP_SECONDS)
        JOBS.pop(job_id, None)
        return response

    return send_file(filepath, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
