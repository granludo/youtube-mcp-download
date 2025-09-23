# YouTube Video Downloader

A comprehensive collection of Python tools for downloading YouTube content using yt-dlp, including both simple scripts and an advanced MCP server.

## Tools

### 1. Simple Scripts

#### Single Video Downloader (`youtube_downloader.py`)
Downloads individual YouTube videos with progress tracking.

#### Playlist Downloader (`playlist_downloader.py`)
Downloads entire YouTube playlists with organization.

### 2. MCP Server (`youtube_mcp_server_fastmcp.py`)

An advanced MCP (Model Context Protocol) server using FastMCP that provides:
- Asynchronous video and playlist downloads
- Job tracking and status monitoring
- SQLite database for metadata storage
- Comprehensive library management
- Claude Desktop integration

## Features

### Simple Scripts

#### Single Video Downloader
- ✅ Prompts user for YouTube URL
- ✅ Downloads the best quality video available
- ✅ Creates a `downloads` folder for saved videos
- ✅ Shows download progress
- ✅ Handles errors gracefully
- ✅ Auto-installs yt-dlp if not present
- ✅ No pytube dependency (as requested)

#### Playlist Downloader
- ✅ Prompts user for YouTube playlist URL
- ✅ Downloads entire playlists (up to 50 videos by default)
- ✅ Creates organized folders for each playlist
- ✅ Shows playlist information before downloading
- ✅ Downloads videos with playlist index numbers
- ✅ Auto-installs yt-dlp if not present
- ✅ Confirmation prompt before downloading large playlists

### MCP Server Features
- ✅ **Asynchronous Downloads**: Start downloads and get job IDs for tracking
- ✅ **Job Status Monitoring**: Check download progress and status
- ✅ **Metadata Database**: SQLite database with video/playlists info
- ✅ **Library Management**: Browse all downloaded content
- ✅ **Error Handling**: Comprehensive error tracking and reporting
- ✅ **Concurrent Downloads**: Multiple downloads can run simultaneously
- ✅ **Rich Metadata**: Stores titles, descriptions, duration, file paths, etc.

## Requirements

- Python 3.11+
- yt-dlp (automatically installed if missing)
- MCP SDK (automatically installed if missing)

## Usage

### Single Video Download

1. Run the single video downloader:
   ```bash
   python3 youtube_downloader.py
   ```

2. Enter a YouTube URL when prompted

3. The video will be downloaded to the `downloads` folder

### Playlist Download

1. Run the playlist downloader:
   ```bash
   python3 playlist_downloader.py
   ```

2. Enter a YouTube playlist URL when prompted

3. Review playlist information and confirm download

4. All videos will be downloaded to a playlist-specific folder

### MCP Server Usage

The MCP server provides four main tools for asynchronous downloading and library management.

#### Using with uv (Recommended)

1. **Install dependencies and run:**
   ```bash
   cd /Users/granludo/code/testing/youtube_download
   uv sync
   uv run python start_server.py
   ```

#### Direct Python Usage

```bash
python3 youtube_mcp_server_fastmcp.py
```

#### Available MCP Tools

1. **download_video** - Start async video download
2. **download_playlist** - Start async playlist download
3. **get_download_status** - Monitor download progress
4. **cancel_download** - Cancel running downloads
5. **list_downloads** - Browse all download jobs
6. **get_video_metadata** - Get video info without downloading

## Examples

### Single Video Example
```bash
$ python3 youtube_downloader.py

==================================================
YouTube Video Downloader
==================================================
Enter YouTube URL: https://www.youtube.com/watch?v=dQw4w9WgXcQ
📥 Downloading video from: https://www.youtube.com/watch?v=dQw4w9WgXcQ
✓ Download completed!
📁 Files saved to: /path/to/downloads
```

### Playlist Example
```bash
$ python3 playlist_downloader.py

==================================================
YouTube Playlist Downloader
==================================================
Enter YouTube Playlist URL: https://www.youtube.com/playlist?list=PLrAXtmRdnEQy5rhxJj7aKre_2qO5yQ5nI
📊 Analyzing playlist...
📋 Playlist name: My Music Playlist
🎥 Number of videos: 25

🔄 Download 25 videos? (y/N): y
📥 Downloading playlist: My Music Playlist
✓ Playlist download completed!
📁 All videos saved to: /path/to/playlists/My Music Playlist
```

### MCP Server Examples

#### Using with uv

1. **Install and run the server:**
   ```bash
   cd /Users/granludo/code/testing/youtube_download
   uv sync                    # Install dependencies
   uv run python start_server.py  # Start server
   ```

2. **The server will start silently** (no stdout output, as required by MCP protocol)

#### MCP Tool Examples

**Tool 1: Download Single Video**
```json
{
  "name": "download_video",
  "arguments": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "output_dir": "downloads"
  }
}
```
Response: `"Download started successfully. Job ID: abc123-def456-ghi789"`

**Tool 2: Download Playlist**
```json
{
  "name": "download_playlist",
  "arguments": {
    "url": "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy5rhxJj7aKre_2qO5yQ5nI",
    "output_dir": "playlists"
  }
}
```
Response: `"Playlist download started successfully. Job ID: def456-ghi789-jkl012"`

**Tool 3: Check Download Status**
```json
{
  "name": "get_download_status",
  "arguments": {
    "job_id": "abc123-def456-ghi789"
  }
}
```
Response: JSON object with job status, progress, and metadata

**Tool 4: List Downloads**
```json
{
  "name": "list_downloads",
  "arguments": {}
}
```
Response:
```
📹 VIDEOS:
- Never Gonna Give You Up (ID: video-uuid-123)
  Path: /downloads/Never Gonna Give You Up.mp4
  Duration: 213s

📁 PLAYLISTS:
- Music Collection (ID: playlist-uuid-456)
  Videos: 25
  Path: /playlists/Music Collection
```

#### Complete Workflow Example

1. **Configure Claude Desktop** - Add the MCP server to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "youtube-mcp-tools": {
         "command": "/opt/homebrew/bin/uv",
         "args": [
           "--directory",
           "/Users/granludo/code/testing/youtube_download",
           "run",
           "start_server.py"
         ]
       }
     }
   }
   ```

2. **Download a video** in Claude:
   ```
   "Download this YouTube video: https://www.youtube.com/watch?v=jNQXAC9IVRw"
   ```
   The server will start the download and return a job ID immediately.

3. **Check download status**:
   ```
   "What's the status of that download?"
   ```

4. **List all downloads**:
   ```
   "Show me all my download jobs"
   ```

## Notes

### Simple Scripts
- Both scripts will automatically install yt-dlp if it's not found
- Videos are saved with their original titles
- Playlist videos are numbered by their position in the playlist
- The playlist downloader limits downloads to 50 videos by default (adjustable)
- Both scripts handle keyboard interrupts gracefully
- Downloads are organized in separate folders for videos vs playlists

### MCP Server
- Uses FastMCP for simplified MCP server implementation
- Creates `youtube_library.db` SQLite database for metadata
- Supports up to 3 concurrent downloads
- Job tracking with unique UUIDs for each download
- Rich metadata storage including titles, descriptions, duration, file paths
- Asynchronous downloads that return immediately with job IDs
- Comprehensive error handling and logging
- Compatible with Claude Desktop and other MCP clients
