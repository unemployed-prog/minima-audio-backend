const express = require('express');
const cors = require('cors');
const yts = require('yt-search');
const ytdl = require('@distube/ytdl-core');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());

// 1. ROUTE DI RICERCA MULTI-PIATTAFORMA
app.get('/api/search', async (req, res) => {
    const query = req.query.q;
    const platform = req.query.platform || 'youtube';

    if (!query) return res.status(400).json({ error: 'Query mancante' });

    try {
        let results = [];

        if (platform === 'youtube') {
            const r = await yts(query);
            results = r.videos.slice(0, 15).map(v => ({
                id: v.videoId,
                title: v.title,
                artist: v.author.name,
                album: 'YouTube Music',
                duration: v.seconds,
                coverUrl: v.thumbnail,
                platform: 'youtube',
                streamUrl: `/api/stream?id=${v.videoId}`,
                downloadUrl: `/api/download?id=${v.videoId}&title=${encodeURIComponent(v.title)}`
            }));
        } 
        else if (platform === 'deezer') {
            const searchRes = await axios.get(`https://api.deezer.com/search?q=${encodeURIComponent(query)}`);
            results = searchRes.data.data.slice(0, 15).map(item => ({
                id: item.id.toString(),
                title: item.title,
                artist: item.artist.name,
                album: item.album.title,
                duration: item.duration,
                coverUrl: item.album.cover_medium,
                platform: 'deezer',
                streamUrl: `/api/stream?query=${encodeURIComponent(item.artist.name + ' - ' + item.title)}`,
                downloadUrl: `/api/download?query=${encodeURIComponent(item.artist.name + ' - ' + item.title)}&title=${encodeURIComponent(item.title)}`
            }));
        }
        else if (platform === 'spotify' || platform === 'soundcloud') {
            const searchQuery = `${query} ${platform === 'spotify' ? 'audio' : 'soundcloud'}`;
            const r = await yts(searchQuery);
            results = r.videos.slice(0, 15).map(v => ({
                id: v.videoId,
                title: v.title.replace(/official audio|lyric video/gi, '').trim(),
                artist: v.author.name,
                album: platform.toUpperCase(),
                duration: v.seconds,
                coverUrl: v.thumbnail,
                platform: platform,
                streamUrl: `/api/stream?id=${v.videoId}`,
                downloadUrl: `/api/download?id=${v.videoId}&title=${encodeURIComponent(v.title)}`
            }));
        }

        res.json(results);
    } catch (err) {
        console.error('Errore ricerca:', err.message);
        res.status(500).json({ error: 'Errore nel recupero dei brani' });
    }
});

// 2. ROUTE STREAMING AUDIO INTERO
app.get('/api/stream', async (req, res) => {
    let videoId = req.query.id;
    const query = req.query.query;

    try {
        if (!videoId && query) {
            const search = await yts(query);
            if (search.videos.length > 0) videoId = search.videos[0].videoId;
        }

        if (!videoId) return res.status(400).send('Traccia non trovata');

        const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        res.setHeader('Content-Type', 'audio/mpeg');

        ytdl(videoUrl, {
            filter: 'audioonly',
            quality: 'highestaudio',
            highWaterMark: 1 << 25
        }).pipe(res);
    } catch (err) {
        console.error('Errore streaming:', err.message);
        res.status(500).send('Errore streaming audio');
    }
});

// 3. ROUTE DOWNLOAD FILE AUDIO
app.get('/api/download', async (req, res) => {
    let videoId = req.query.id;
    const query = req.query.query;
    const title = req.query.title || 'traccia';

    try {
        if (!videoId && query) {
            const search = await yts(query);
            if (search.videos.length > 0) videoId = search.videos[0].videoId;
        }

        if (!videoId) return res.status(400).send('Traccia non trovata');

        const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        const cleanTitle = title.replace(/[/\\?%*:|"<>]/g, '');

        res.setHeader('Content-Disposition', `attachment; filename="${cleanTitle}.mp3"`);
        res.setHeader('Content-Type', 'audio/mpeg');

        ytdl(videoUrl, {
            filter: 'audioonly',
            quality: 'highestaudio'
        }).pipe(res);
    } catch (err) {
        console.error('Errore download:', err.message);
        res.status(500).send('Errore durante il download');
    }
});

app.listen(PORT, () => {
    console.log(`> Server Cloud attivo sulla porta ${PORT}`);
});