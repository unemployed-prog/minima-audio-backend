from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import urllib.parse
import urllib.request
import os
import re

app = Flask(__name__)
CORS(app)

# 1. ROUTE DI RICERCA MULTI-PIATTAFORMA
@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q')
    platform = request.args.get('platform', 'youtube')
    
    if not query:
        return jsonify({'error': 'Query mancante'}), 400

    try:
        if platform == 'youtube':
            search_query = f"ytsearch15:{query}"
        else:
            search_query = f"ytsearch15:{query} audio"
        
        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            results = []
            
            for entry in info.get('entries', []):
                video_id = entry.get('id')
                title = entry.get('title')
                uploader = entry.get('uploader') or entry.get('channel') or 'Unknown Artist'
                duration = entry.get('duration') or 0
                thumbnail = entry.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                
                results.append({
                    'id': video_id,
                    'title': title,
                    'artist': uploader,
                    'album': platform.upper(),
                    'duration': duration,
                    'coverUrl': thumbnail,
                    'platform': platform,
                    'streamUrl': f'/api/stream?id={video_id}',
                    'downloadUrl': f'/api/download?id={video_id}&title={urllib.parse.quote(title or "traccia")}'
                })
                
        return jsonify(results)
    except Exception as e:
        print(f"Errore ricerca: {str(e)}")
        return jsonify({'error': 'Errore nel recupero dei brani'}), 500

# 2. ROUTE STREAMING AUDIO INTERO
@app.route('/api/stream', methods=['GET'])
def stream():
    video_id = request.args.get('id')
    query = request.args.get('query')

    try:
        if not video_id and query:
            with yt_dlp.YoutubeDL({'extract_flat': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get('entries', [])
                if entries:
                    video_id = entries[0].get('id')

        if not video_id:
            return "Traccia non trovata", 400

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = info.get('url')

        def generate():
            req = urllib.request.urlopen(audio_url)
            while True:
                chunk = req.read(1024 * 64)
                if not chunk:
                    break
                yield chunk

        return Response(generate(), mimetype='audio/mpeg')
    except Exception as e:
        print(f"Errore streaming: {str(e)}")
        return "Errore streaming audio", 500

# 3. ROUTE DOWNLOAD FILE AUDIO
@app.route('/api/download', methods=['GET'])
def download():
    video_id = request.args.get('id')
    query = request.args.get('query')
    title = request.args.get('title', 'traccia')

    try:
        if not video_id and query:
            with yt_dlp.YoutubeDL({'extract_flat': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get('entries', [])
                if entries:
                    video_id = entries[0].get('id')

        if not video_id:
            return "Traccia non trovata", 400

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = info.get('url')

        clean_title = re.sub(r'[/\\?%*:|"<>]', '', title)

        def generate():
            req = urllib.request.urlopen(audio_url)
            while True:
                chunk = req.read(1024 * 64)
                if not chunk:
                    break
                yield chunk

        headers = {
            'Content-Disposition': f'attachment; filename="{clean_title}.mp3"'
        }
        return Response(generate(), mimetype='audio/mpeg', headers=headers)
    except Exception as e:
        print(f"Errore download: {str(e)}")
        return "Errore durante il download", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)