from flask import Flask, request, render_template_string, send_file
import yt_dlp
import os
import tempfile
import shutil
from threading import Timer
import traceback

app = Flask(__name__)

HTML = '''
<!doctype html>
<title>YouTube Audio Downloader</title>
<h2>YouTube Audio Downloader</h2>
<form method=post>
  <label for=url>YouTube URL:</label>
  <input type=text id=url name=url size=50 required><br><br>
  <label for=proxy>Proxy (optional, e.g. http://proxyserver:port):</label>
  <input type=text id=proxy name=proxy size=50><br><br>
  <input type=submit value=Download>
</form>
{% if error %}
<p style="color:red;">Error: {{ error }}</p>
{% endif %}
'''

def cleanup_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        proxy = request.form.get('proxy', '').strip() or None

        if not url:
            return render_template_string(HTML, error='Please enter a YouTube URL')

        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': output_path,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            # Increase buffer to reduce worker timeout risks
            'ratelimit': None,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
            'noplaylist': True,
        }

        if proxy:
            ydl_opts['proxy'] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + '.mp3'

            # Schedule temp directory cleanup after 60 seconds
            Timer(60, cleanup_dir, args=[temp_dir]).start()

            return send_file(filename, as_attachment=True)
        except Exception as e:
            print(traceback.format_exc())
            cleanup_dir(temp_dir)
            return render_template_string(HTML, error=str(e))

    return render_template_string(HTML)

if __name__ == '__main__':
    # Use 0.0.0.0 to be accessible externally
    app.run(host='0.0.0.0', port=5000)
