#!/usr/bin/env python3
"""
YouTube MCP Server (FastMCP version)
Provides asynchronous video and playlist downloads with job tracking and metadata storage.
"""

import asyncio
import sqlite3
import threading
import time
import os
import subprocess
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

# FastMCP
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("youtube-downloader")

# Global variables
db_path = "youtube_library.db"
download_executor = ThreadPoolExecutor(max_workers=3)


def setup_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Jobs table for tracking download jobs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,  -- 'video' or 'playlist'
            url TEXT NOT NULL,
            status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
            progress INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')

    # Videos table for individual videos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            duration INTEGER,
            file_path TEXT,
            source_url TEXT,
            job_id TEXT,
            playlist TEXT,  -- Playlist name/title (nullable)
            pl_index INTEGER,  -- Position in playlist (nullable)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    ''')


    conn.commit()
    conn.close()
    print("Database initialized", file=sys.stderr)


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def create_download_job(job_type: str, url: str) -> str:
    """Create a new download job and return job ID"""
    job_id = str(uuid.uuid4())

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO jobs (id, job_type, url, status)
        VALUES (?, ?, ?, 'pending')
    ''', (job_id, job_type, url))

    conn.commit()
    conn.close()

    return job_id


def update_job_status(job_id: str, status: str, progress: int = None, error_message: str = None):
    """Update job status in database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    update_fields = ["status = ?"]
    params = [status]

    if progress is not None:
        update_fields.append("progress = ?")
        params.append(progress)

    if error_message is not None:
        update_fields.append("error_message = ?")
        params.append(error_message)

    if status == "completed" or status == "failed":
        update_fields.append("completed_at = CURRENT_TIMESTAMP")

    params.append(job_id)

    cursor.execute(f'''
        UPDATE jobs
        SET {", ".join(update_fields)}
        WHERE id = ?
    ''', params)

    conn.commit()
    conn.close()


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get current status of a download job"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM jobs WHERE id = ?
    ''', (job_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def cancel_job(job_id: str) -> bool:
    """Cancel a running or pending job"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE jobs
        SET status = 'cancelled', completed_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status IN ('pending', 'running')
    ''', (job_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success


def run_yt_dlp(url: str, output_template: str, job_id: str, job_type: str, max_videos: int = None) -> Dict[str, Any]:
    """Run yt-dlp to download video/playlist"""
    try:
        # Update job status to running
        update_job_status(job_id, "running", progress=0)

        # Handle playlist downloads differently - extract video URLs first
        if job_type == "playlist":
            # Get video URLs from playlist
            playlist_result = get_playlist_video_urls(url, max_videos)
            if "error" in playlist_result:
                update_job_status(job_id, "failed", error_message=playlist_result["error"])
                return {"error": playlist_result["error"]}

            videos_to_download = playlist_result["videos"]
            playlist_title = playlist_result["playlist_title"]

            # Update progress for each video download
            total_videos = len(videos_to_download)
            for i, video_info in enumerate(videos_to_download):
                video_url = video_info["url"]
                pl_index = video_info["index"]

                # Download this video individually using the video download logic
                try:
                    # Get metadata for this video
                    metadata_cmd = [
                        sys.executable, "-m", "yt_dlp",
                        "--no-warnings",
                        "--quiet",
                        "--no-download",
                        "--dump-json",
                        video_url
                    ]
                    metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=30)

                    if metadata_result.returncode == 0:
                        metadata = json.loads(metadata_result.stdout)

                        # Store video metadata in database with playlist info
                        conn = get_db_connection()
                        cursor = conn.cursor()

                        # Generate file path
                        title = metadata.get("title", "unknown")
                        sanitized_title = title.replace("/", "_").replace("\\", "_").replace("|", "_").replace("?", "_").replace("*", "_").replace("<", "_").replace(">", "_").replace('"', "_").replace(":", "_")
                        expected_filename = f"{sanitized_title}.mp4"
                        base_dir = os.path.dirname(output_template)
                        file_path = os.path.abspath(os.path.join(base_dir, expected_filename))

                        cursor.execute('''
                            INSERT INTO videos (id, title, description, duration, file_path, source_url, job_id, playlist, pl_index)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            str(uuid.uuid4()),
                            metadata.get("title"),
                            metadata.get("description", "")[:1000],  # Limit description
                            metadata.get("duration"),
                            file_path,
                            video_url,
                            job_id,
                            playlist_title,
                            pl_index
                        ))

                        conn.commit()
                        conn.close()

                        # Now download the actual video
                        video_cmd = [
                            sys.executable, "-m", "yt_dlp",
                            "--no-warnings",
                            "--quiet",
                            "--no-simulate",
                            "-f", "best[ext=mp4]/best",
                            "-o", output_template,
                            video_url
                        ]

                        video_result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=300)
                        if video_result.returncode != 0:
                            print(f"Warning: Failed to download video {video_url}: {video_result.stderr}", file=sys.stderr)
                            continue

                except Exception as e:
                    print(f"Warning: Failed to download/process video {video_url}: {e}", file=sys.stderr)
                    continue

                # Update progress
                progress = int((i + 1) / total_videos * 100)
                update_job_status(job_id, "running", progress=progress)

            # Mark job as completed
            update_job_status(job_id, "completed", progress=100)
            return {"success": True}

        # Handle single video downloads
        elif job_type == "video":
            try:
                # Get metadata
                metadata_cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "--no-warnings",
                    "--quiet",
                    "--no-download",
                    "--dump-json",
                    url
                ]
                metadata_result = subprocess.run(metadata_cmd, capture_output=True, text=True, timeout=30)

                if metadata_result.returncode == 0:
                    metadata = json.loads(metadata_result.stdout)

                    # Store video metadata in database
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Generate file path based on yt-dlp output template
                    # yt-dlp sanitizes the title, so we need to approximate this
                    title = metadata.get("title", "unknown")
                    # Basic sanitization that yt-dlp does
                    sanitized_title = title.replace("/", "_").replace("\\", "_").replace("|", "_").replace("?", "_").replace("*", "_").replace("<", "_").replace(">", "_").replace('"', "_").replace(":", "_")
                    expected_filename = f"{sanitized_title}.mp4"
                    base_dir = os.path.dirname(output_template)
                    file_path = os.path.abspath(os.path.join(base_dir, expected_filename))

                    cursor.execute('''
                        INSERT INTO videos (id, title, description, duration, file_path, source_url, job_id, playlist, pl_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        metadata.get("title"),
                        metadata.get("description", "")[:1000],  # Limit description
                        metadata.get("duration"),
                        file_path,
                        url,
                        job_id,
                        None,  # No playlist
                        None   # No playlist index
                    ))

                    conn.commit()
                    conn.close()
            except Exception as e:
                # Don't fail the download if metadata storage fails
                print(f"Warning: Failed to store video metadata: {e}", file=sys.stderr)

        # Prepare command
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-simulate",
            "--progress",
            "--newline",
            "-o", output_template
        ]

        # For video downloads, run yt-dlp directly
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-simulate",
            "--progress",
            "--newline",
            "-f", "best[ext=mp4]/best",
            "-o", output_template,
            url
        ]

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Parse progress from output
        for line in process.stdout:
            line = line.strip()

            if "[download]" in line:
                # Try to extract percentage
                if "%" in line:
                    try:
                        percent_str = line.split("%")[0].split()[-1]
                        progress = float(percent_str)
                        update_job_status(job_id, "running", progress=int(progress))
                    except (ValueError, IndexError):
                        pass

                # Check if download is complete
                if "100%" in line or "has already been downloaded" in line:
                    update_job_status(job_id, "running", progress=100)

        # Wait for process to complete
        process.wait()

        if process.returncode == 0:
            update_job_status(job_id, "completed", progress=100)
            return {"success": True, "job_id": job_id}
        else:
            stderr = process.stderr.read() if process.stderr else "Unknown error"
            update_job_status(job_id, "failed", error_message=stderr)
            return {"success": False, "error": stderr}

    except Exception as e:
        error_msg = str(e)
        update_job_status(job_id, "failed", error_message=error_msg)
        return {"success": False, "error": error_msg}


def start_download_async(url: str, output_dir: str, job_id: str, job_type: str, max_videos: int = None) -> Dict[str, Any]:
    """Start download in background thread (non-blocking)"""
    try:
        # Prepare output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Use same output template for both videos and playlists
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

        # Submit to executor (this returns immediately)
        download_executor.submit(run_yt_dlp, url, output_template, job_id, job_type, max_videos)

        return {"success": True, "job_id": job_id}
    except Exception as e:
        update_job_status(job_id, "failed", error_message=str(e))
        return {"success": False, "error": str(e)}


async def download_video_async(url: str, output_dir: str = "downloads") -> Dict[str, Any]:
    """Asynchronously download a video (starts download and returns immediately)"""
    # Create job
    job_id = create_download_job("video", url)

    # Start download in background (non-blocking)
    result = start_download_async(url, output_dir, job_id, "video")

    return result


async def download_playlist_async(url: str, output_dir: str = "downloads", max_videos: int = 5) -> Dict[str, Any]:
    """Asynchronously download videos from a playlist (starts download and returns immediately)"""
    # Create job
    job_id = create_download_job("playlist", url)

    # Start download in background (non-blocking)
    result = start_download_async(url, output_dir, job_id, "playlist", max_videos)

    return result


# MCP Tool Definitions using FastMCP decorators

@mcp.tool()
async def download_video(url: str, output_dir: str = "downloads") -> str:
    """
    Start downloading a video from YouTube or other supported sites.
    Returns a job ID to track download progress.
    
    Args:
        url: The URL of the video to download
        output_dir: Directory to save the video (default: 'downloads')
    """
    result = await download_video_async(url, output_dir)
    if result["success"]:
        return f"Download started successfully. Job ID: {result['job_id']}"
    else:
        return f"Failed to start download: {result['error']}"


@mcp.tool()
async def download_playlist(url: str, output_dir: str = "downloads", max_videos: int = 5) -> str:
    """
    Start downloading videos from a YouTube playlist.
    Downloads individual videos and stores them with playlist metadata.
    Returns a job ID to track download progress.

    Args:
        url: The URL of the playlist to download from
        output_dir: Directory to save the videos (default: 'downloads')
        max_videos: Maximum number of videos to download (default: 5)
    """
    result = await download_playlist_async(url, output_dir, max_videos)
    if result["success"]:
        return f"Playlist download started successfully (limited to {max_videos} videos). Job ID: {result['job_id']}"
    else:
        return f"Failed to start playlist download: {result['error']}"


@mcp.tool()
async def get_download_status(job_id: str) -> Dict[str, Any]:
    """
    Check the status of a download job.

    Args:
        job_id: The job ID returned when starting a download
    """
    status = get_job_status(job_id)
    if status:
        return {
            "job_id": status["id"],
            "type": status["job_type"],
            "url": status["url"],
            "status": status["status"],
            "progress": status["progress"],
            "error": status["error_message"],
            "created_at": status["created_at"],
            "completed_at": status["completed_at"]
        }
    else:
        return {"error": f"Job {job_id} not found"}


@mcp.tool()
async def cancel_download(job_id: str) -> str:
    """
    Cancel a running or pending download job.
    
    Args:
        job_id: The job ID to cancel
    """
    if cancel_job(job_id):
        return f"Job {job_id} has been cancelled"
    else:
        return f"Could not cancel job {job_id} (it may be already completed or not exist)"


@mcp.tool()
async def list_downloads() -> Dict[str, Any]:
    """
    List all download jobs with their current status.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, job_type, url, status, progress, created_at
        FROM jobs
        ORDER BY created_at DESC
        LIMIT 20
    ''')

    rows = cursor.fetchall()
    conn.close()

    if rows:
        jobs = []
        for row in rows:
            jobs.append({
                "job_id": row["id"],
                "type": row["job_type"],
                "url": row["url"],
                "status": row["status"],
                "progress": row["progress"],
                "created_at": row["created_at"]
            })
        return {"jobs": jobs}
    else:
        return {"jobs": []}


