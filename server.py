import yt_dlp
import tempfile
import os
import shutil
from threading import Timer
from flask import Flask, request, render_template_string, send_file

app = Flask(__name__)

PROXIES = [
    "socks5://5.135.191.18:9100",
    "socks5://139.170.229.78:7080",
    "socks5://179.43.182.73:1080",
    "socks5://192.241.232.61:56527",
    "socks5://87.238.192.63:39272",
]

HTML_FORM = '''
<!doctype html>
<title>YouTube Audio Downloader with Proxy</title>
<h2>YouTube Audio Downloader with Proxy</h2>
<form method=post>
  <label for=url>YouTube URL:</label>
  <input type=text id=url name=url size=50 required><br><br>
  <label for=proxy>Select Proxy (optional):</label>
  <select id=proxy name=proxy>
    <option value="">No Proxy</option>
    {% for p in proxies %}
      <option value="{{p}}">{{p}}</option>
    {% endfor %}
  </select><br><br>
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
            return render_template_string(HTML_FORM, error="Please enter a YouTube URL", proxies=PROXIES)

        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
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
        }

        if proxy:
            ydl_opts['proxy'] = proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = os.path.splitext(filename)[0] + '.mp3'

            Timer(60, cleanup_dir, args=[temp_dir]).start()

            return send_file(filename, as_attachment=True)
        except Exception as e:
            cleanup_dir(temp_dir)
            return render_template_string(HTML_FORM, error=str(e), proxies=PROXIES)

    return render_template_string(HTML_FORM, proxies=PROXIES)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
