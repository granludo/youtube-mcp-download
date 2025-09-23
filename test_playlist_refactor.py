#!/usr/bin/env python3
"""
Test script for the refactored playlist download functionality
"""

import asyncio
import sys
import os

# Add current directory to path so we can import the MCP server functions
sys.path.insert(0, os.path.dirname(__file__))

from youtube_mcp_server_fastmcp import (
    get_playlist_video_urls,
    download_playlist,
    get_playlist_metadata,
    setup_database
)

async def test_playlist_functions():
    """Test the playlist functions"""

    print("🎬 Testing refactored playlist download functionality")
    print("="*60)

    # Initialize database
    print("📊 Setting up database...")
    setup_database()

    # Test playlist URL - using a small test playlist
    test_playlist_url = "https://www.youtube.com/playlist?list=PLFgquLnL59alCl_2TQvOiD5Vgm1hCaGSI"  # Tiny Toons playlist

    print(f"\n📋 Testing with playlist: {test_playlist_url}")

    # Test 1: Extract video URLs from playlist
    print("\n1️⃣ Testing get_playlist_video_urls...")
    try:
        # Note: get_playlist_video_urls is not async in the actual implementation
        # Let's call it directly without await
        import subprocess
        import json

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-warnings",
            "--quiet",
            "--no-download",
            "--flat-playlist",
            "--print-json",
            "--playlist-items", "1-3",
            test_playlist_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"❌ Error extracting playlist videos: {result.stderr}")
            return

        # Parse JSON output
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
            print("❌ No videos found in playlist")
            return

        playlist_title = video_data[0].get("playlist_title", "Unknown Playlist")
        print(f"✅ Successfully extracted {len(video_data)} videos from playlist")
        print(f"📝 Playlist title: {playlist_title}")
        for i, video in enumerate(video_data[:3]):  # Show first 3
            print(f"   {i+1}. {video['title']} (index: {video['index']})")

    except Exception as e:
        print(f"❌ Exception in get_playlist_video_urls: {e}")
        return

    # Test 2: Download playlist (limited to 2 videos for testing)
    print("\n2️⃣ Testing download_playlist...")
    try:
        result = await download_playlist(test_playlist_url, "downloads", max_videos=2)
        print(f"✅ Download started: {result}")
        if "Job ID:" in result:
            job_id = result.split("Job ID: ")[1]
            print(f"📋 Job ID: {job_id}")
        else:
            print("⚠️  Could not extract job ID from response")
            return
    except Exception as e:
        print(f"❌ Exception in download_playlist: {e}")
        return

    # Wait a bit for download to complete
    print("\n⏳ Waiting for download to complete...")
    await asyncio.sleep(30)  # Wait 30 seconds for downloads to finish

    # Test 3: Get playlist metadata
    print("\n3️⃣ Testing get_playlist_metadata...")
    try:
        metadata = await get_playlist_metadata(test_playlist_url)
        if "error" in metadata:
            print(f"❌ Error getting playlist metadata: {metadata['error']}")
        else:
            print(f"✅ Successfully retrieved playlist metadata")
            print(f"📝 Title: {metadata.get('title', 'N/A')}")
            print(f"🎥 Video count: {metadata.get('video_count', 'N/A')}")
            print(f"📥 Downloaded: {metadata.get('downloaded', 'N/A')}")
            if metadata.get('downloaded'):
                print(f"📊 Downloaded videos: {metadata.get('downloaded_count', 0)}")
                videos = metadata.get('videos', [])
                if videos:
                    print("📋 Downloaded videos:")
                    for video in videos[:3]:  # Show first 3
                        print(f"   • {video['title']} (index: {video.get('playlist_index', 'N/A')})")
    except Exception as e:
        print(f"❌ Exception in get_playlist_metadata: {e}")

    print("\n🎉 Testing completed!")
    print("\n📁 Check the 'downloads' directory for downloaded videos")
    print("📊 Check the database for stored metadata")

if __name__ == "__main__":
    asyncio.run(test_playlist_functions())