@mcp.tool()
async def get_video_metadata(url: str) -> Dict[str, Any]:
    """
    Fetch metadata about a video without downloading it.
    Also includes file path if the video has been downloaded.

    Args:
        url: The URL of the video
    """
    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-download",
            "--dump-json",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            # Extract relevant fields
            clean_metadata = {
                "title": metadata.get("title"),
                "description": metadata.get("description", "")[:500],  # Limit description length
                "duration": metadata.get("duration"),
                "uploader": metadata.get("uploader"),
                "upload_date": metadata.get("upload_date"),
                "view_count": metadata.get("view_count"),
                "like_count": metadata.get("like_count"),
                "formats_available": len(metadata.get("formats", []))
            }

            # Check if video has been downloaded and get file path
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_path FROM videos
                WHERE source_url = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (url,))

            row = cursor.fetchone()
            conn.close()

            if row and row["file_path"]:
                clean_metadata["file_path"] = row["file_path"]
                clean_metadata["downloaded"] = True
            else:
                clean_metadata["downloaded"] = False

            return clean_metadata
        else:
            return {"error": f"Failed to fetch metadata: {result.stderr}"}

    except subprocess.TimeoutExpired:
        return {"error": "Timeout while fetching metadata"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse metadata"}
    except Exception as e:
        return {"error": f"Error fetching metadata: {str(e)}"}


def get_playlist_video_urls(url: str, max_videos: int = 5) -> Dict[str, Any]:
    """
    Extract individual video URLs from a playlist.

    Args:
        url: Playlist URL
        max_videos: Maximum number of videos to extract (default 5)

    Returns:
        Dict with playlist metadata and list of video URLs
    """
    try:
        # Use yt-dlp to get playlist info and extract video URLs
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-download",
            "--flat-playlist",  # Don't download, just list videos
            "--print-json",
            "--playlist-items", f"1-{max_videos}",  # Limit to max_videos
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return {"error": f"Failed to extract playlist videos: {result.stderr}"}

        # Parse JSON output - yt-dlp outputs one JSON object per video
        video_data = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    video = json.loads(line)
                    video_data.append({
                        "url": video.get("url"),
                        "title": video.get("title"),
                        "duration": video.get("duration"),
                        "index": video.get("playlist_index")
                    })
                except json.JSONDecodeError:
                    continue

        if not video_data:
            return {"error": "No videos found in playlist"}

        # Extract playlist metadata from first video
        playlist_title = video_data[0].get("playlist_title", "Unknown Playlist") if video_data else "Unknown Playlist"

        return {
            "playlist_title": playlist_title,
            "videos": video_data
        }

    except subprocess.TimeoutExpired:
        return {"error": "Timeout while extracting playlist videos"}
    except Exception as e:
        return {"error": f"Error extracting playlist videos: {str(e)}"}


@mcp.tool()
async def get_playlist_metadata(url: str) -> Dict[str, Any]:
    """
    Fetch metadata about a playlist without downloading it.
    Also includes file path and video information if the playlist has been downloaded.

    Args:
        url: The URL of the playlist
    """
    try:
        # First, try to get playlist info using --print-json without --flat-playlist
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-download",
            "--playlist-items", "1",  # Just get first video to get playlist info
            "--print-json",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Parse the JSON output (should be a single video with playlist info)
            metadata = json.loads(result.stdout.strip())
            # Extract relevant fields
            clean_metadata = {
                "title": metadata.get("playlist_title"),
                "description": metadata.get("playlist_description", "")[:500],  # Limit description length
                "uploader": metadata.get("playlist_uploader"),
                "video_count": metadata.get("playlist_count", 0),
                "upload_date": metadata.get("upload_date"),
                "view_count": metadata.get("view_count")
            }

            # Check if any videos from this playlist have been downloaded
            conn = get_db_connection()
            cursor = conn.cursor()

            # Get playlist title to match against video playlist field
            playlist_title = clean_metadata.get("title", "")

            if playlist_title:
                # Check if videos from this playlist exist in database
                cursor.execute('''
                    SELECT title, duration, file_path, source_url, pl_index
                    FROM videos
                    WHERE playlist = ?
                    ORDER BY pl_index
                ''', (playlist_title,))

                video_rows = cursor.fetchall()
                if video_rows:
                    clean_metadata["downloaded"] = True
                    clean_metadata["downloaded_count"] = len(video_rows)

                    videos = []
                    for row in video_rows:
                        videos.append({
                            "title": row["title"],
                            "duration": row["duration"],
                            "file_path": row["file_path"],
                            "source_url": row["source_url"],
                            "playlist_index": row["pl_index"]
                        })

                    clean_metadata["videos"] = videos
                else:
                    clean_metadata["downloaded"] = False
                    clean_metadata["downloaded_count"] = 0
            else:
                clean_metadata["downloaded"] = False
                clean_metadata["downloaded_count"] = 0

            conn.close()
            return clean_metadata
        else:
            return {"error": f"Failed to fetch playlist metadata: {result.stderr}"}

    except subprocess.TimeoutExpired:
        return {"error": "Timeout while fetching playlist metadata"}
    except json.JSONDecodeError:
        return {"error": "Failed to parse playlist metadata"}
    except Exception as e:
        return {"error": f"Error fetching playlist metadata: {str(e)}"}


def main():
    """Main entry point for the FastMCP server"""
    # Print to stderr so it doesn't interfere with MCP stdio protocol
    print("YouTube MCP Server (FastMCP) starting...", file=sys.stderr)
    setup_database()

    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
